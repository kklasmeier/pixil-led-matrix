"""sprite_batch protocol pack/unpack."""

from shared.sprite_batch_protocol import (
    pack_hide_record,
    pack_move_record,
    pack_show_record,
    pack_sprite_op,
    unpack_sprite_batch,
)


def test_move_roundtrip():
    rec = pack_move_record("ball_sprite", 10, 20, 3)
    cmds = list(unpack_sprite_batch(rec))
    assert cmds[0] == ("move_sprite", ("ball_sprite", 10, 20, 3))


def test_show_with_cel_roundtrip():
    rec = pack_show_record("ball_sprite", 5, 6, 1, 0)
    cmds = list(unpack_sprite_batch(rec))
    assert cmds[0][0] == "show_sprite"
    assert cmds[0][1][0] == "ball_sprite"
    assert cmds[0][1][1:4] == (5, 6, 1)


def test_hide_roundtrip():
    rec = pack_hide_record("ball_sprite", 7)
    cmds = list(unpack_sprite_batch(rec))
    assert cmds[0] == ("hide_sprite", ("ball_sprite", 7))


def test_pack_sprite_op_from_parsed_args():
    rec = pack_sprite_op("move_sprite", ["ball_sprite", "12", "34", "2"])
    cmds = list(unpack_sprite_batch(rec))
    assert cmds[0][1][:4] == ("ball_sprite", 12, 34, 2)
