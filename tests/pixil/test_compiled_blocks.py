"""Regression tests for compiled loops and procedures (v0)."""

from pathlib import Path

import pytest

import pixil_utils.optimization_flags as flags
from pixil_utils.loop_compiler import (
    CallStmt,
    CommandStmt,
    try_compile_loop_block,
    try_compile_procedure_block,
    run_compiled_block,
    run_compiled_loop_body,
    make_loop_context,
    reset_loop_compiler_stats,
)
from pixil_utils.variable_registry import VariableRegistry
from pixil_utils.array_manager import PixilArray


@pytest.mark.parametrize("color", ["white", "cyan", "blue", "green", "yellow", "red"])
def test_mplot_named_colors_parametrized(color):
    """Named colors must not go through evaluate_math_expression (regression)."""
    flags.ENABLE_COMPILED_LOOPS = True
    plots = []

    def capture_mplot(x, y, c, intensity):
        plots.append((x, y, c, intensity))

    block = [f"mplot(5, 5, {color}, 50)"]
    compiled = try_compile_loop_block(block)
    assert compiled is not None

    variables = VariableRegistry()
    ctx = make_loop_context(variables, capture_mplot, lambda: False)
    run_compiled_block(compiled, ctx)
    assert plots == [(5, 5, color, 50)]
    flags.ENABLE_COMPILED_LOOPS = False


