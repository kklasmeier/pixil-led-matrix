"""Tests for external next/jump control requests."""

import json

from pixil_utils import runtime_control


def test_next_request_is_consumed_once(monkeypatch, tmp_path):
    control_path = tmp_path / "control.json"
    monkeypatch.setattr(runtime_control, "CONTROL_PATH", control_path)
    monkeypatch.setattr(runtime_control.os, "getpid", lambda: 1234)
    control_path.write_text(json.dumps({"pid": 1234, "action": "next"}))

    assert runtime_control.consume_transition_request() is True
    assert not control_path.exists()
    assert runtime_control.consume_transition_request() is False


def test_jump_request_records_target(monkeypatch, tmp_path):
    control_path = tmp_path / "control.json"
    monkeypatch.setattr(runtime_control, "CONTROL_PATH", control_path)
    monkeypatch.setattr(runtime_control.os, "getpid", lambda: 1234)
    monkeypatch.setattr(runtime_control, "_pending_jump_target", None)
    control_path.write_text(
        json.dumps({"pid": 1234, "action": "jump", "target": "/shows/Rain.pix"})
    )

    assert runtime_control.consume_transition_request() is True
    assert runtime_control.consume_jump_target() == "/shows/Rain.pix"
    assert runtime_control.consume_jump_target() is None


def test_request_for_another_process_is_not_consumed(monkeypatch, tmp_path):
    control_path = tmp_path / "control.json"
    monkeypatch.setattr(runtime_control, "CONTROL_PATH", control_path)
    monkeypatch.setattr(runtime_control.os, "getpid", lambda: 1234)
    control_path.write_text(json.dumps({"pid": 9999, "action": "next"}))

    assert runtime_control.consume_transition_request() is False
    assert control_path.exists()
