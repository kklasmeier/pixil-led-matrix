"""Loop compiler v0 — parse and run metaballs-style blocks."""

from pixil_utils.loop_compiler import (
    CommandStmt,
    try_compile_loop_block,
    try_compile_procedure_block,
    run_compiled_loop_body,
    run_compiled_block,
    make_loop_context,
    reset_loop_compiler_stats,
)
from pixil_utils.math_functions import evaluate_math_expression
from pixil_utils.optimization_flags import ENABLE_COMPILED_LOOPS
from pixil_utils.variable_registry import VariableRegistry
from pixil_utils.array_manager import PixilArray
import pixil_utils.optimization_flags as flags


def test_compile_metaballs_inner_structure():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    block = [
        "for v_x in (0, 3, 1)",
        "v_sum = 0",
        "for v_i in (0, 2, 1)",
        "v_dx = v_x - v_pos_x[v_i]",
        "v_dy = v_y - v_pos_y[v_i]",
        "v_sum = v_sum + (v_radius[v_i] * v_radius[v_i]) / max((v_dx * v_dx + v_dy * v_dy), 1)",
        "endfor v_i",
        "if v_sum > 1 then",
        "v_color = min(v_sum * 15, 95)",
        "mplot(v_x, v_y, v_color, 75)",
        "endif",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    assert len(compiled.statements) == 1
    flags.ENABLE_COMPILED_LOOPS = False


def test_run_small_grid_mplot_count():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    variables = VariableRegistry()
    variables.scan_and_register(["v_x", "v_y", "v_i", "v_sum", "v_color", "v_dx", "v_dy"])
    variables.set("v_pos_x", PixilArray(3))
    variables.set("v_pos_y", PixilArray(3))
    variables.set("v_radius", PixilArray(3))
    for i in range(3):
        variables.get("v_pos_x")[i] = 10 + i
        variables.get("v_pos_y")[i] = 10 + i
        variables.get("v_radius")[i] = 12
    plots = []

    def capture_mplot(x, y, color, intensity):
        plots.append((x, y, color, intensity))

    block = [
        "for v_x in (0, 3, 1)",
        "v_sum = 0",
        "for v_i in (0, 2, 1)",
        "v_dx = v_x - v_pos_x[v_i]",
        "v_dy = v_y - v_pos_y[v_i]",
        "v_sum = v_sum + (v_radius[v_i] * v_radius[v_i]) / max((v_dx * v_dx + v_dy * v_dy), 1)",
        "endfor v_i",
        "if v_sum > 1 then",
        "mplot(v_x, v_y, 50, 75)",
        "endif",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    variables.set("v_y", 10)
    ctx = make_loop_context(variables, capture_mplot, lambda: False)
    run_compiled_loop_body(compiled, "v_y", 10.0, 10.0, 1.0, ctx)
    assert len(plots) > 0
    flags.ENABLE_COMPILED_LOOPS = False


def test_mplot_named_color_white():
    flags.ENABLE_COMPILED_LOOPS = True
    plots = []

    def capture_mplot(x, y, color, intensity):
        plots.append((x, y, color, intensity))

    block = [
        "mplot(10, 10, white, 40)",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    variables = VariableRegistry()
    variables.scan_and_register(["v_x", "v_y"])
    ctx = make_loop_context(variables, capture_mplot, lambda: False)
    run_compiled_block(compiled, ctx)
    assert len(plots) == 1
    assert plots[0] == (10, 10, "white", 40)
    flags.ENABLE_COMPILED_LOOPS = False


def test_mplot_quoted_named_color_is_stripped():
    """Regression: quoted named colors like "white" must work in compiled mplot."""
    flags.ENABLE_COMPILED_LOOPS = True
    plots = []

    def capture_mplot(x, y, color, intensity, burnout=None, burnout_mode=None):
        plots.append((x, y, color, intensity, burnout, burnout_mode))

    block = [
        'mplot(10, 10, "white", 40)',
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    variables = VariableRegistry()
    ctx = make_loop_context(variables, capture_mplot, lambda: False)
    run_compiled_block(compiled, ctx)
    assert plots == [(10, 10, "white", 40, None, None)]
    flags.ENABLE_COMPILED_LOOPS = False


def test_mplot_burnout_in_compiled_loop():
    """Regression: compiled mplot must pass burnout so pixels turn off."""
    flags.ENABLE_COMPILED_LOOPS = True
    plots = []

    def capture_mplot(x, y, color, intensity, burnout=None, burnout_mode=None):
        plots.append((x, y, color, intensity, burnout, burnout_mode))

    block = [
        "for v_x in (0, 1, 1)",
        'mplot(v_x, 5, "white", 40, 30)',
        "endfor v_x",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    variables = VariableRegistry()
    variables.scan_and_register(["v_x"])
    ctx = make_loop_context(variables, capture_mplot, lambda: False)
    run_compiled_block(compiled, ctx)
    assert plots == [(0, 5, "white", 40, 30, None), (1, 5, "white", 40, 30, None)]
    flags.ENABLE_COMPILED_LOOPS = False


def test_mplot_fade_burnout_mode_in_compiled_loop():
    """Regression: burnout_mode 'fade' must not go through evaluate_math_expression."""
    flags.ENABLE_COMPILED_LOOPS = True
    plots = []

    def capture_mplot(x, y, color, intensity, burnout=None, burnout_mode=None):
        plots.append((x, y, color, intensity, burnout, burnout_mode))

    block = [
        "mplot(10, 20, white, 50, 100, fade)",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    variables = VariableRegistry()
    ctx = make_loop_context(variables, capture_mplot, lambda: False)
    run_compiled_block(compiled, ctx)
    assert plots == [(10, 20, "white", 50, 100, "fade")]
    flags.ENABLE_COMPILED_LOOPS = False


def test_mplot_accepts_float_spectral_color():
    flags.ENABLE_COMPILED_LOOPS = True
    from shared.mplot_protocol import normalize_mplot_color

    assert normalize_mplot_color(42.7) == 43
    assert normalize_mplot_color("cyan") == "cyan"
    flags.ENABLE_COMPILED_LOOPS = False


def test_bare_procedure_name_still_falls_back():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    block = [
        "calculate_distance",
    ]
    assert try_compile_loop_block(block) is None
    flags.ENABLE_COMPILED_LOOPS = False


def test_call_keyword_compiles_in_loop():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    from pixil_utils.loop_compiler import CallStmt

    block = ["call foo"]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    assert isinstance(compiled.statements[0], CallStmt)
    assert compiled.statements[0].proc_name == "foo"
    flags.ENABLE_COMPILED_LOOPS = False


def test_literal_loop_bounds_skip_eval():
    """(0, 3, 1) bounds are folded at compile time — eval_expr not used for bounds."""
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    block = [
        "for v_x in (0, 3, 1)",
        "v_sum = v_sum + v_x",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    for_stmt = compiled.statements[0]
    assert for_stmt.const_start == 0.0
    assert for_stmt.const_end == 3.0
    assert for_stmt.const_step == 1.0

    variables = VariableRegistry()
    variables.scan_and_register(["v_x", "v_sum"])
    variables.set("v_sum", 0)

    def bounds_must_not_eval(expr: str):
        if expr.strip() in ("0", "3", "1"):
            raise AssertionError(f"literal loop bound should be folded: {expr!r}")
        return evaluate_math_expression(expr, variables)

    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    ctx.eval_expr = bounds_must_not_eval  # type: ignore[method-assign]
    run_compiled_block(compiled, ctx)
    assert variables.get("v_sum") == 6.0
    flags.ENABLE_COMPILED_LOOPS = False


def test_variable_loop_bounds_still_eval():
    flags.ENABLE_COMPILED_LOOPS = True
    block = [
        "for v_i in (0, v_end, 1)",
        "v_acc = v_acc + 1",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    for_stmt = compiled.statements[0]
    assert for_stmt.const_start is None
    assert for_stmt.const_end is None
    assert for_stmt.const_step is None

    variables = VariableRegistry()
    variables.scan_and_register(["v_i", "v_end", "v_acc"])
    variables.set("v_end", 2)
    variables.set("v_acc", 0)
    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    run_compiled_block(compiled, ctx)
    assert variables.get("v_acc") == 3.0
    flags.ENABLE_COMPILED_LOOPS = False


def test_nested_literal_bounds_inner_for():
    """Metaballs-style outer loop with literal inner (0, 2, 1)."""
    flags.ENABLE_COMPILED_LOOPS = True
    block = [
        "for v_y in (0, 1, 1)",
        "for v_x in (0, 2, 1)",
        "v_sum = v_sum + 1",
        "endfor v_x",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    outer = compiled.statements[0]
    inner = outer.body[0]
    assert outer.const_start == 0.0 and outer.const_end == 1.0
    assert inner.const_start == 0.0 and inner.const_end == 2.0

    eval_count = {"n": 0}
    orig_eval = evaluate_math_expression

    def counting_eval(expr, variables):
        eval_count["n"] += 1
        return orig_eval(expr, variables)

    variables = VariableRegistry()
    variables.scan_and_register(["v_x", "v_y", "v_sum"])
    variables.set("v_sum", 0)
    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    ctx.eval_expr = lambda e: counting_eval(e, variables)  # type: ignore[method-assign]
    run_compiled_block(compiled, ctx)
    # body assign only: 3 cells * 2 rows = 6 evals for v_sum = v_sum + 1
    assert variables.get("v_sum") == 6.0
    assert eval_count["n"] == 6
    flags.ENABLE_COMPILED_LOOPS = False


def test_begin_frame_false_literal_parsing():
    """begin_frame(false) must not use bool('false') which is True in Python."""
    from pixil_utils.parameter_types import parse_bool_literal

    assert parse_bool_literal("false") is False
    assert parse_bool_literal("true") is True
    assert bool("false") is True  # why compiled path avoids bool(parse_value(...))


def test_loop_begin_frame_false_compiles():
    flags.ENABLE_COMPILED_LOOPS = True
    block = ["begin_frame(false)", "end_frame"]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    commands = []

    def capture(cmd_name, arg_exprs):
        commands.append((cmd_name, list(arg_exprs)))

    variables = VariableRegistry()
    ctx = make_loop_context(
        variables, lambda *a: None, lambda: False, run_command=capture,
    )
    run_compiled_block(compiled, ctx)
    assert commands[0] == ("begin_frame", ["false"])
    from pixil_utils.parameter_types import parse_bool_literal

    assert parse_bool_literal(commands[0][1][0]) is False
    flags.ENABLE_COMPILED_LOOPS = False


def test_loop_chladni_style_begin_frame_plot_end_frame():
    """Chladni inner loop: begin_frame(false), plot with literals, end_frame."""
    from pixil_utils.loop_compiler import PlotStmt
    from pixil_utils.parameter_types import parse_bool_literal

    flags.ENABLE_COMPILED_LOOPS = True
    block = [
        "begin_frame(false)",
        "plot(32, 32, white, 100)",
        "end_frame",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    assert isinstance(compiled.statements[1], PlotStmt)

    frame_starts: list[bool] = []
    plots: list[tuple] = []

    def run_command(cmd_name, arg_exprs):
        if cmd_name == "begin_frame":
            preserve = False
            if arg_exprs:
                preserve = parse_bool_literal(arg_exprs[0])
            frame_starts.append(preserve)

    def capture_mplot(x, y, color, intensity, burnout=None, burnout_mode=None):
        plots.append((x, y, color, intensity))

    variables = VariableRegistry()
    ctx = make_loop_context(
        variables,
        capture_mplot,
        lambda: False,
        run_command=run_command,
    )
    run_compiled_block(compiled, ctx)
    assert frame_starts == [False]
    assert plots == [(32, 32, "white", 100)]
    flags.ENABLE_COMPILED_LOOPS = False


def test_loop_draw_circle_compiles_and_invokes_run_command():
    flags.ENABLE_COMPILED_LOOPS = True
    from pixil_utils.loop_compiler import DrawCircleStmt
    # Inner body only — Pixil wraps with run_compiled_loop_body (see Pixil.py for loop)
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
    assert len(circles) == 3
    assert all(c[2] == 3 for c in circles)
    flags.ENABLE_COMPILED_LOOPS = False


def test_loop_elseif_draw_shape_branches():
    """Expanding_Circles-style shape dispatch in a compiled loop."""
    flags.ENABLE_COMPILED_LOOPS = True
    block = [
        "if v_shape[v_i] == 0 then",
        "draw_polygon(10, 10, 4, 5, 20, 80, 0, false)",
        "elseif v_shape[v_i] == 1 then",
        "draw_polygon(10, 10, 4, 7, 30, 80, 0, false)",
        "else",
        "draw_circle(10, 10, 4, 40, 80, false)",
        "endif",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None

    commands = []

    def capture_command(cmd_name, arg_exprs):
        commands.append(cmd_name)

    variables = VariableRegistry()
    variables.scan_and_register(["v_i", "v_shape"])
    variables.set("v_shape", PixilArray(3))
    variables.get("v_shape")[0] = 0
    variables.get("v_shape")[1] = 1
    variables.get("v_shape")[2] = 2

    ctx = make_loop_context(
        variables, lambda *a: None, lambda: False, run_command=capture_command,
    )
    run_compiled_loop_body(compiled, "v_i", 0.0, 2.0, 1.0, ctx)
    assert commands == ["draw_polygon", "draw_polygon", "draw_circle"]
    flags.ENABLE_COMPILED_LOOPS = False


def test_loop_call_inside_if_compiles():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    block = [
        "for v_j in (0, 2, 1)",
        "if v_i != v_j then",
        "call calculate_distance",
        "endif",
        "endfor v_j",
    ]
    assert try_compile_loop_block(block) is not None
    flags.ENABLE_COMPILED_LOOPS = False


def test_loop_array_assign_compiles():
    flags.ENABLE_COMPILED_LOOPS = True
    block = [
        "v_radius[v_i] = v_radius[v_i] + v_growth_speed",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    variables = VariableRegistry()
    variables.scan_and_register(["v_i", "v_radius", "v_growth_speed"])
    variables.set("v_radius", PixilArray(3))
    variables.get("v_radius")[0] = 1.0
    variables.get("v_radius")[1] = 2.0
    variables.get("v_radius")[2] = 3.0
    variables.set("v_growth_speed", 0.5)
    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    run_compiled_loop_body(compiled, "v_i", 0.0, 2.0, 1.0, ctx)
    assert variables.get("v_radius")[0] == 1.5
    assert variables.get("v_radius")[2] == 3.5
    flags.ENABLE_COMPILED_LOOPS = False


def test_expanding_circles_draw_loop_compiles():
    """Regression: main draw/update for in Expanding_Circles.pix (inner body only)."""
    flags.ENABLE_COMPILED_LOOPS = True
    body = [
        "if v_active[v_i] == 1 then",
        "v_draw_x = round(v_center_x[v_i])",
        "v_draw_y = round(v_center_y[v_i])",
        "v_draw_radius = round(v_radius[v_i])",
        "if v_draw_radius >= 1 then",
        "if v_shape[v_i] == 0 then",
        "draw_polygon(v_draw_x, v_draw_y, v_draw_radius, 5, v_color[v_i], 80, 0, false)",
        "elseif v_shape[v_i] == 1 then",
        "draw_polygon(v_draw_x, v_draw_y, v_draw_radius, 7, v_color[v_i], 80, 0, false)",
        "elseif v_shape[v_i] == 2 then",
        "draw_polygon(v_draw_x, v_draw_y, v_draw_radius, 9, v_color[v_i], 80, 0, false)",
        "else",
        "draw_circle(v_draw_x, v_draw_y, v_draw_radius, v_color[v_i], 80, false)",
        "endif",
        "endif",
        "v_radius[v_i] = v_radius[v_i] + v_growth_speed",
        "if v_radius[v_i] > 45 then",
        "v_active[v_i] = 0",
        "endif",
        "endif",
    ]
    assert try_compile_loop_block(body) is not None
    flags.ENABLE_COMPILED_LOOPS = False


def test_procedure_block_skips_hash_comments():
    """Regression: # comments in def bodies must not block compilation."""
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "# setup",
        "v_best_dist = 9999",
        "for v_i in (0, 2, 1)",
        "v_best_dist = v_best_dist + v_i",
        "endfor v_i",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    flags.ENABLE_COMPILED_PROCEDURES = False
