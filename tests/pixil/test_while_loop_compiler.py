"""Compiled while loops."""

import pixil_utils.optimization_flags as flags
from pixil_utils.loop_compiler import (
    try_compile_loop_block,
    run_compiled_while_body,
    make_loop_context,
    reset_loop_compiler_stats,
)
from pixil_utils.variable_registry import VariableRegistry


def test_compile_while_with_begin_end_frame():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    block = [
        "v_n = 0",
        "begin_frame(true)",
        "v_n = v_n + 1",
        "end_frame",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    flags.ENABLE_COMPILED_LOOPS = False


def test_run_while_condition_stops():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    variables = VariableRegistry()
    variables.scan_and_register(["v_n", "v_limit"])
    variables.set("v_limit", 3)
    frame_starts = []

    def run_command(cmd_name, arg_exprs):
        if cmd_name == "begin_frame":
            frame_starts.append(1)

    block = [
        "v_n = v_n + 1",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    variables.set("v_n", 0)
    ctx = make_loop_context(
        variables,
        lambda *a: None,
        lambda: False,
        run_command=run_command,
    )
    run_compiled_while_body(compiled, "v_n < v_limit", ctx)
    assert variables.get("v_n") == 3
    flags.ENABLE_COMPILED_LOOPS = False


def test_compile_nested_while_for_sprite_ops():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    block = [
        "for v_i in (0, 2, 1)",
        "move_sprite(ball_sprite, v_i, v_i, v_i)",
        "endfor v_i",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    flags.ENABLE_COMPILED_LOOPS = False
