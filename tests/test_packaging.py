"""Guards on the packaging contract itself.

There is no product code yet, so these tests exist to prove the toolchain is
wired correctly end to end: the package imports from a src layout, it advertises
inline types, and the Python floor/ceiling recorded in ADR-0001 is enforced.
"""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

import mepdiff


def test_package_imports_and_exposes_a_version() -> None:
    assert isinstance(mepdiff.__version__, str)
    assert mepdiff.__version__


def test_installed_metadata_matches_module_version() -> None:
    """Catches a stale editable install, which otherwise fails confusingly later."""
    assert importlib.metadata.version("mepdiff") == mepdiff.__version__


def test_package_ships_a_py_typed_marker() -> None:
    """Without this, downstream mypy users silently get ``Any`` for everything."""
    marker = Path(mepdiff.__file__).parent / "py.typed"
    assert marker.is_file()


def test_running_on_a_supported_interpreter() -> None:
    """IfcOpenShell 0.8.x declares ``>=3.9,<3.13``; the IFC adapter lands in M2."""
    assert (3, 11) <= sys.version_info[:2] < (3, 13)
