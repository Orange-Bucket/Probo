# SPDX-License-Identifier: Apache-2.0
"""The committed JSON Schemas are what `probo schema` prints now, and every published finding's
JSON loads as its model and validates against its committed schema."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, validate

from probo.cli import SCHEMAS, json_schema

from .repository_support import PACKAGE_DIR, REPOSITORY_ROOT, needs_repository

SCHEMA_DIR = PACKAGE_DIR / "schemas"
REGENERATE = "pnpm nx run probo:export-schema"
"""The command that rewrites the committed schemas, run from the repository root."""
PUBLISHED = {"report": "report.json", "calibration": "judge-calibration.json"}
"""File name of each JSON output in a published finding's directory."""


def schema_path(name: str) -> Path:
    return SCHEMA_DIR / f"{name}.schema.json"


def published(name: str) -> list[Path]:
    return sorted((REPOSITORY_ROOT / "findings").glob(f"*/{PUBLISHED[name]}"))


def test_every_schema_has_a_published_file_name() -> None:
    assert set(PUBLISHED) == set(SCHEMAS)


@needs_repository
@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_committed_schema_is_current(name: str) -> None:
    """Fails when a model changed without its committed schema being regenerated."""
    path = schema_path(name)
    hint = f"run `{REGENERATE}` from the repository root and commit the result"
    assert path.is_file(), f"{path.relative_to(REPOSITORY_ROOT)} is missing; {hint}"
    committed = path.read_bytes().decode("utf-8")
    assert committed == json_schema(name), (
        f"{path.relative_to(REPOSITORY_ROOT)} differs from `probo schema {name}`; {hint}"
    )


@needs_repository
@pytest.mark.parametrize("name", sorted(PUBLISHED))
def test_findings_publish_each_output(name: str) -> None:
    """At least one finding holds each output, so the validation below is not vacuous."""
    assert published(name)


@needs_repository
@pytest.mark.parametrize(
    ("name", "path"),
    [(name, path) for name in sorted(PUBLISHED) for path in published(name)],
    ids=lambda value: value.parent.name if isinstance(value, Path) else str(value),
)
def test_published_output_validates(name: str, path: Path) -> None:
    """The file loads as its model and validates against its committed JSON Schema (which
    `validate` checks against the 2020-12 metaschema first)."""
    text = path.read_text(encoding="utf-8")
    SCHEMAS[name].model_validate_json(text)
    schema = json.loads(schema_path(name).read_text(encoding="utf-8"))
    validate(json.loads(text), schema, cls=Draft202012Validator)
