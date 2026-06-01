"""
Regression: sprite names containing 'v_' must not be parsed as Pixil variables.

Space Invaders (and similar scripts) use names like inv_bullet, invader1.
A broken has_math_expression() used `'v_' in value`, so inv_bullet was eval'd and
raised: invalid syntax (<string>, line 1).

See: scripts/main/Space_Invaders.pix — show_sprite(inv_bullet, ...)
"""

import pytest

from pixil_utils.expression_parser import format_parameter
from pixil_utils.loop_compiler import (
    make_loop_context,
    run_compiled_block,
    try_compile_loop_block,
)
from pixil_utils.math_functions import evaluate_math_expression, has_math_expression
from pixil_utils.optimization_flags import ENABLE_COMPILED_LOOPS
from pixil_utils.parameter_types import validate_command_params
from pixil_utils.variable_registry import VariableRegistry
from pixil_utils.array_manager import PixilArray
import pixil_utils.optimization_flags as flags

# Names from Space_Invaders.pix and similar games
SPRITE_NAMES_WITH_V_SUBSTRING = [
    "inv_bullet",
    "invader1",
    "invader2",
    "invader3",
    "player",
    "bullet",
    "paddle_sprite",
    "ball_sprite",
]


@pytest.mark.parametrize("name", SPRITE_NAMES_WITH_V_SUBSTRING)
def test_has_math_expression_false_for_sprite_names(name):
  """Sprite template names are literals, not v_ expressions."""
  assert has_math_expression(name) is False


@pytest.mark.parametrize("name", ["v_x", "v_ib_x", "v_slot"])
def test_has_math_expression_true_for_real_variables(name):
    assert has_math_expression(name) is True


@pytest.mark.parametrize("name", SPRITE_NAMES_WITH_V_SUBSTRING)
def test_format_parameter_show_sprite_name_passthrough(name):
    reg = VariableRegistry()
    assert format_parameter(name, "show_sprite", 0, reg) == name


def test_format_parameter_show_sprite_inv_bullet_with_expressions():
    """Space Invaders: show_sprite(inv_bullet, v_ib_x[v_slot], v_ib_y[v_slot], 200 + v_slot)"""
    reg = VariableRegistry()
    reg.scan_and_register(["v_slot", "v_ib_x", "v_ib_y"])
    reg.set("v_slot", 1)
    reg.set("v_ib_x", PixilArray(3))
    reg.set("v_ib_y", PixilArray(3))
    reg.get("v_ib_x")[1] = 12
    reg.get("v_ib_y")[1] = 20

    assert format_parameter("inv_bullet", "show_sprite", 0, reg) == "inv_bullet"
    assert format_parameter("v_ib_x[v_slot]", "show_sprite", 1, reg) == "12"
    assert format_parameter("v_ib_y[v_slot]", "show_sprite", 2, reg) == "20"
    assert format_parameter("200 + v_slot", "show_sprite", 3, reg) == "201"


def test_format_parameter_move_and_hide_sprite_inv_bullet():
    reg = VariableRegistry()
    reg.scan_and_register(["v_i", "v_ib_x", "v_ib_y"])
    reg.set("v_i", 0)
    reg.set("v_ib_x", PixilArray(3))
    reg.set("v_ib_y", PixilArray(3))
    reg.get("v_ib_x")[0] = 5
    reg.get("v_ib_y")[0] = 30

    assert format_parameter("inv_bullet", "move_sprite", 0, reg) == "inv_bullet"
    assert format_parameter("v_ib_x[v_i]", "move_sprite", 1, reg) == "5"
    assert format_parameter("200 + v_i", "move_sprite", 3, reg) == "200"
    assert format_parameter("inv_bullet", "hide_sprite", 0, reg) == "inv_bullet"
    assert format_parameter("200 + v_i", "hide_sprite", 1, reg) == "200"


def test_evaluate_math_expression_rejects_inv_bullet():
    reg = VariableRegistry()
    with pytest.raises(Exception):
        evaluate_math_expression("inv_bullet", reg)


def test_compiled_loop_show_sprite_inv_bullet_formats_name():
    """Compiled CommandStmt path must format inv_bullet without eval error."""
    flags.ENABLE_COMPILED_LOOPS = True
    flags.ENABLE_COMPILED_PROCEDURES = True
    block = [
        "show_sprite(inv_bullet, v_ib_x[v_slot], v_ib_y[v_slot], 200 + v_slot)",
    ]
    compiled = try_compile_loop_block(block)
    assert compiled is not None

    reg = VariableRegistry()
    reg.scan_and_register(["v_slot", "v_ib_x", "v_ib_y"])
    reg.set("v_slot", 0)
    reg.set("v_ib_x", PixilArray(3))
    reg.set("v_ib_y", PixilArray(3))
    reg.get("v_ib_x")[0] = 8
    reg.get("v_ib_y")[0] = 16

    commands = []

    def capture(cmd_name, arg_exprs):
        from pixil_utils.parameter_types import expand_legacy_shape_params

        arg_str = ",".join(arg_exprs)
        args = validate_command_params(cmd_name, arg_str)
        args = expand_legacy_shape_params(cmd_name, args)
        formatted = [
            format_parameter(arg, cmd_name, position, reg)
            for position, arg in enumerate(args)
        ]
        commands.append((cmd_name, formatted))

    ctx = make_loop_context(
        reg, lambda *a: None, lambda: False, run_command=capture,
    )
    run_compiled_block(compiled, ctx)
    assert commands == [
        ("show_sprite", ["inv_bullet", "8", "16", "200"]),
    ]
    flags.ENABLE_COMPILED_LOOPS = False
    flags.ENABLE_COMPILED_PROCEDURES = False


def test_compiled_procedure_body_show_sprite_inv_bullet():
    """Procedure bodies use the same CommandStmt + format_parameter path."""
    flags.ENABLE_COMPILED_LOOPS = True
    flags.ENABLE_COMPILED_PROCEDURES = True
    from pixil_utils.loop_compiler import try_compile_procedure_block, run_compiled_block

    body = [
        "show_sprite(inv_bullet, 10, 20, 201)",
    ]
    compiled = try_compile_procedure_block(body)
    assert compiled is not None

    commands = []

    def capture(cmd_name, arg_exprs):
        reg = VariableRegistry()
        formatted = [
            format_parameter(arg, cmd_name, position, reg)
            for position, arg in enumerate(
                validate_command_params(cmd_name, ",".join(arg_exprs))
            )
        ]
        commands.append((cmd_name, formatted))

    ctx = make_loop_context(
        VariableRegistry(), lambda *a: None, lambda: False, run_command=capture,
    )
    run_compiled_block(compiled, ctx)
    assert commands[0][0] == "show_sprite"
    assert commands[0][1][0] == "inv_bullet"
    flags.ENABLE_COMPILED_LOOPS = False
    flags.ENABLE_COMPILED_PROCEDURES = False
