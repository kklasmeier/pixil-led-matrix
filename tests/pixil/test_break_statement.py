"""break in compiled loops and interpreter fallback."""

import pixil_utils.optimization_flags as flags
from pixil_utils.loop_compiler import (
    BreakStmt,
    LoopBreak,
    try_compile_loop_block,
    try_compile_procedure_block,
    run_compiled_block,
    run_compiled_loop_body,
    make_loop_context,
    reset_loop_compiler_stats,
)
from pixil_utils.variable_registry import VariableRegistry
from pixil_utils.array_manager import PixilArray


def test_break_parses_in_loop_block():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    from pixil_utils.loop_compiler import ForStmt, IfStmt

    block = [
        "for v_i in (0, 10, 1)",
        "if v_i == 3 then",
        "break",
        "endif",
        "v_sum = v_sum + 1",
        "endfor v_i",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None
    for_stmt = compiled.statements[0]
    assert isinstance(for_stmt, ForStmt)
    if_stmt = for_stmt.body[0]
    assert isinstance(if_stmt, IfStmt)
    assert isinstance(if_stmt.branches[0][1][0], BreakStmt)
    flags.ENABLE_COMPILED_LOOPS = False


def test_compiled_for_break_exits_early():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    block = [
        "for v_i in (0, 10, 1)",
        "if v_i == 3 then",
        "break",
        "endif",
        "v_sum = v_sum + 1",
        "endfor v_i",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None

    variables = VariableRegistry()
    variables.scan_and_register(["v_i", "v_sum"])
    variables.set("v_sum", 0)
    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    run_compiled_block(compiled, ctx)
    assert variables.get("v_sum") == 3.0
    flags.ENABLE_COMPILED_LOOPS = False


def test_compiled_nested_break_only_inner():
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    block = [
        "for v_outer in (0, 2, 1)",
        "v_outer_sum = v_outer_sum + 1",
        "for v_inner in (0, 5, 1)",
        "if v_inner == 2 then",
        "break",
        "endif",
        "v_inner_sum = v_inner_sum + 1",
        "endfor v_inner",
        "endfor v_outer",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None

    variables = VariableRegistry()
    variables.scan_and_register(["v_outer", "v_inner", "v_outer_sum", "v_inner_sum"])
    variables.set("v_outer_sum", 0)
    variables.set("v_inner_sum", 0)
    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    run_compiled_block(compiled, ctx)
    assert variables.get("v_outer_sum") == 3.0
    assert variables.get("v_inner_sum") == 6.0
    flags.ENABLE_COMPILED_LOOPS = False


def test_compiled_find_first_slot_pattern():
    """Expanding_Circles-style: break when first inactive slot is found."""
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    block = [
        "v_new_index = -1",
        "for v_i in (0, 4, 1)",
        "if v_active[v_i] == 0 then",
        "v_new_index = v_i",
        "break",
        "endif",
        "endfor v_i",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None

    variables = VariableRegistry()
    variables.scan_and_register(["v_i", "v_new_index", "v_active"])
    variables.set("v_new_index", -1)
    variables.set("v_active", PixilArray(5))
    variables.get("v_active")[0] = 1
    variables.get("v_active")[1] = 1
    variables.get("v_active")[2] = 0
    variables.get("v_active")[3] = 0

    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    run_compiled_block(compiled, ctx)
    assert variables.get("v_new_index") == 2.0
    flags.ENABLE_COMPILED_LOOPS = False


def test_compiled_while_break():
    flags.ENABLE_COMPILED_LOOPS = True
    from pixil_utils.loop_compiler import run_compiled_while_body

    reset_loop_compiler_stats()
    inner = try_compile_loop_block([
        "v_n = v_n + 1",
        "if v_n >= 3 then",
        "break",
        "endif",
    ])
    assert inner is not None

    variables = VariableRegistry()
    variables.scan_and_register(["v_n"])
    variables.set("v_n", 0)
    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    run_compiled_while_body(inner, "v_n < 10", ctx)
    assert variables.get("v_n") == 3.0
    flags.ENABLE_COMPILED_LOOPS = False


def test_voronoi_edge_loop_with_break_compiles():
    """Original Voronoi inner pattern compiled once break is supported."""
    flags.ENABLE_COMPILED_LOOPS = True
    reset_loop_compiler_stats()
    block = [
        "for v_x in (0, 3, 1)",
        "v_closest = 0",
        "v_min_dist = 10000",
        "for v_i in (0, 4, 1)",
        "if v_i != v_closest then",
        "v_dx = v_x - v_px[v_i]",
        "v_dy = v_y - v_py[v_i]",
        "v_dist = v_dx * v_dx + v_dy * v_dy",
        "if v_dist < v_min_dist * 1.05 then",
        "v_edge = 1",
        "break",
        "endif",
        "endif",
        "endfor v_i",
        "endfor v_x",
    ]
    assert try_compile_loop_block(block) is not None
    flags.ENABLE_COMPILED_LOOPS = False


def test_break_in_procedure_compiles():
    flags.ENABLE_COMPILED_PROCEDURES = True
    body = [
        "for v_i in (0, 5, 1)",
        "if v_i == 2 then",
        "break",
        "endif",
        "v_acc = v_acc + 1",
        "endfor v_i",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None

    variables = VariableRegistry()
    variables.scan_and_register(["v_i", "v_acc"])
    variables.set("v_acc", 0)
    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    run_compiled_block(compiled, ctx)
    assert variables.get("v_acc") == 2.0
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_top_level_break_in_compiled_block_is_ignored():
    flags.ENABLE_COMPILED_LOOPS = True
    compiled = try_compile_loop_block(["break", "v_x = 5"])
    assert compiled is not None
    variables = VariableRegistry()
    variables.scan_and_register(["v_x"])
    variables.set("v_x", 0)
    ctx = make_loop_context(variables, lambda *a: None, lambda: False)
    run_compiled_block(compiled, ctx)
    assert variables.get("v_x") == 0
    flags.ENABLE_COMPILED_LOOPS = False


def test_interpreter_style_loop_break_semantics():
    """Mirror Pixil for-loop + process_lines: LoopBreak exits only the innermost loop."""
    from pixil_utils.math_functions import evaluate_math_expression, evaluate_condition

    variables = VariableRegistry()
    variables.scan_and_register(["v_i", "v_sum"])
    variables.set("v_sum", 0)

    loop_block = [
        "if v_i == 3 then",
        "break",
        "endif",
        "v_sum = v_sum + 1",
    ]

    def process_block(lines):
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.lower() == "break":
                raise LoopBreak()
            if line.startswith("if ") and line.endswith(" then"):
                cond = line[3:-5].strip()
                i += 1
                body = []
                while i < len(lines) and lines[i].strip() != "endif":
                    body.append(lines[i])
                    i += 1
                if evaluate_condition(cond, variables):
                    process_block(body)
                if i < len(lines) and lines[i].strip() == "endif":
                    i += 1
                continue
            if line.startswith("v_") and "=" in line:
                var, expr = line.split("=", 1)
                variables.set(var.strip(), evaluate_math_expression(expr.strip(), variables))
            i += 1

    current = 0.0
    while current <= 10.0 + 1e-10:
        variables.set("v_i", current)
        try:
            process_block(loop_block)
        except LoopBreak:
            break
        current += 1.0

    assert variables.get("v_sum") == 3.0
