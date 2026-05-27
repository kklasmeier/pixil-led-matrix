"""Compiled while loops."""

import pixil_utils.optimization_flags as flags
from pixil_utils.loop_compiler import (
    CallStmt,
    try_compile_loop_block,
    try_compile_procedure_block,
    run_compiled_while_body,
    run_compiled_block,
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


def test_compiled_while_invokes_call():
    """Ink-style: while body calls a compiled procedure each iteration."""
    flags.ENABLE_COMPILED_LOOPS = True
    flags.ENABLE_COMPILED_PROCEDURES = True
    reset_loop_compiler_stats()

    proc = try_compile_procedure_block(["v_ticks = v_ticks + 1"])
    assert proc is not None

    while_body = try_compile_loop_block(["call tick_proc"])
    assert while_body is not None
    assert isinstance(while_body.statements[0], CallStmt)

    variables = VariableRegistry()
    variables.scan_and_register(["v_ticks", "v_limit"])
    variables.set("v_ticks", 0)
    variables.set("v_limit", 4)

    def call_procedure(name):
        assert name == "tick_proc"
        run_compiled_block(proc, proc_ctx)

    proc_ctx = make_loop_context(
        variables, lambda *a: None, lambda: False, call_procedure=call_procedure
    )
    loop_ctx = make_loop_context(
        variables,
        lambda *a: None,
        lambda: False,
        call_procedure=call_procedure,
    )
    run_compiled_while_body(while_body, "v_ticks < v_limit", loop_ctx)
    assert variables.get("v_ticks") == 4

    flags.ENABLE_COMPILED_LOOPS = False
    flags.ENABLE_COMPILED_PROCEDURES = False


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
