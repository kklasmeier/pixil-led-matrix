"""pixil_utils.test_hooks — no-op unless PIXIL_TEST_MODE is set."""

import os

from pixil_utils import test_hooks


def test_effective_rest_unchanged_when_off(monkeypatch):
    monkeypatch.delenv("PIXIL_TEST_MODE", raising=False)
    assert test_hooks.is_test_mode() is False
    assert test_hooks.effective_rest_duration(2.5) == 2.5
    test_hooks.record_command_dispatched()
    assert test_hooks.get_metrics().commands_dispatched == 0


def test_effective_rest_capped_when_on(monkeypatch):
    monkeypatch.setenv("PIXIL_TEST_MODE", "1")
    monkeypatch.setenv("PIXIL_TEST_REST_CAP", "0.01")
    assert test_hooks.is_test_mode() is True
    assert test_hooks.effective_rest_duration(5.0) == 0.01


def test_summary_line_format(monkeypatch):
    monkeypatch.setenv("PIXIL_TEST_MODE", "1")
    test_hooks.reset_metrics("testing/foo.pix")
    test_hooks.record_command_dispatched()
    test_hooks.set_buffer_hash("abc123")
    line = test_hooks.get_metrics().format_summary_line(0)
    assert line.startswith("PIXIL_TEST_SUMMARY ")
    assert "script=testing/foo.pix" in line
    assert "commands=1" in line
    assert "buffer=abc123" in line
    assert "failures=0" in line
    assert "exit=0" in line
