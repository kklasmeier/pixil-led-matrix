"""Tests for the persistent Pixil runtime status file."""

import json

from pixil_utils import runtime_status


def test_initialize_and_update_runtime_status(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime_status, "STATUS_PATH", tmp_path / "runtime_status.json")
    monkeypatch.setattr(runtime_status.os, "getpid", lambda: 1234)
    timestamps = iter((100.0, 120.0))
    monkeypatch.setattr(runtime_status.time, "time", lambda: next(timestamps))

    runtime_status.initialize_status(["main/*", "-t", "45:00"])
    runtime_status.set_current_script("/shows/Example.pix", 2700)

    status = runtime_status.read_status()
    assert status == {
        "arguments": ["main/*", "-t", "45:00"],
        "pid": 1234,
        "process_started_at": 100.0,
        "recent_scripts": [],
        "script_expected_end_at": 2820.0,
        "script_name": "Example.pix",
        "script_path": "/shows/Example.pix",
        "script_started_at": 120.0,
    }
    assert json.loads(runtime_status.STATUS_PATH.read_text()) == status


def test_clear_status_only_removes_own_process(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime_status, "STATUS_PATH", tmp_path / "runtime_status.json")
    monkeypatch.setattr(runtime_status.os, "getpid", lambda: 1234)
    runtime_status._write_status({"pid": 9999})

    runtime_status.clear_status()
    assert runtime_status.read_status() == {"pid": 9999}

    runtime_status._write_status({"pid": 1234})
    runtime_status.clear_status()
    assert not runtime_status.STATUS_PATH.exists()


def test_read_status_ignores_invalid_json(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime_status, "STATUS_PATH", tmp_path / "runtime_status.json")
    runtime_status.STATUS_PATH.write_text("{not valid JSON")

    assert runtime_status.read_status() is None


def test_queue_reporter_tracks_current_and_script_average(monkeypatch, tmp_path):
    queue_path = tmp_path / "queue_status.json"
    monkeypatch.setattr(runtime_status, "QUEUE_STATUS_PATH", queue_path)
    monkeypatch.setattr(runtime_status.os, "getpid", lambda: 1234)
    monkeypatch.setattr(runtime_status.time, "time", lambda: 200.0)

    depths = iter((10, 30))

    class FakeQueue:
        def qsize(self):
            return next(depths)

    queue_instance = type(
        "FakeQueueManager",
        (),
        {"command_queue": FakeQueue(), "_queue_size": 5000},
    )()
    reporter = runtime_status.QueueStatusReporter(queue_instance)
    reporter.reset_for_script(100.0)
    reporter._sample()
    reporter._sample()

    status = json.loads(queue_path.read_text())
    assert status["queue_depth"] == 30
    assert status["queue_capacity"] == 5000
    assert status["script_average_queue_depth"] == 20
    assert status["sample_count"] == 2
    assert status["script_started_at"] == 100.0


def test_recent_scripts_are_this_run_only(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime_status, "STATUS_PATH", tmp_path / "runtime_status.json")
    monkeypatch.setattr(runtime_status.os, "getpid", lambda: 1234)
    timestamps = iter((100.0, 110.0, 120.0, 130.0, 140.0, 150.0))
    monkeypatch.setattr(runtime_status.time, "time", lambda: next(timestamps))

    runtime_status.initialize_status(["main/*"])
    runtime_status.set_current_script("/shows/One.pix", 10)
    runtime_status.set_current_script("/shows/Two.pix", 10)
    runtime_status.set_current_script("/shows/Three.pix", 10)
    runtime_status.set_current_script("/shows/Four.pix", 10)

    status = runtime_status.read_status()
    assert [entry["name"] for entry in status["recent_scripts"]] == [
        "One.pix",
        "Two.pix",
        "Three.pix",
    ]
    assert status["script_name"] == "Four.pix"

    runtime_status.initialize_status(["main/*"])
    assert runtime_status.read_status()["recent_scripts"] == []
