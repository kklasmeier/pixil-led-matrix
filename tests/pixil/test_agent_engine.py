"""Unit tests for agent_chemotaxis (no matrix / Pixil script harness)."""

import pytest

from pixil_utils.agent_engine import agent_chemotaxis
from pixil_utils.agent_commands import run_agent_line
from pixil_utils.array_manager import PixilArray


def _arr(values):
    a = PixilArray(len(values))
    for i, val in enumerate(values):
        a[i] = val
    return a


def _empty_field(size):
    return _arr([0.0] * (size * size))


def test_chemotaxis_moves_toward_scent_and_deposits():
    size = 8
    field = _empty_field(size)
    # Scent to the east of the agent
    field[4 * size + 6] = 1.0

    x = _arr([4.0])
    y = _arr([4.0])
    heading = _arr([0.0])  # facing east

    agent_chemotaxis(
        x, y, heading, field, size,
        sensor_dist=2, step=1, deposit=0.5, count=1, wrap=1,
    )

    assert x[0] == pytest.approx(5.0)
    assert y[0] == pytest.approx(4.0)
    # Deposit at landing cell
    assert field[4 * size + 5] >= 0.5


def test_chemotaxis_turns_toward_stronger_side_sensor():
    size = 8
    field = _empty_field(size)
    x = _arr([4.0])
    y = _arr([4.0])
    heading = _arr([0.0])  # east
    # Strong scent on the south-east sensor ray
    field[6 * size + 6] = 1.2

    agent_chemotaxis(
        x, y, heading, field, size,
        sensor_dist=2, step=1, deposit=0, count=1, wrap=1,
    )

    # Should turn toward SE (heading 1) and step that way
    assert int(heading[0]) % 8 == 1
    assert x[0] == pytest.approx(5.0)
    assert y[0] == pytest.approx(5.0)


def test_chemotaxis_deposit_zero_does_not_write_field():
    size = 4
    field = _empty_field(size)
    before = list(field.data)
    x = _arr([1.0])
    y = _arr([1.0])
    heading = _arr([2.0])

    agent_chemotaxis(
        x, y, heading, field, size,
        sensor_dist=1, step=1, deposit=0, count=1, wrap=1,
    )

    assert list(field.data) == before


def test_chemotaxis_rejects_bad_field_size():
    field = _arr([0.0] * 10)
    with pytest.raises(ValueError, match="field length"):
        agent_chemotaxis(
            _arr([0.0]), _arr([0.0]), _arr([0.0]), field, 4,
        )


def test_agent_line_dispatch():
    from pixil_utils.variable_registry import VariableRegistry

    size = 4
    variables = VariableRegistry()
    variables.set("v_x", _arr([1.0, 2.0]))
    variables.set("v_y", _arr([1.0, 2.0]))
    variables.set("v_dir", _arr([0.0, 4.0]))
    variables.set("v_field", _empty_field(size))
    variables.set("v_size", size)
    variables.set("v_n", 2)

    run_agent_line(
        "agent_chemotaxis(v_x, v_y, v_dir, v_field, v_size, 2, 1, 0.4, v_n, 1)",
        variables,
    )
    assert variables.get("v_x")[0] != 1.0 or variables.get("v_y")[0] != 1.0
