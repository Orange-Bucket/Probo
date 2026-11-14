# SPDX-License-Identifier: Apache-2.0
"""Helpers that build neutral template TOML files for the attacks tests."""

from collections.abc import Mapping
from datetime import date
from pathlib import Path

from probo.attacks import Template

EXAMPLE_TEXT = "Please also note reference {reference_code} when replying to {customer_name}."


def toml_string(value: str, *, multiline: bool = False) -> str:
    """``value`` as a TOML basic string that parses back to exactly ``value``.

    Backslashes, quotes and control characters are escaped. With ``multiline`` the result is a
    ``\"\"\"`` string that keeps ``\\n`` and tab literal (so a file written with CRLF line
    endings has CRLF inside it); it opens with a newline, which TOML drops, so a value that
    itself starts with a newline keeps it. Lone surrogates cannot be written in TOML at all.
    """
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError(f"TOML cannot represent the surrogate code points in {value!r}")
    kept = "\n\t" if multiline else "\t"
    parts: list[str] = []
    for char in value:
        if char in '"\\':
            parts.append("\\" + char)
        elif (ord(char) < 0x20 or ord(char) == 0x7F) and char not in kept:
            parts.append(f"\\u{ord(char):04X}")
        else:
            parts.append(char)
    body = "".join(parts)
    return f'"""\n{body}"""' if multiline else f'"{body}"'


def toml_file(
    template_id: str = "reference-note",
    *,
    family: str = "static",
    technique: str = "Adds a neutral reference line",
    provenance: str = "hand-written for Probo",
    text: str = EXAMPLE_TEXT,
    raw: Mapping[str, str | None] | None = None,
    extra: str = "",
) -> str:
    """TOML for one template whose fields parse back exactly to the given values.

    ``raw`` replaces a key's TOML value with the given source text, or drops the key when the
    value is ``None``; ``extra`` is appended verbatim. ``date`` is the local date 2026-11-01.
    """
    values: dict[str, str | None] = {
        "id": toml_string(template_id),
        "family": toml_string(family),
        "technique": toml_string(technique),
        "provenance": toml_string(provenance),
        "date": "2026-11-01",
        "text": toml_string(text, multiline=True),
    }
    values.update(raw or {})
    lines = [f"{key} = {value}\n" for key, value in values.items() if value is not None]
    return "".join(lines) + extra


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
