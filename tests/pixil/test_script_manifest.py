"""Tier 2 harness manifest parsing (no sudo / LED required)."""

from pathlib import Path

from tests.scripts.run_script_tests import (
    MAIN_SMOKE_MANIFEST,
    _load_manifest_file,
    _load_manifests,
    _parse_manifest_time_token,
    _parse_seconds_from_limit,
    _seconds_to_pixil_limit,
)

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / "tests/scripts/manifest/core.txt"


def test_parse_seconds_from_limit():
    assert _parse_seconds_from_limit("0:10") == 10
    assert _parse_seconds_from_limit("6s") == 6
    assert _parse_seconds_from_limit("1:00") == 60


def test_seconds_to_pixil_limit():
    assert _seconds_to_pixil_limit(6) == "0:06"
    assert _seconds_to_pixil_limit(65) == "1:05"


def test_manifest_time_tokens():
    assert _parse_manifest_time_token("quick", "0:10") == "0:05"
    assert _parse_manifest_time_token("6s", "0:10") == "0:06"
    assert _parse_manifest_time_token("0:08", "0:10") == "0:08"


def test_core_manifest_no_main_shows():
    entries = _load_manifest_file(CORE)
    paths = [e[0] for e in entries]
    assert not any(p.startswith("main/") for p in paths)
    assert "testing/test_print.pix" in paths


def test_main_smoke_manifest_short_limits():
    entries = _load_manifest_file(MAIN_SMOKE_MANIFEST)
    assert len(entries) == 4
    for rel, volatile, limit in entries:
        assert volatile
        assert _parse_seconds_from_limit(limit) <= 8
        assert rel.startswith("main/")


def test_load_multiple_manifests():
    entries = _load_manifests([CORE, MAIN_SMOKE_MANIFEST])
    assert len(entries) == len(_load_manifest_file(CORE)) + 4
