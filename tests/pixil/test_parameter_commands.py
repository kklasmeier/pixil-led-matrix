"""Minimal valid parameter strings for every defined command."""

import pytest

from pixil_utils.parameter_types import PARAMETER_TYPES, validate_command_params


def _literal_for_type(param_type: str) -> str:
    if param_type == "int":
        return "10"
    if param_type == "float":
        return "1.0"
    if param_type == "bool":
        return "true"
    if param_type == "color":
        return "red"
    if param_type == "str":
        return '"name"'
    raise ValueError(param_type)


def _minimal_param_string(command: str) -> str:
    """Build comma-separated params for all required fields only."""
    parts = []
    for spec in PARAMETER_TYPES[command]:
        if spec.get("optional"):
            continue
        parts.append(_literal_for_type(spec["type"]))
    return ", ".join(parts)


@pytest.mark.parametrize("command", sorted(PARAMETER_TYPES.keys()))
def test_validate_minimal_required_params(command):
    param_string = _minimal_param_string(command)
    if not param_string and command in ("clear", "sync_queue", "mflush", "dispose_all_sprites"):
        params = validate_command_params(command, "")
        assert params == []
        return
    params = validate_command_params(command, param_string)
    required = sum(1 for p in PARAMETER_TYPES[command] if not p.get("optional"))
    assert len(params) >= required


def test_draw_text_requires_six_params():
    raw = '10, 20, "Hi", tiny64_font, 8, white'
    params = validate_command_params("draw_text", raw)
    assert len(params) == 6


def test_begin_frame_false_and_true_params():
    """Regression: begin_frame must be in PARAMETER_TYPES (Chladni compiled loops)."""
    assert validate_command_params("begin_frame", "false") == ["false"]
    assert validate_command_params("begin_frame", "true") == ["true"]


def test_begin_frame_no_params():
    assert validate_command_params("begin_frame", "") == []
