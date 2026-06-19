"""Tests for Chladni native particle step."""

from pixil_utils.array_manager import PixilArray
from pixil_utils.chladni_engine import _chladni_value, run_chladni_step
from pixil_utils.variable_registry import VariableRegistry


def test_chladni_value_computes():
    scale = 0.09817477
    val = _chladni_value(32, 32, 1 * scale, 2 * scale)
    assert 0 <= val <= 2.0


def test_chladni_step_moves_particles_and_draws():
    reg = VariableRegistry()
    for name in ("v_px", "v_py", "v_n_scale", "v_m_scale"):
        reg.register(name)
    reg.set("v_px", PixilArray(3))
    reg.set("v_py", PixilArray(3))
    reg.get("v_px")[0] = 10
    reg.get("v_py")[0] = 10
    reg.get("v_px")[1] = 50
    reg.get("v_py")[1] = 50
    reg.get("v_px")[2] = 32
    reg.get("v_py")[2] = 32
    reg.set("v_n_scale", 1 * 0.09817477)
    reg.set("v_m_scale", 2 * 0.09817477)

    draws = []

    def capture(cmd, args):
        draws.append((cmd, args))

    run_chladni_step(reg, "v_px", "v_py", "v_n_scale", "v_m_scale", capture)
    assert len(draws) == 3
    assert draws[0][0] == "mplot"
