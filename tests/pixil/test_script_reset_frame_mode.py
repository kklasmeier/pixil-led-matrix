"""Tests for script reset clearing stuck frame mode (no LED hardware)."""


def test_apply_script_reset_closes_open_frame():
    from shared.command_queue import MatrixCommandQueue

    q = MatrixCommandQueue(queue_size=4)
    calls = []

    class FakeApi:
        frame_mode = True
        preserve_frame_changes = True

        def reset_fps(self):
            calls.append("reset_fps")

        def end_frame(self):
            calls.append("end_frame")
            self.frame_mode = False

        def clear(self):
            calls.append("clear")
            self.frame_mode = False

        def dispose_all_sprites(self):
            calls.append("dispose")

    api = FakeApi()
    q._apply_script_reset(api)

    assert calls == ["reset_fps", "end_frame", "clear", "dispose"]
    assert api.frame_mode is False


def test_apply_script_reset_without_open_frame():
    from shared.command_queue import MatrixCommandQueue

    q = MatrixCommandQueue(queue_size=4)
    calls = []

    class FakeApi:
        frame_mode = False

        def reset_fps(self):
            calls.append("reset_fps")

        def end_frame(self):
            calls.append("end_frame")

        def clear(self):
            calls.append("clear")

        def dispose_all_sprites(self):
            calls.append("dispose")

    api = FakeApi()
    q._apply_script_reset(api)

    assert calls == ["reset_fps", "clear", "dispose"]
