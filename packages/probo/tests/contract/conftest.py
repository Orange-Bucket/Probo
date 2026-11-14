# SPDX-License-Identifier: Apache-2.0
"""Skip `docker`-marked contract tests when Docker or the pinned image is unusable."""

import shutil
import subprocess
from functools import cache

import pytest

from .fixtures.support import IMAGE

QUERY_TIMEOUT = 10
PULL_TIMEOUT = 180


def _succeeds(cmd: list[str], timeout: int) -> bool:
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


@cache
def docker_unavailable_reason() -> str | None:
    """Why Docker tests cannot run here, or None when they can. Computed once per session."""
    if shutil.which("docker") is None:
        return "docker CLI not found"
    if not _succeeds(["docker", "info"], QUERY_TIMEOUT):
        return "Docker daemon not available"
    if not _succeeds(["docker", "compose", "version"], QUERY_TIMEOUT):
        return "Docker Compose plugin not available"
    if _succeeds(["docker", "image", "inspect", IMAGE], QUERY_TIMEOUT):
        return None
    if _succeeds(["docker", "pull", "--quiet", IMAGE], PULL_TIMEOUT):
        return None
    return f"{IMAGE} is not present locally and could not be pulled"


def pytest_runtest_setup(item: pytest.Item) -> None:
    if item.get_closest_marker("docker") is None:
        return
    reason = docker_unavailable_reason()
    if reason is not None:
        pytest.skip(reason)
