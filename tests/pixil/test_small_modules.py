"""cli, timer_manager, optimization_flags, regex_patterns, debug."""

import argparse
import re
import sys
import time

import pytest

from pixil_utils import debug as debug_mod
from pixil_utils import optimization_flags as opt
from pixil_utils import regex_patterns as rx
from pixil_utils import timer_manager as timer
from pixil_utils.cli import validate_debug_level, validate_time_format


def test_validate_time_format_mm_ss():
    assert validate_time_format("2:30") == 150
    assert validate_time_format(None) is None


def test_validate_time_format_rejects_bad_seconds():
    with pytest.raises(argparse.ArgumentTypeError, match="mm:ss"):
        validate_time_format("2:60")


def test_validate_debug_level():
    from pixil_utils.debug import DEBUG_SUMMARY, DEBUG_VERBOSE

    assert validate_debug_level("DEBUG_VERBOSE") == DEBUG_VERBOSE
    assert validate_debug_level("debug_summary") == DEBUG_SUMMARY


def test_validate_debug_level_invalid():
    with pytest.raises(argparse.ArgumentTypeError):
        validate_debug_level("LOUD")


def test_timer_expiry(monkeypatch):
    timer.clear_timer()
    now = [1000.0]

    def fake_time():
        return now[0]

    monkeypatch.setattr(timer.time, "time", fake_time)
    timer.initialize_timer(10)
    assert timer.is_time_expired() is False
    now[0] += 11
    assert timer.is_time_expired() is True
    timer.clear_timer()
    assert timer.is_time_expired() is False


def test_timer_unlimited_never_expires(monkeypatch):
    timer.clear_timer()
    monkeypatch.setattr(timer.time, "time", lambda: 99999.0)
    timer.initialize_timer(None)
    assert timer.is_time_expired() is False
    assert timer.get_remaining_time() is None


def test_force_timer_expired():
    timer.clear_timer()
    timer.initialize_timer(60)
    timer.force_timer_expired()
    assert timer.is_time_expired() is True


def test_is_time_expired_on_spacebar_skip(monkeypatch):
    timer.clear_timer()
    timer.initialize_timer(3600)
    monkeypatch.setattr(
        "pixil_utils.terminal_handler.consume_skip_request",
        lambda: True,
    )
    assert timer.is_time_expired() is True
    timer.clear_timer()


def test_consume_skip_request():
    from pixil_utils import terminal_handler as th

    th._skip_event.set()
    assert th.consume_skip_request() is True
    assert th.consume_skip_request() is False


def test_shutdown_request_and_reset():
    from pixil_utils import shutdown as sd

    sd.reset_shutdown()
    assert sd.shutdown_requested() is False
    sd.request_shutdown()
    assert sd.shutdown_requested() is True
    sd.reset_shutdown()
    assert sd.shutdown_requested() is False


def test_set_profile_only_working_keeps_jit_off():
    opt.set_profile_only_working()
    assert opt.ENABLE_JIT is False
    assert opt.ENABLE_FAST_MATH is True


def test_set_profile_all_off_disables_condition_templates():
    opt.set_profile_all_off()
    assert opt.ENABLE_CONDITION_TEMPLATES is False
    opt.set_profile_only_working()


def test_fast_path_regex_patterns_match_samples():
    assert rx.FAST_SIMPLE_ARRAY_PATTERN.match("v_data[v_i]")
    assert rx.FAST_VAR_PLUS_NUM_PATTERN.match("v_x + 5")
    assert rx.FAST_VAR_MUL_VAR_PATTERN.match("v_a * v_b")
    assert rx.FAST_NUM_PLUS_VAR_PATTERN.match("5 + v_x")
    assert rx.COMMAND_PATTERN.match("plot(10, 20, red)")
    assert rx.IF_PATTERN.match("if v_x > 5 then")


def test_debug_print_respects_level(capsys):
    debug_mod.set_debug_level(debug_mod.DEBUG_OFF)
    debug_mod.debug_print("hidden", debug_mod.DEBUG_CONCISE)
    assert capsys.readouterr().out == ""

    debug_mod.set_debug_level(debug_mod.DEBUG_VERBOSE)
    debug_mod.debug_print("visible", debug_mod.DEBUG_CONCISE)
    assert "visible" in capsys.readouterr().out
    debug_mod.set_debug_level(debug_mod.DEBUG_VERBOSE)
