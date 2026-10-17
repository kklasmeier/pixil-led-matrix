"""Tests for agent_chemotaxis kernel."""

import pytest

from pixil_utils.agent_engine import agent_chemotaxis
from pixil_utils.array_manager import PixilArray


def _arr(values):
    a = PixilArray(len(values))
    for i, val in enumerate(values):
        a[i] = float(val)
    return a


def test_agent_steps_ahead_and_deposits():
    size = 16
    field = PixilArray(size * size)
    x = _arr([8.0])
    y = _arr([8.0])
    heading = _arr([0.0])  # east

    agent_chemotaxis(
        x, y, heading, field, size,
        sensor_dist=3,
        step=1,
        deposit=0.5,
        wrap=True,
    )

    assert x[0] == pytest.approx(9.0)
    assert y[0] == pytest.approx(8.0)
    assert heading[0] == pytest.approx(0.0)
    assert field[8 * size + 9] >= 0.5


def test_agent_turns_toward_stronger_side_scent():
    size = 16
    field = PixilArray(size * size)
    # Facing east; strong scent on the north (left) sensor cell
    # left of E is NE → sample at (8+3, 8-3) = (11, 5)
    field[5 * size + 11] = 1.2

    x = _arr([8.0])
    y = _arr([8.0])
    heading = _arr([0.0])

    agent_chemotaxis(
        x, y, heading, field, size,
        sensor_dist=3,
        step=1,
        deposit=0.0,
        wrap=True,
    )

    assert heading[0] == pytest.approx(7.0)  # turned left to NE
    assert x[0] == pytest.approx(9.0)
    assert y[0] == pytest.approx(7.0)


def test_agent_wraps_and_respects_count():
    size = 8
    field = PixilArray(size * size)
    x = _arr([7.0, 3.0])
    y = _arr([4.0, 3.0])
    heading = _arr([0.0, 0.0])  # east

    agent_chemotaxis(
        x, y, heading, field, size,
        sensor_dist=1,
        step=1,
        deposit=0.25,
        count=1,
        wrap=True,
    )

    assert x[0] == pytest.approx(0.0)  # wrapped
    assert x[1] == pytest.approx(3.0)  # untouched (count=1)
    assert field[int(y[0]) * size + int(x[0])] >= 0.25


def test_deposit_zero_does_not_write_field():
    size = 8
    field = PixilArray(size * size)
    x = _arr([2.0])
    y = _arr([2.0])
    heading = _arr([0.0])

    agent_chemotaxis(
        x, y, heading, field, size,
        deposit=0.0,
        wrap=False,
    )
    assert sum(field.data) == 0.0
