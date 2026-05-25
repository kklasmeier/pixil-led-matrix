"""Script path resolution (pixil_utils.script_manager / file_manager)."""

import os
from pathlib import Path

import pytest

from pixil_utils.file_manager import PixilFileManager
from pixil_utils.script_manager import ScriptManager

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def repo_cwd():
    """ScriptManager globs relative to cwd — use repo root like production."""
    prev = os.getcwd()
    os.chdir(REPO_ROOT)
    yield
    os.chdir(prev)


def test_file_manager_resolves_testing_print():
    fm = PixilFileManager()
    path = fm.get_script_path("testing/test_print")
    assert path.exists()
    assert path.suffix == ".pix"


def test_file_manager_resolves_without_pix_extension():
    fm = PixilFileManager()
    path = fm.get_script_path("testing/test_if_else.pix")
    assert path.name == "test_if_else.pix"


def test_script_manager_single_script():
    sm = ScriptManager("testing/test_procedure")
    assert sm.is_single_script()
    assert len(sm.scripts) == 1
    assert "test_procedure" in sm.scripts[0]


def test_script_manager_glob_finds_multiple():
    sm = ScriptManager("testing/test_math*.pix")
    assert not sm.is_single_script()
    assert sm.script_count >= 2


def test_script_manager_missing_script_raises():
    with pytest.raises(FileNotFoundError):
        ScriptManager("testing/no_such_script_xyz.pix")
