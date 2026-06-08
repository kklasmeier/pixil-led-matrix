"""Compiled draw_line / draw_circle / draw_polygon / draw_arc fast paths and reusable ExecContext."""

from pixil_utils import optimization_flags as flags
from pixil_utils.loop_compiler import (
    DrawArcStmt,
    DrawCircleStmt,
    DrawLineStmt,
    DrawPolygonStmt,
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


def test_draw_polygon_in_compiled_procedure_uses_draw_polygon_stmt():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "draw_polygon(32, 32, 4, 6, purple, 80, 30, true)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    assert isinstance(compiled.statements[0], DrawPolygonStmt)
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_draw_polygon_stmt_uses_draw_polygon_fn_when_provided():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "draw_polygon(v_x, v_y, v_size, 3, v_color, v_bright, v_angle, true)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None

    polygons = []
    commands = []

    def capture_draw_polygon(
        x, y, radius, sides, color, intensity, rotation, filled,
        burnout=None, burnout_mode=None,
    ):
        polygons.append((x, y, radius, sides, color, intensity, rotation, filled))

    def capture_command(cmd_name, arg_exprs):
        commands.append((cmd_name, list(arg_exprs)))

    variables = VariableRegistry()
    variables.scan_and_register(["v_x", "v_y", "v_size", "v_color", "v_bright", "v_angle"])
    variables.set("v_x", 10)
    variables.set("v_y", 20)
    variables.set("v_size", 3)
    variables.set("v_color", "red")
    variables.set("v_bright", 75)
    variables.set("v_angle", 45)

    ctx = make_loop_context(
        variables,
        lambda *a: None,
        lambda: False,
        run_command=capture_command,
        draw_polygon_fn=capture_draw_polygon,
    )
    run_compiled_block(compiled, ctx)
    assert polygons == [(10, 20, 3, 3, "red", 75, 45.0, True)]
    assert commands == []
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_draw_polygon_legacy_omitted_intensity():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "draw_polygon(32, 32, 4, 5, yellow, 15, false)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    stmt = compiled.statements[0]
    assert isinstance(stmt, DrawPolygonStmt)
    assert stmt.intensity_expr == "100"
    assert stmt.rotation_expr == "15"
    assert stmt.filled_expr == "false"

    polygons = []

    def capture_draw_polygon(
        x, y, radius, sides, color, intensity, rotation, filled,
        burnout=None, burnout_mode=None,
    ):
        polygons.append((x, y, radius, sides, color, intensity, rotation, filled))

    variables = VariableRegistry()
    ctx = make_loop_context(
        variables, lambda *a: None, lambda: False, draw_polygon_fn=capture_draw_polygon,
    )
    run_compiled_block(compiled, ctx)
    assert polygons == [(32, 32, 4, 5, "yellow", 100, 15.0, False)]
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_draw_arc_in_compiled_procedure_uses_draw_arc_stmt():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "draw_arc(10, 20, 30, 40, 5, cyan, 60, false)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    assert isinstance(compiled.statements[0], DrawArcStmt)
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_draw_arc_stmt_uses_draw_arc_fn_when_provided():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "draw_arc(v_x1, v_y1, v_x2, v_y2, v_bulge, v_color, v_bright, false)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None

    arcs = []
    commands = []

    def capture_draw_arc(
        x1, y1, x2, y2, bulge, color, intensity, filled,
        burnout=None, burnout_mode=None,
    ):
        arcs.append((x1, y1, x2, y2, bulge, color, intensity, filled))

    def capture_command(cmd_name, arg_exprs):
        commands.append((cmd_name, list(arg_exprs)))

    variables = VariableRegistry()
    variables.scan_and_register(
        ["v_x1", "v_y1", "v_x2", "v_y2", "v_bulge", "v_color", "v_bright"],
    )
    variables.set("v_x1", 1)
    variables.set("v_y1", 2)
    variables.set("v_x2", 10)
    variables.set("v_y2", 20)
    variables.set("v_bulge", -3.5)
    variables.set("v_color", "navy")
    variables.set("v_bright", 25)

    ctx = make_loop_context(
        variables,
        lambda *a: None,
        lambda: False,
        run_command=capture_command,
        draw_arc_fn=capture_draw_arc,
    )
    run_compiled_block(compiled, ctx)
    assert arcs == [(1, 2, 10, 20, -3.5, "navy", 25, False)]
    assert commands == []
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_draw_arc_in_compiled_loop():
    flags.ENABLE_COMPILED_LOOPS = True
    block = [
        "draw_arc(v_i, 5, v_i + 10, 15, 2, white, 80, false)",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    assert isinstance(compiled.statements[0], DrawArcStmt)

    arcs = []

    def capture_draw_arc(
        x1, y1, x2, y2, bulge, color, intensity, filled,
        burnout=None, burnout_mode=None,
    ):
        arcs.append((x1, y1, x2, y2, bulge, color, intensity, filled))

    variables = VariableRegistry()
    variables.scan_and_register(["v_i"])
    ctx = make_loop_context(
        variables, lambda *a: None, lambda: False, draw_arc_fn=capture_draw_arc,
    )
    run_compiled_loop_body(compiled, "v_i", 0.0, 1.0, 1.0, ctx)
    assert arcs == [
        (0, 5, 10, 15, 2.0, "white", 80, False),
        (1, 5, 11, 15, 2.0, "white", 80, False),
    ]
    flags.ENABLE_COMPILED_LOOPS = False


def test_kaleidoscope_draw_wedges_compiles():
    """Regression: draw_wedges from Kaleidoscope_Tumbler.pix must compile (uses draw_arc)."""
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "v_wedge_inten = v_wedge_intensity * v_fade_multiplier / 100",
        "for v_wi in (0, v_symmetry - 1, 1)",
        "v_wi2 = v_wi + 1",
        "v_x1 = v_wedge_x[v_wi]",
        "v_y1 = v_wedge_y[v_wi]",
        "v_x2 = v_wedge_x[v_wi2]",
        "v_y2 = v_wedge_y[v_wi2]",
        "v_color = v_wedge_color[v_wi]",
        "draw_line(v_center_x, v_center_y, v_x1, v_y1, v_color, v_wedge_inten)",
        "draw_line(v_center_x, v_center_y, v_x2, v_y2, v_color, v_wedge_inten)",
        "draw_arc(v_x1, v_y1, v_x2, v_y2, v_wedge_bulge[v_wi], v_color, v_wedge_inten, false)",
        "endfor v_wi",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    draw_stmts = [
        s for s in compiled.statements[1].body
        if isinstance(s, (DrawLineStmt, DrawArcStmt))
    ]
    assert len(draw_stmts) == 3
    assert isinstance(draw_stmts[2], DrawArcStmt)
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_kaleidoscope_draw_at_segment_compiles():
    """Regression: draw_at_segment uses draw_polygon and draw_circle fast paths."""
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "v_col_i = v_obj_color_idx[v_di]",
        "v_draw_color = v_pal_colors[v_col_i]",
        "v_obj_inten = v_obj_intensity[v_di]",
        "v_draw_inten = v_obj_inten * v_fade_multiplier / 100",
        "if v_motion_mode == 1 or v_motion_mode == 2 then",
        "v_draw_inten = v_draw_inten * v_obj_fade_mul[v_di]",
        "endif",
        "v_draw_size = v_obj_size[v_di]",
        "v_draw_angle = v_obj_angle[v_di]",
        "v_draw_shape = v_obj_shape[v_di]",
        "if v_draw_shape == 1 then",
        "draw_circle(v_dx, v_dy, v_draw_size, v_draw_color, v_draw_inten, true)",
        "endif",
        "if v_draw_shape == 2 then",
        "draw_polygon(v_dx, v_dy, v_draw_size, 3, v_draw_color, v_draw_inten, v_draw_angle, true)",
        "endif",
        "if v_draw_shape == 3 then",
        "draw_polygon(v_dx, v_dy, v_draw_size, 6, v_draw_color, v_draw_inten, v_draw_angle, true)",
        "endif",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    flags.ENABLE_COMPILED_PROCEDURES = False
