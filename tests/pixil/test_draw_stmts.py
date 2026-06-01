"""Compiled draw_line / draw_circle fast paths and reusable ExecContext."""

from pixil_utils import optimization_flags as flags
from pixil_utils.loop_compiler import (
    DrawCircleStmt,
    DrawLineStmt,
    ReusableLoopContext,
    make_loop_context,
    run_compiled_block,
    run_compiled_loop_body,
    try_compile_loop_block,
    try_compile_procedure_block,
)
from pixil_utils.variable_registry import VariableRegistry


def test_draw_line_in_compiled_procedure_uses_draw_line_stmt():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "draw_line(0, 0, 10, 10, cyan, 80)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    assert isinstance(compiled.statements[0], DrawLineStmt)
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_draw_line_stmt_uses_draw_line_fn_when_provided():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "draw_line(v_x, v_y, v_x + 5, v_y + 5, white, v_bright)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None

    lines = []
    commands = []

    def capture_draw_line(x0, y0, x1, y1, color, intensity, burnout=None, burnout_mode=None):
        lines.append((x0, y0, x1, y1, color, intensity))

    def capture_command(cmd_name, arg_exprs):
        commands.append((cmd_name, list(arg_exprs)))

    variables = VariableRegistry()
    variables.scan_and_register(["v_x", "v_y", "v_bright"])
    variables.set("v_x", 4)
    variables.set("v_y", 8)
    variables.set("v_bright", 70)

    ctx = make_loop_context(
        variables,
        lambda *a: None,
        lambda: False,
        run_command=capture_command,
        draw_line_fn=capture_draw_line,
    )
    run_compiled_block(compiled, ctx)
    assert lines == [(4, 8, 9, 13, "white", 70)]
    assert commands == []
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_draw_line_burnout_in_compiled_procedure():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "draw_line(1, 2, 3, 4, red, 50, 200, fade)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    stmt = compiled.statements[0]
    assert isinstance(stmt, DrawLineStmt)
    assert stmt.burnout_expr == "200"
    assert stmt.burnout_mode_expr == "fade"

    lines = []

    def capture_draw_line(x0, y0, x1, y1, color, intensity, burnout=None, burnout_mode=None):
        lines.append((x0, y0, x1, y1, color, intensity, burnout, burnout_mode))

    variables = VariableRegistry()
    ctx = make_loop_context(
        variables, lambda *a: None, lambda: False, draw_line_fn=capture_draw_line,
    )
    run_compiled_block(compiled, ctx)
    assert lines == [(1, 2, 3, 4, "red", 50, 200, "fade")]
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_draw_circle_in_compiled_procedure_uses_draw_circle_stmt():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "draw_circle(32, 32, 4, teal, v_bright, false)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    assert isinstance(compiled.statements[0], DrawCircleStmt)
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_draw_circle_stmt_uses_draw_circle_fn_when_provided():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "draw_circle(v_x, v_y, 3, black, 100, true)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None

    circles = []
    commands = []

    def capture_draw_circle(x, y, radius, color, intensity, filled, burnout=None, burnout_mode=None):
        circles.append((x, y, radius, color, intensity, filled))

    def capture_command(cmd_name, arg_exprs):
        commands.append((cmd_name, list(arg_exprs)))

    variables = VariableRegistry()
    variables.scan_and_register(["v_x", "v_y"])
    variables.set("v_x", 10)
    variables.set("v_y", 20)

    ctx = make_loop_context(
        variables,
        lambda *a: None,
        lambda: False,
        run_command=capture_command,
        draw_circle_fn=capture_draw_circle,
    )
    run_compiled_block(compiled, ctx)
    assert circles == [(10, 20, 3, "black", 100, True)]
    assert commands == []
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_draw_circle_legacy_omitted_intensity():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "draw_circle(32, 32, 4, teal, false)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    stmt = compiled.statements[0]
    assert isinstance(stmt, DrawCircleStmt)
    assert stmt.intensity_expr == "100"
    assert stmt.filled_expr == "false"

    circles = []

    def capture_draw_circle(x, y, radius, color, intensity, filled, burnout=None, burnout_mode=None):
        circles.append((x, y, radius, color, intensity, filled))

    variables = VariableRegistry()
    ctx = make_loop_context(
        variables, lambda *a: None, lambda: False, draw_circle_fn=capture_draw_circle,
    )
    run_compiled_block(compiled, ctx)
    assert circles == [(32, 32, 4, "teal", 100, False)]
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_draw_circle_in_compiled_loop():
    flags.ENABLE_COMPILED_LOOPS = True
    block = [
        "draw_circle(v_i, 5, 3, 50, 80, false)",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    assert isinstance(compiled.statements[0], DrawCircleStmt)

    circles = []

    def capture_draw_circle(x, y, radius, color, intensity, filled, burnout=None, burnout_mode=None):
        circles.append((x, y, radius, color, intensity, filled))

    variables = VariableRegistry()
    variables.scan_and_register(["v_i"])
    ctx = make_loop_context(
        variables, lambda *a: None, lambda: False, draw_circle_fn=capture_draw_circle,
    )
    run_compiled_loop_body(compiled, "v_i", 0.0, 2.0, 1.0, ctx)
    assert circles == [
        (0, 5, 3, 50, 80, False),
        (1, 5, 3, 50, 80, False),
        (2, 5, 3, 50, 80, False),
    ]
    flags.ENABLE_COMPILED_LOOPS = False


def test_reusable_loop_context_returns_same_instance():
    variables = VariableRegistry()
    pool = ReusableLoopContext(
        variables,
        lambda *a: None,
        lambda: False,
        plot_fn=lambda *a: None,
    )
    ctx1 = pool.get()
    ctx2 = pool.get()
    assert ctx1 is ctx2

    pool.reset()
    ctx3 = pool.get()
    assert ctx3 is not ctx1
