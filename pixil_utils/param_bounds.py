"""
Bounded parameter clamping for the Pixil script interpreter.

Out-of-range values are clamped (never dropped) and reported with WARN prints
so script authors see every occurrence.
"""
from typing import Any, Union

INTENSITY_MIN = 0
INTENSITY_MAX = 100
SPECTRAL_MIN = 0
SPECTRAL_MAX = 99
THROTTLE_MIN = 0.01
BURNOUT_PERMANENT = -1


def warn_param_clamp(
    command: str,
    param_name: str,
    original: Union[int, float, str],
    clamped: Union[int, float],
    detail: str = "",
) -> None:
    """Always print a clamp warning (visible regardless of debug level)."""
    ctx = f"{command} {param_name}" if command else param_name
    extra = f" ({detail})" if detail else ""
    print(
        f"WARN {ctx}: {original} out of range{extra}, using {clamped}",
        flush=True,
    )


def _to_number(value: Union[str, int, float]) -> Union[int, float]:
    if isinstance(value, str):
        value = value.strip()
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)
    return value


def is_numeric_literal(value: Any) -> bool:
    if isinstance(value, (int, float)):
        return True
    if not isinstance(value, str):
        return False
    s = value.strip()
    if not s:
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


def clamp_intensity(
    value: Union[str, int, float],
    *,
    command: str = "",
    param_name: str = "intensity",
    warn: bool = True,
) -> int:
    raw = _to_number(value)
    num = round(raw) if isinstance(raw, float) else int(raw)
    clamped = max(INTENSITY_MIN, min(INTENSITY_MAX, num))
    if warn and clamped != num:
        warn_param_clamp(
            command,
            param_name,
            num,
            clamped,
            f"range {INTENSITY_MIN}-{INTENSITY_MAX}",
        )
    return clamped


def clamp_spectral_color(
    value: Union[str, int, float],
    *,
    command: str = "",
    param_name: str = "color",
    warn: bool = True,
) -> int:
    raw = _to_number(value)
    num = round(raw) if isinstance(raw, float) else int(raw)
    clamped = max(SPECTRAL_MIN, min(SPECTRAL_MAX, num))
    if warn and clamped != num:
        warn_param_clamp(
            command,
            param_name,
            num,
            clamped,
            f"range {SPECTRAL_MIN}-{SPECTRAL_MAX}",
        )
    return clamped


def clamp_burnout_duration(
    value: Union[str, int, float],
    *,
    command: str = "",
    param_name: str = "duration",
    warn: bool = True,
) -> float:
    raw = _to_number(value)
    num = float(raw)
    if num == BURNOUT_PERMANENT:
        return BURNOUT_PERMANENT
    if num < 0:
        if warn:
            warn_param_clamp(
                command,
                param_name,
                num,
                0,
                "min 0 (or -1 permanent)",
            )
        return 0.0
    return num


def clamp_throttle(
    value: Union[str, int, float],
    *,
    warn: bool = True,
) -> float:
    raw = _to_number(value)
    num = float(raw)
    if num < THROTTLE_MIN:
        if warn:
            warn_param_clamp(
                "throttle",
                "factor",
                num,
                THROTTLE_MIN,
                f"min {THROTTLE_MIN}",
            )
        return THROTTLE_MIN
    return num


def format_burnout_for_command(value: float) -> str:
    if value == BURNOUT_PERMANENT:
        return "-1"
    if value == int(value):
        return str(int(value))
    return str(value)


def is_burnout_duration_param(command: str, param_name: str) -> bool:
    if param_name == "burnout":
        return True
    if param_name == "duration" and command != "rest":
        return True
    return False


__all__ = [
    "INTENSITY_MIN",
    "INTENSITY_MAX",
    "SPECTRAL_MIN",
    "SPECTRAL_MAX",
    "THROTTLE_MIN",
    "BURNOUT_PERMANENT",
    "warn_param_clamp",
    "clamp_intensity",
    "clamp_spectral_color",
    "clamp_burnout_duration",
    "clamp_throttle",
    "format_burnout_for_command",
    "is_burnout_duration_param",
    "is_numeric_literal",
]
