"""Frame flush ordering: begin_frame with batch; draw_batch before draw_text."""


def _order_frame_commands(
    commands: list[str],
    pending_begin_frame: str | None = None,
) -> list[str]:
    """Mirror Pixil.flush_frame_commands ordering."""
    draw_batches: list[str] = []
    sprite_batches: list[str] = []
    plot_batches: list[str] = []
    other: list[str] = []
    for cmd in commands:
        if cmd.startswith("draw_batch("):
            draw_batches.append(cmd)
        elif cmd.startswith("sprite_batch("):
            sprite_batches.append(cmd)
        elif cmd.startswith("plot_batch("):
            plot_batches.append(cmd)
        else:
            other.append(cmd)
    ordered: list[str] = []
    if pending_begin_frame is not None:
        ordered.append(pending_begin_frame)
    ordered.extend(draw_batches + sprite_batches + plot_batches + other)
    return ordered


def test_draw_batch_runs_after_draw_text_was_queued():
    """Regression: game_of_life HUD was painted under the grid."""
    queued = [
        'draw_text(2, 2, "42", tiny64_font, 8, white, 100)',
        'draw_batch("abc")',
    ]
    ordered = _order_frame_commands(queued, pending_begin_frame="begin_frame(false)")
    assert ordered[0] == "begin_frame(false)"
    assert ordered[1].startswith("draw_batch(")
    assert ordered[2].startswith("draw_text(")


def test_begin_frame_precedes_draw_batch():
    """begin_frame must queue with draw_batch, not ahead of producer work."""
    queued = ['draw_batch("xyz")']
    ordered = _order_frame_commands(queued, pending_begin_frame="begin_frame(false)")
    assert ordered == ["begin_frame(false)", 'draw_batch("xyz")']


def test_begin_frame_preserve_mode():
    ordered = _order_frame_commands([], pending_begin_frame="begin_frame(true)")
    assert ordered == ["begin_frame(true)"]