def test_mplot_named_color_in_compiled_procedure():
    """Earthquake-style: mplot(array[x], array[y], white, intensity) in a procedure."""
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "for v_st in (0, 1, 1)",
        "mplot(v_station_x[v_st], v_station_y[v_st], white, 40)",
        "mplot(v_noise_x, v_noise_y, blue, v_noise_intensity)",
        "endfor v_st",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None

    plots = []

    def capture_mplot(x, y, c, intensity):
        plots.append((x, y, c, intensity))

    variables = VariableRegistry()
    variables.scan_and_register(["v_st", "v_noise_x", "v_noise_y", "v_noise_intensity"])
    variables.set("v_station_x", PixilArray(2))
    variables.set("v_station_y", PixilArray(2))
    variables.get("v_station_x")[0] = 10
    variables.get("v_station_y")[0] = 20
    variables.get("v_station_x")[1] = 30
    variables.get("v_station_y")[1] = 40
    variables.set("v_noise_x", 5)
    variables.set("v_noise_y", 6)
    variables.set("v_noise_intensity", 15)

    ctx = make_loop_context(variables, capture_mplot, lambda: False)
    run_compiled_block(compiled, ctx)
    assert plots == [
        (10, 20, "white", 40),
        (5, 6, "blue", 15),
        (30, 40, "white", 40),
        (5, 6, "blue", 15),
    ]
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_mplot_expression_color_still_evaluates():
    """Variable/expression spectral colors must still evaluate (not treated as names)."""
    flags.ENABLE_COMPILED_LOOPS = True
    plots = []

    def capture_mplot(x, y, c, intensity):
        plots.append((x, y, c, intensity))

    block = [
        "v_sum = 2",
        "mplot(1, 1, v_sum * 15, 75)",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None

    variables = VariableRegistry()
    variables.scan_and_register(["v_sum"])
    ctx = make_loop_context(variables, capture_mplot, lambda: False)
    run_compiled_block(compiled, ctx)
    assert len(plots) == 1
    assert plots[0] == (1, 1, 30, 75)
    flags.ENABLE_COMPILED_LOOPS = False


def _boids_procedure_body(name: str) -> list[str]:
    """Extract procedure lines from Boids_Flocking_Simulation.pix."""
    text = Path(__file__).resolve().parents[2] / "scripts/main/Boids_Flocking_Simulation.pix"
    lines = text.read_text().splitlines()
    proc_lines: list[str] = []
    in_proc = False
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("def ") and line.endswith("{"):
            in_proc = line[4:-2].strip() == name
            proc_lines = []
            continue
        if in_proc and line == "}":
            return proc_lines
        if in_proc:
            proc_lines.append(line)
    raise AssertionError(f"procedure {name!r} not found")


def test_flags_off_skips_compilation():
    flags.ENABLE_COMPILED_LOOPS = False
    flags.ENABLE_COMPILED_PROCEDURES = False
    reset_loop_compiler_stats()
    assert try_compile_loop_block(["v_x = 1"]) is None
    assert try_compile_procedure_block(["v_x = 1"]) is None


def test_procedure_if_else_execution():
    flags.ENABLE_COMPILED_PROCEDURES = True
    reset_loop_compiler_stats()
    block = [
        "if v_x > 5 then",
        "v_y = 1",
        "else",
        "v_y = 2",
        "endif",
    ]
    compiled = try_compile_procedure_block(block)
    assert compiled is not None

    variables = VariableRegistry()
    variables.scan_and_register(["v_x", "v_y"])

    variables.set("v_x", 10)
    variables.set("v_y", 0)
    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    run_compiled_block(compiled, ctx)
    assert variables.get("v_y") == 1

    variables.set("v_x", 1)
    variables.set("v_y", 0)
    run_compiled_block(compiled, ctx)
    assert variables.get("v_y") == 2
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_procedure_elseif_chain_execution():
    flags.ENABLE_COMPILED_PROCEDURES = True
    block = [
        "if v_x < 3 then",
        "v_out = 1",
        "elseif v_x < 6 then",
        "v_out = 2",
        "else",
        "v_out = 3",
        "endif",
    ]
    compiled = try_compile_procedure_block(block)
    assert compiled is not None

    variables = VariableRegistry()
    variables.scan_and_register(["v_x", "v_out"])
    ctx = make_loop_context(variables, lambda *a: None, lambda: False)

    for v_x, expected in [(1, 1), (4, 2), (9, 3)]:
        variables.set("v_x", v_x)
        run_compiled_block(compiled, ctx)
        assert variables.get("v_out") == expected
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_frame_commands_sequence():
    """begin_frame / mflush / end_frame must invoke run_command, not CallStmt."""
    flags.ENABLE_COMPILED_PROCEDURES = True
    compiled = try_compile_procedure_block(["begin_frame", "mflush", "end_frame"])
    assert compiled is not None
    for stmt in compiled.statements:
        assert not isinstance(stmt, CallStmt)
        assert isinstance(stmt, CommandStmt)

    commands: list[tuple[str, list]] = []

    def capture(cmd_name, arg_exprs):
        commands.append((cmd_name, list(arg_exprs)))

    variables = VariableRegistry()
    ctx = make_loop_context(
        variables, lambda *a: None, lambda: False, run_command=capture,
    )
    run_compiled_block(compiled, ctx)
    assert [c[0] for c in commands] == ["begin_frame", "mflush", "end_frame"]
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_boids_key_procedures_compile():
    """Smoke-compile real Boids procedures (no hardware)."""
    flags.ENABLE_COMPILED_PROCEDURES = True
    reset_loop_compiler_stats()
    assert try_compile_procedure_block(_boids_procedure_body("calculate_distance")) is not None
    assert try_compile_procedure_block(_boids_procedure_body("apply_flocking_rules")) is not None
    assert try_compile_procedure_block(_boids_procedure_body("update_boids")) is not None
    draw = try_compile_procedure_block(_boids_procedure_body("draw_boids"))
    assert draw is not None
    assert isinstance(draw.statements[0], CommandStmt)
    assert draw.statements[0].command_name == "begin_frame"
    # update_dynamics uses print — must fall back
    assert try_compile_procedure_block(_boids_procedure_body("update_dynamics")) is None
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_nested_loop_array_assign_matches_interpreter_math():
    """Procedure nested for + array read/write (Boids-style)."""
    flags.ENABLE_COMPILED_PROCEDURES = True
    block = [
        "for v_i in (0, 2, 1)",
        "for v_j in (0, 1, 1)",
        "v_acc[v_i] = v_acc[v_i] + v_src[v_j]",
        "endfor v_j",
        "endfor v_i",
    ]
    compiled = try_compile_procedure_block(block)
    assert compiled is not None

    variables = VariableRegistry()
    variables.scan_and_register(["v_i", "v_j", "v_acc", "v_src"])
    variables.set("v_acc", PixilArray(3))
    variables.set("v_src", PixilArray(2))
    for i in range(3):
        variables.get("v_acc")[i] = 0.0
    variables.get("v_src")[0] = 1.0
    variables.get("v_src")[1] = 2.0

    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    run_compiled_block(compiled, ctx)
    assert variables.get("v_acc")[0] == 3.0
    assert variables.get("v_acc")[1] == 3.0
    assert variables.get("v_acc")[2] == 3.0
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_loop_nested_if_mplot_intensity():
    """Trail-style mplot with computed intensity inside nested loops."""
    flags.ENABLE_COMPILED_LOOPS = True
    block = [
        "for v_i in (1, 2, 1)",
        "for v_j in (1, 2, 1)",
        "v_intensity = 100 - (v_j * 20)",
        "mplot(v_i, v_j, 5, v_intensity)",
        "endfor v_j",
        "endfor v_i",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    plots = []

    def capture_mplot(x, y, color, intensity):
        plots.append((x, y, color, intensity))

    variables = VariableRegistry()
    variables.scan_and_register(["v_i", "v_j", "v_intensity"])
    ctx = make_loop_context(variables, capture_mplot, lambda: False)
    run_compiled_block(compiled, ctx)
    assert len(plots) == 4
    assert sorted(p[3] for p in plots) == [60, 60, 80, 80]
    flags.ENABLE_COMPILED_LOOPS = False
