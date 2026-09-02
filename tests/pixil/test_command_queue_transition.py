"""Tests for script-transition queue reset (no LED hardware required)."""

import pytest

from shared.command_queue import ConsumerRecoveryRequired, MatrixCommandQueue


def test_recreate_command_queue_replaces_ipc_objects():
    q = MatrixCommandQueue(queue_size=8)
    old_command_queue = q.command_queue
    old_reply_queue = q._test_snapshot_reply
    q._recreate_command_queue()
    assert q.command_queue is not old_command_queue
    assert q._test_snapshot_reply is not old_reply_queue
    assert q.command_queue._maxsize == 8


def test_prepare_for_next_script_uses_fast_drain_and_reset(monkeypatch):
    q = MatrixCommandQueue(queue_size=4)
    drain_calls = []
    reset_calls = []
    kill_calls = []
    fallback_calls = []

    monkeypatch.setattr(q, "discard_pending", lambda: 0)
    monkeypatch.setattr(
        q,
        "request_fast_drain",
        lambda timeout=1.0: drain_calls.append(timeout) or 12,
    )
    monkeypatch.setattr(
        q,
        "_wait_for_script_reset",
        lambda timeout=3.0: reset_calls.append(timeout) or True,
    )
    monkeypatch.setattr(
        q,
        "_kill_consumer_process",
        lambda *args, **kwargs: kill_calls.append(1),
    )
    monkeypatch.setattr(
        q,
        "reset_for_next_script",
        lambda timeout=3.0: fallback_calls.append(timeout),
    )
    q._consumer_process = type("P", (), {"is_alive": lambda self: True})()

    q.prepare_for_next_script()

    assert len(drain_calls) == 1
    assert len(reset_calls) == 1
    assert kill_calls == []
    assert fallback_calls == []


def test_prepare_for_next_script_falls_back_when_reset_not_acknowledged(monkeypatch):
    q = MatrixCommandQueue(queue_size=4)

    monkeypatch.setattr(q, "discard_pending", lambda: 0)
    monkeypatch.setattr(q, "request_fast_drain", lambda timeout=1.0: 5)
    monkeypatch.setattr(q, "_wait_for_script_reset", lambda timeout=3.0: False)
    q._consumer_process = type("P", (), {"is_alive": lambda self: True})()

    with pytest.raises(ConsumerRecoveryRequired, match="script reset"):
        q.prepare_for_next_script()


def test_prepare_for_next_script_falls_back_when_drain_times_out(monkeypatch):
    q = MatrixCommandQueue(queue_size=4)

    monkeypatch.setattr(q, "discard_pending", lambda: 0)
    monkeypatch.setattr(q, "request_fast_drain", lambda timeout=1.0: -1)
    q._consumer_process = type("P", (), {"is_alive": lambda self: True})()

    with pytest.raises(ConsumerRecoveryRequired, match="recovery"):
        q.prepare_for_next_script()


def test_fast_drain_waits_for_fifo_marker_before_acknowledging():
    q = MatrixCommandQueue(queue_size=4)
    q._drain_requested.set()

    assert q._handle_fast_drain_command("draw_line(0,0,1,1,white)") is True
    assert q._drain_swallowed.value == 1
    assert q._drain_complete.is_set() is False
    assert q._drain_requested.is_set() is True

    assert q._handle_fast_drain_command("__DRAIN__") is True
    assert q._drain_complete.is_set()
    assert q._drain_requested.is_set() is False


def test_fast_drain_does_not_consume_commands_when_not_requested():
    q = MatrixCommandQueue(queue_size=4)

    assert q._handle_fast_drain_command("draw_line(0,0,1,1,white)") is False
    assert q._drain_swallowed.value == 0
    assert q._drain_complete.is_set() is False


def test_sleep_delay_interruptible_detects_drain():
    q = MatrixCommandQueue(queue_size=4)
    q._drain_requested.set()
    assert q._sleep_delay_interruptible(500) is True


def test_reset_for_next_script_requires_full_process_restart():
    """Partial consumer replacement is unsafe after queue transport failure."""
    q = MatrixCommandQueue(queue_size=4)

    with pytest.raises(ConsumerRecoveryRequired, match="recovery"):
        q.reset_for_next_script()


def test_put_command_fails_instead_of_waiting_forever_on_full_queue():
    q = MatrixCommandQueue(
        queue_size=1,
        queue_full_timeout=0.01,
        consumer_heartbeat_timeout=60.0,
    )
    q.command_queue.put_nowait(("first", 0))
    q._consumer_process = type("P", (), {"is_alive": lambda self: True})()

    with pytest.raises(ConsumerRecoveryRequired, match="remained full"):
        q.put_command("second")


def test_shutdown_display_sets_force_shutdown_and_waits(monkeypatch):
    q = MatrixCommandQueue(queue_size=4)
    calls = []

    class FakeProcess:
        def __init__(self):
            self._alive = True

        def is_alive(self):
            return self._alive

        def join(self, timeout=None):
            calls.append(("join", timeout))
            self._alive = False

    q._consumer_process = FakeProcess()
    monkeypatch.setattr(q._shutdown_complete, "wait", lambda timeout: True)
    monkeypatch.setattr(q, "discard_pending", lambda: calls.append("discard") or 0)
    monkeypatch.setattr(q, "_kill_consumer_process", lambda *args, **kwargs: calls.append("kill"))
    monkeypatch.setattr(q, "_recreate_command_queue", lambda: calls.append("recreate"))
    emergency_calls = []
    monkeypatch.setattr(
        q,
        "_run_emergency_blackout",
        lambda timeout=4.0: emergency_calls.append(timeout),
    )

    q.shutdown_display(timeout=4.0)

    assert q._force_shutdown.is_set() is False
    assert "discard" in calls
    assert ("join", 1.0) in calls
    assert "recreate" in calls
    assert emergency_calls == []
    assert q._consumer_process is None


def test_shutdown_display_runs_emergency_blackout_when_consumer_times_out(monkeypatch):
    q = MatrixCommandQueue(queue_size=4)
    calls = []

    class FakeProcess:
        def is_alive(self):
            return calls.count("kill") == 0

        def join(self, timeout=None):
            calls.append(("join", timeout))

    q._consumer_process = FakeProcess()
    q._shutdown_complete.clear()
    monkeypatch.setattr(q, "discard_pending", lambda: 0)
    monkeypatch.setattr(
        q,
        "_kill_consumer_process",
        lambda *args, **kwargs: calls.append("kill"),
    )
    monkeypatch.setattr(q, "_recreate_command_queue", lambda: None)
    monkeypatch.setattr("shared.command_queue.time.sleep", lambda _s: None)
    emergency_calls = []
    monkeypatch.setattr(
        q,
        "_run_emergency_blackout",
        lambda timeout=4.0: emergency_calls.append(timeout),
    )

    q.shutdown_display(timeout=0.01)

    assert "kill" in calls
    assert emergency_calls == [0.01]

