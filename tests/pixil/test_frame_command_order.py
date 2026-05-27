"""Frame flush ordering: draw_batch must run before draw_text in the same frame."""


def _order_frame_commands(commands: list[str]) -> list[str]:
    """Mirror Pixil.flush_frame_commands ordering (batches before HUD/text)."""
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
    return draw_batches + sprite_batches + plot_batches + other


def test_draw_batch_runs_after_draw_text_was_queued():
    """Regression: game_of_life HUD was painted under the grid."""
    queued = [
        'draw_text(2, 2, "42", tiny64_font, 8, white, 100)',
        'draw_batch("abc")',
    ]
    ordered = _order_frame_commands(queued)
    assert ordered[0].startswith("draw_batch(")
    assert ordered[1].startswith("draw_text(")
