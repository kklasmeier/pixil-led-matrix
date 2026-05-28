"""Compiled plot() fast path (PlotStmt)."""

from pixil_utils import optimization_flags as flags
from pixil_utils.loop_compiler import (
    PlotStmt,
    make_loop_context,
    run_compiled_block,
    try_compile_procedure_block,
)
from pixil_utils.variable_registry import VariableRegistry


def test_plot_in_compiled_procedure_uses_plot_stmt():
    """Regression: plot() in loops should not use slow CommandStmt path."""
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "for v_n in (0, 2, 1)",
        "plot(v_n, v_n, white, 80)",
        "endfor v_n",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    assert isinstance(compiled.statements[0].body[0], PlotStmt)

    plots = []

    def capture_mplot(x, y, color, intensity, burnout=None, burnout_mode=None):
        plots.append((x, y, color, intensity))

    variables = VariableRegistry()
    ctx = make_loop_context(variables, capture_mplot, lambda: False)
    run_compiled_block(compiled, ctx)
    assert plots == [(0, 0, "white", 80), (1, 1, "white", 80), (2, 2, "white", 80)]
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_plot_stmt_uses_plot_fn_when_provided():
    """plot() in compiled blocks should use plot_fn, not mplot_fn."""
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "plot(10, 20, white, 50, 100, fade)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None

    plots = []
    mplots = []

    def capture_plot(x, y, color, intensity, burnout=None, burnout_mode=None):
        plots.append((x, y, color, intensity, burnout, burnout_mode))

    def capture_mplot(x, y, color, intensity, burnout=None, burnout_mode=None):
        mplots.append((x, y, color, intensity, burnout, burnout_mode))

    variables = VariableRegistry()
    ctx = make_loop_context(
        variables, capture_mplot, lambda: False, plot_fn=capture_plot,
    )
    run_compiled_block(compiled, ctx)
    assert plots == [(10, 20, "white", 50, 100, "fade")]
    assert mplots == []
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_plot_burnout_in_compiled_procedure():
    """Regression: plot() with burnout/fade must not be dropped by PlotStmt."""
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "plot(10, 20, white, 50, 100, fade)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None
    assert isinstance(compiled.statements[0], PlotStmt)
    assert compiled.statements[0].burnout_expr == "100"
    assert compiled.statements[0].burnout_mode_expr == "fade"

    plots = []

    def capture_mplot(x, y, color, intensity, burnout=None, burnout_mode=None):
        plots.append((x, y, color, intensity, burnout, burnout_mode))

    variables = VariableRegistry()
    ctx = make_loop_context(variables, capture_mplot, lambda: False)
    run_compiled_block(compiled, ctx)
    assert plots == [(10, 20, "white", 50, 100, "fade")]
    flags.ENABLE_COMPILED_PROCEDURES = False
