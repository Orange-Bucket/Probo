# SPDX-License-Identifier: Apache-2.0
"""The LICENSE and NOTICE copies in the package directory match the repository root files.

The build backend cannot include files from above the package directory, so the package keeps
its own copies for the wheel and sdist. These tests keep the copies from drifting.
"""

import tomllib

import pytest

from .repository_support import PACKAGE_DIR, REPOSITORY_ROOT, needs_repository


def test_package_dir_is_the_probo_project() -> None:
    """The paths above point at the probo project, wherever the tests run from."""
    config = tomllib.loads((PACKAGE_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["project"]["name"] == "probo"


@needs_repository
@pytest.mark.parametrize("name", ["LICENSE", "NOTICE"])
def test_copy_matches_repository_root(name: str) -> None:
    copy = (PACKAGE_DIR / name).read_bytes()
    original = (REPOSITORY_ROOT / name).read_bytes()
    assert copy == original, f"packages/probo/{name} differs from the repository root {name}"
