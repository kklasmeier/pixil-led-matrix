"""Compiled procedure v0 tests."""

import pixil_utils.optimization_flags as flags
from pixil_utils.loop_compiler import (
    try_compile_procedure_block,
    try_compile_loop_block,
    run_compiled_block,
    make_loop_context,
    reset_loop_compiler_stats,
)
from pixil_utils.variable_registry import VariableRegistry
from pixil_utils.array_manager import PixilArray


def test_procedure_array_assign_and_call():
    flags.ENABLE_COMPILED_PROCEDURES = True
    reset_loop_compiler_stats()

    helper = [
        "v_acc = v_pos_x[v_i] + 1",
    ]
    main = [
        "for v_i in (0, 2, 1)",
        "call helper_proc",
        "endfor v_i",
    ]
    assert try_compile_procedure_block(helper) is not None
    compiled = try_compile_procedure_block(main)
    assert compiled is not None

    variables = VariableRegistry()
    variables.scan_and_register(["v_i", "v_acc"])
    variables.set("v_pos_x", PixilArray(3))
    for i in range(3):
        variables.get("v_pos_x")[i] = float(i)

    calls = []

    def call_proc(name):
        calls.append(name)
        body = try_compile_procedure_block(helper)
        ctx = make_loop_context(variables, lambda *a: None, lambda: False, call_procedure=call_proc)
        run_compiled_block(body, ctx)

    ctx = make_loop_context(
        variables, lambda *a: None, lambda: False, call_procedure=call_proc,
    )
    run_compiled_block(compiled, ctx)
    assert calls == ["helper_proc", "helper_proc", "helper_proc"]
    assert variables.get("v_acc") == 3.0
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_procedure_if_else():
    flags.ENABLE_COMPILED_PROCEDURES = True
    reset_loop_compiler_stats()
    block = [
        "if v_x > 5 then",
        "v_y = 1",
        "else",
        "v_y = 2",
        "endif",
    ]
    assert try_compile_procedure_block(block) is not None
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_loop_rejects_bare_procedure_name():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    assert try_compile_loop_block(["draw_particles"]) is None
    flags.ENABLE_COMPILED_LOOPS = False


def test_loop_accepts_call_keyword():
    from pixil_utils.loop_compiler import CallStmt

    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    compiled = try_compile_loop_block(["call draw_particles"])
    assert compiled is not None
    assert len(compiled.statements) == 1
    assert isinstance(compiled.statements[0], CallStmt)
    assert compiled.statements[0].proc_name == "draw_particles"
    flags.ENABLE_COMPILED_LOOPS = False


def test_draw_boids_begin_frame_is_command_not_call():
    """begin_frame without () must not become CallStmt (no frame clear)."""
    flags.ENABLE_COMPILED_PROCEDURES = True
    from pixil_utils.loop_compiler import CallStmt, CommandStmt, try_compile_procedure_block

    body = [
        "begin_frame",
        "mflush",
        "end_frame",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    assert isinstance(compiled.statements[0], CommandStmt)
    assert compiled.statements[0].command_name == "begin_frame"
    assert not isinstance(compiled.statements[0], CallStmt)
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_procedure_rejects_print():
    flags.ENABLE_COMPILED_PROCEDURES = True
    reset_loop_compiler_stats()
    assert try_compile_procedure_block(['print("x")']) is None
    flags.ENABLE_COMPILED_PROCEDURES = False
