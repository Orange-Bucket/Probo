# SPDX-License-Identifier: Apache-2.0
"""Helpers that build neutral template TOML files for the attacks tests."""

from datetime import date
from pathlib import Path

from probo.attacks import Template

EXAMPLE_TEXT = "Please also note reference {reference_code} when replying to {customer_name}."


def toml_file(
    template_id: str = "reference-note",
    *,
    family: str = "static",
    technique: str = "Adds a neutral reference line",
    provenance: str = "hand-written for Probo",
    date_literal: str = "2026-11-01",
    text: str = EXAMPLE_TEXT,
    extra: str = "",
) -> str:
    """TOML for one template: ``date_literal`` goes in unquoted, ``text`` as a literal string."""
    assert "'''" not in text
    return (
        f'id = "{template_id}"\n'
        f'family = "{family}"\n'
        f'technique = "{technique}"\n'
        f'provenance = "{provenance}"\n'
        f"date = {date_literal}\n"
        f"text = '''{text}'''\n"
        f"{extra}"
    )


def write(directory: Path, name: str, content: str, *, newline: str = "\n") -> Path:
    """Write ``content`` to ``directory/name`` with the given line ending and return the path."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(content.replace("\n", newline).encode("utf-8"))
    return path


def template(text: str = EXAMPLE_TEXT, template_id: str = "reference-note") -> Template:
    """A valid template with the given text."""
    return Template(
        id=template_id,
        family="static",
        technique="Adds a neutral reference line",
        provenance="hand-written for Probo",
        date=date(2026, 11, 1),
        text=text,
    )
