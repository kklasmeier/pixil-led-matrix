"""
Regression: procedural painting inside define_sprite must reach plot/sprite_draw.

Amiga_Boing_Ball.pix paints cels via:
  sprite_cel(N)
      v_spin = ...
      call draw_ball

Previously every line inside define_sprite was forced through process_sprite_command,
which only accepts drawing commands — so assignments and call were silently ignored
and the ball sprite stayed empty (only the navy shadow circle remained visible).

Hardening: clear/mplot are sprite-legal (mplot→plot); draw_text and other non-draw
commands must not be silently ignored.
"""

import pytest

from pixil_utils.regex_patterns import (
    SPRITE_DEFINITION_DRAW_COMMANDS,
    sprite_definition_allows_fallthrough,
    sprite_definition_emit_command,
)


@pytest.mark.parametrize(
    "line",
    [
        "v_spin = 0",
        "v_spin = 0.19635 * v_spin_sign",
        "call draw_ball",
        "for v_py in (0, 23, 1)",
        "while v_i < 10 then",
        "if v_d2 <= 1 then",
        "print(\"Rendering ball cels...\")",
        "break",
    ],
)
def test_control_flow_falls_through_during_sprite_definition(line):
    assert sprite_definition_allows_fallthrough(line) is True


@pytest.mark.parametrize(
    "line",
    [
        "sprite_cel(0)",
        "sprite_cel()",
        "plot(v_px, v_py, red, v_inten)",
        "mplot(v_px, v_py, red, v_inten)",
        "draw_circle(12, 12, 11, navy, 45, true)",
        "draw_rectangle(0, 0, 10, 10, blue, 100, true)",
        "draw_line(0, 0, 8, 8, white, 100)",
        "draw_ellipse(12, 12, 10, 8, white, 100, true)",
        "clear()",
        "draw_text(0, 0, \"hi\", tiny64_font, 5, white, 100)",
        "rest(1)",
        "fps(30)",
        "sync_queue",
        "begin_frame()",
    ],
)
def test_drawing_and_non_control_lines_do_not_fall_through(line):
    """Non-control lines stay on the sprite-command path (draw or hard-error)."""
    assert sprite_definition_allows_fallthrough(line) is False


@pytest.mark.parametrize(
    "cmd",
    [
        "plot",
        "mplot",
        "draw_line",
        "draw_rectangle",
        "draw_circle",
        "draw_polygon",
        "draw_ellipse",
        "draw_arc",
        "clear",
    ],
)
def test_sprite_definition_allow_list_includes_clear_and_mplot(cmd):
    assert cmd in SPRITE_DEFINITION_DRAW_COMMANDS


@pytest.mark.parametrize(
    "cmd",
    [
        "draw_text",
        "rest",
        "fps",
        "sync_queue",
        "begin_frame",
        "end_frame",
        "mflush",
    ],
)
def test_sprite_definition_allow_list_excludes_unsupported(cmd):
    assert cmd not in SPRITE_DEFINITION_DRAW_COMMANDS


def test_mplot_emits_as_plot():
    assert sprite_definition_emit_command("mplot") == "plot"
    assert sprite_definition_emit_command("plot") == "plot"
    assert sprite_definition_emit_command("clear") == "clear"
    assert sprite_definition_emit_command("draw_ellipse") == "draw_ellipse"


@pytest.mark.parametrize(
    "line",
    [
        "show_sprite(ball, 10, 10)",
        "hide_sprite(ball)",
        "move_sprite(ball, 12, 12)",
        "dispose_sprite(ball)",
    ],
)
def test_sprite_ops_do_not_fall_through_during_definition(line):
    """Sprite ops are blocked mid-definition (hard error in Pixil), not fallthrough."""
    assert sprite_definition_allows_fallthrough(line) is False
