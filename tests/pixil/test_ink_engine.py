"""Tests for ink-in-water native particle step."""

from pixil_utils.array_manager import PixilArray
from pixil_utils.ink_engine import run_ink_step
from pixil_utils.variable_registry import VariableRegistry


def _make_ink_vars():
    reg = VariableRegistry()
    for name in (
        "v_px", "v_py", "v_vx", "v_vy", "v_intensity", "v_alive",
        "v_curve_x", "v_curve_y", "v_drop_x", "v_drop_y", "v_drift_x",
        "v_drift_y", "v_swirl_active", "v_swirl_strength", "v_swirl_dir",
        "v_fade_rate", "v_color_bright", "v_color_mid", "v_color_dark",
        "v_any_alive",
    ):
        reg.register(name)

    n = 3
    reg.set("v_px", PixilArray(n))
    reg.set("v_py", PixilArray(n))
    reg.set("v_vx", PixilArray(n))
    reg.set("v_vy", PixilArray(n))
    reg.set("v_intensity", PixilArray(n))
    reg.set("v_alive", PixilArray(n))
    reg.set("v_curve_x", PixilArray(n))
    reg.set("v_curve_y", PixilArray(n))

    px = reg.get("v_px")
    py = reg.get("v_py")
    vx = reg.get("v_vx")
    vy = reg.get("v_vy")
    intensity = reg.get("v_intensity")
    alive = reg.get("v_alive")

    px[0] = 32
    py[0] = 32
    vx[0] = 0.5
    vy[0] = 0.2
    intensity[0] = 90
    alive[0] = 1

    px[1] = 10
    py[1] = 10
    intensity[1] = 5
    alive[1] = 1

    alive[2] = 0

    reg.set("v_drop_x", 32)
    reg.set("v_drop_y", 32)
    reg.set("v_drift_x", 0)
    reg.set("v_drift_y", 0)
    reg.set("v_swirl_active", 0)
    reg.set("v_swirl_strength", 0)
    reg.set("v_swirl_dir", 1)
    reg.set("v_fade_rate", 2)
    reg.set("v_color_bright", "cyan")
    reg.set("v_color_mid", "blue")
    reg.set("v_color_dark", "navy")

    return reg


def test_ink_step_updates_and_draws_living_particles():
    reg = _make_ink_vars()
    draws = []

    def capture(cmd, args):
        draws.append((cmd, args))

    run_ink_step(reg, capture)

    assert reg.get("v_any_alive") == 1
    assert len(draws) == 2
    assert draws[0][0] == "mplot"
    assert draws[0][1][2] == "cyan"
    assert reg.get("v_px")[0] > 32


def test_ink_step_clears_dead_particles():
    reg = _make_ink_vars()
    intensity = reg.get("v_intensity")
    intensity[1] = 1

    run_ink_step(reg, lambda _c, _a: None)

    assert reg.get("v_alive")[1] == 0
    assert reg.get("v_any_alive") == 1
