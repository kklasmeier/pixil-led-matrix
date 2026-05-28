"""clear() inside compiled while bodies."""

from pixil_utils import optimization_flags as flags
from pixil_utils.loop_compiler import try_compile_loop_block, make_loop_context, run_compiled_block
from pixil_utils.variable_registry import VariableRegistry


def test_while_with_clear_compiles():
    flags.ENABLE_COMPILED_LOOPS = True
    block = [
        "begin_frame",
        "end_frame",
        "if v_frame >= 10 then",
        "clear()",
        "endif",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None

    cleared = []

    def run_command(cmd_name, arg_exprs):
        if cmd_name == "clear":
            cleared.append(True)

    variables = VariableRegistry()
    variables.set("v_frame", 10)
    ctx = make_loop_context(
        variables, lambda *a: None, lambda: False, run_command=run_command,
    )
    run_compiled_block(compiled, ctx)
    assert cleared == [True]
    flags.ENABLE_COMPILED_LOOPS = False
