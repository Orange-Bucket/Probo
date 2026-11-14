# SPDX-License-Identifier: Apache-2.0
"""The LICENSE and NOTICE copies in the package directory match the repository root files.

The build backend cannot include files from above the package directory, so the package keeps
its own copies for the wheel and sdist. These tests keep the copies from drifting.
"""

import tomllib
from pathlib import Path

import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PACKAGE_DIR.parents[1]


def _in_repository() -> bool:
    """True in a checkout of the repository, False when run from an unpacked sdist."""
    root_pyproject = REPOSITORY_ROOT / "pyproject.toml"
    if PACKAGE_DIR.parent.name != "packages" or not root_pyproject.is_file():
        return False
    config = tomllib.loads(root_pyproject.read_text(encoding="utf-8"))
    return "workspace" in config.get("tool", {}).get("uv", {})


def test_package_dir_is_the_probo_project() -> None:
    """The paths above point at the probo project, wherever the tests run from."""
    config = tomllib.loads((PACKAGE_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["project"]["name"] == "probo"


@pytest.mark.skipif(not _in_repository(), reason="not in a repository checkout")
@pytest.mark.parametrize("name", ["LICENSE", "NOTICE"])
def test_copy_matches_repository_root(name: str) -> None:
    copy = (PACKAGE_DIR / name).read_bytes()
    original = (REPOSITORY_ROOT / name).read_bytes()
    assert copy == original, f"packages/probo/{name} differs from the repository root {name}"
