# SPDX-License-Identifier: Apache-2.0
"""Paths of the package and repository, for tests that check files outside the source tree."""

import tomllib
from pathlib import Path

import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[2]
"""`packages/probo/` in a checkout, or the root of an unpacked sdist."""
REPOSITORY_ROOT = PACKAGE_DIR.parents[1]
"""The repository root, when the tests run from a checkout."""


def in_repository() -> bool:
    """True in a checkout of the repository, False when run from an unpacked sdist."""
    root_pyproject = REPOSITORY_ROOT / "pyproject.toml"
    if PACKAGE_DIR.parent.name != "packages" or not root_pyproject.is_file():
        return False
    config = tomllib.loads(root_pyproject.read_text(encoding="utf-8"))
    return "workspace" in config.get("tool", {}).get("uv", {})


needs_repository = pytest.mark.skipif(not in_repository(), reason="not in a repository checkout")
"""Skips a test that reads files only a repository checkout has."""
