# SPDX-License-Identifier: Apache-2.0
"""Dated, versioned text templates: the schema, placeholder rendering and the corpus loader.

A corpus is a directory ``<family>/<version>/`` of TOML files, one template per file. The
packaged corpora live under ``probo/attacks/corpus/``; see the README in each version directory
for the file format.
"""

import hashlib
import json
import re
import tomllib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date as Date
from importlib.resources import files
from importlib.resources.abc import Traversable
from itertools import pairwise
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

NAME_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
"""Template ids and family names: lowercase letters and digits, joined by single hyphens."""

VERSION_PATTERN = r"^[0-9]{4}-(0[1-9]|1[0-2])$"
"""Corpus versions are dated directory names of the form ``YYYY-MM``."""

PLACEHOLDER_NAME = r"[a-z_][a-z0-9_]*"
"""The name inside a ``{name}`` placeholder."""

_TOKEN = re.compile(r"\{\{|\}\}|\{(" + PLACEHOLDER_NAME + r")\}|[{}]")
_FRAGMENT_LIMIT = 40
_HASH_FORMAT = "probo.attacks.corpus/1"
_BOM = b"\xef\xbb\xbf"

Name = Annotated[str, Field(pattern=NAME_PATTERN)]
NonEmpty = Annotated[str, Field(min_length=1)]


class CorpusError(ValueError):
    """A corpus, its directory or one of its template files is invalid.

    An error about a template file starts with that file's path; errors about a ``Corpus``
    being constructed name the offending template id, family or version instead.
    """


def _split(template_id: str, text: str) -> tuple[list[str], list[str]]:
    """Split ``text`` into literals and placeholder names, interleaved literal-name-literal.

    ``len(literals) == len(names) + 1``. ``{{`` and ``}}`` become single braces in the
    literals; any other brace raises ``ValueError`` naming ``template_id`` and the fragment.
    """
    literals: list[str] = []
    names: list[str] = []
    current: list[str] = []
    position = 0
    for match in _TOKEN.finditer(text):
        current.append(text[position : match.start()])
        position = match.end()
        token = match.group(0)
        if token in ("{{", "}}"):
            current.append(token[0])
        elif match.group(1) is not None:
            literals.append("".join(current))
            names.append(match.group(1))
            current = []
        else:
            start = match.start()
            close = text.find("}", start + 1) if token == "{" else start
            end = len(text) if close == -1 else close + 1
            fragment = text[start : min(end, start + _FRAGMENT_LIMIT)]
            raise ValueError(
                f"template {template_id!r}: invalid brace syntax {fragment!r} at offset {start}; "
                f"a placeholder is {{name}} with name matching {PLACEHOLDER_NAME}, "
                "and literal braces are written {{ and }}"
            )
    current.append(text[position:])
    literals.append("".join(current))
    return literals, names


class Template(BaseModel):
    """One hand-written text template with its provenance.

    ``text`` holds ``{name}`` placeholders (name matching ``[a-z_][a-z0-9_]*``) and ``{{`` /
    ``}}`` for literal braces. Every other use of a brace is rejected on validation, so a
    template that loads can always be rendered by ``render``. ``model_copy`` re-validates.
    ``render`` parses ``text`` again itself, so even an instance that skipped validation
    (``model_construct``) never substitutes anything but ``{name}``.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: Name
    """Unique id within its corpus; also the TOML file's stem."""
    family: Name
    """The corpus family the template belongs to, for example ``static``."""
    technique: NonEmpty
    """One-line description of what the text does (no line boundary of ``str.splitlines``)."""
    provenance: NonEmpty
    """Where the text came from, for example ``hand-written for Probo``."""
    date: Date
    """When the text was written or last changed (a TOML local date, never a string)."""
    text: NonEmpty
    """The template text; ``\\n`` line endings only."""

    @model_validator(mode="after")
    def _fields_are_well_formed(self) -> Self:
        for name in ("technique", "provenance", "text"):
            if not getattr(self, name).strip():
                raise ValueError(f"template {self.id!r}: {name} must not be blank")
        if self.technique.splitlines() != [self.technique]:
            raise ValueError(f"template {self.id!r}: technique must be a single line")
        if "\r" in self.text:
            raise ValueError(f"template {self.id!r}: text must use \\n line endings, not \\r")
        _split(self.id, self.text)
        return self

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        """Return a copy with ``update`` applied, fully re-validated (unlike pydantic's default).

        ``deep`` is accepted for compatibility; every field is immutable, so it changes nothing.
        """
        data: dict[str, Any] = {name: getattr(self, name) for name in type(self).model_fields}
        data.update(update or {})
        return self.model_validate(data)

    @property
    def placeholders(self) -> tuple[str, ...]:
        """The distinct placeholder names in ``text``, sorted; derived, so never serialised."""
        return tuple(sorted(set(_split(self.id, self.text)[1])))

    def render(self, values: Mapping[str, str]) -> str:
        """``text`` with each placeholder replaced by ``values[name]``, inserted verbatim.

        Raises ``ValueError`` listing every placeholder without a value and every key of
        ``values`` the template does not use. Values are never re-parsed, so braces in a value
        appear unchanged in the output.
        """
        literals, names = _split(self.id, self.text)
        missing = sorted(set(names) - values.keys())
        unexpected = sorted(values.keys() - set(names))
        if missing or unexpected:
            problems: list[str] = []
            if missing:
                problems.append(f"missing values for {missing}")
            if unexpected:
                problems.append(f"unexpected values for {unexpected}")
            raise ValueError(f"template {self.id!r}: {'; '.join(problems)}")
        parts = [literals[0]]
        for name, literal in zip(names, literals[1:], strict=True):
            parts.extend((values[name], literal))
        return "".join(parts)


@dataclass(frozen=True)
class Corpus:
    """The templates of one family at one dated version, sorted by id.

    Construction re-validates every template (so a copy made with ``model_construct`` that
    breaks the schema is rejected), sorts them by id, and raises ``CorpusError`` for an invalid
    template, a duplicate id, a template of another family, or a ``version`` or ``family`` that
    does not match its pattern.
    """

    version: str
    """The dated directory name, ``YYYY-MM``."""
    family: str
    """The family every template belongs to."""
    templates: tuple[Template, ...]
    """The templates, sorted by id."""

    def __post_init__(self) -> None:
        _check_family_and_version(self.family, self.version)
        validated: list[Template] = []
        for template in self.templates:
            data = {name: getattr(template, name, None) for name in Template.model_fields}
            try:
                validated.append(Template.model_validate(data))
            except ValidationError as error:
                raise CorpusError(f"corpus has an invalid template: {error}") from error
        ordered = tuple(sorted(validated, key=lambda template: template.id))
        for previous, template in pairwise(ordered):
            if previous.id == template.id:
                raise CorpusError(f"corpus has duplicate template id {template.id!r}")
        for template in ordered:
            if template.family != self.family:
                raise CorpusError(
                    f"template {template.id!r} has family {template.family!r}, "
                    f"not the corpus family {self.family!r}"
                )
        object.__setattr__(self, "templates", ordered)

    @property
    def ids(self) -> tuple[str, ...]:
        """The template ids, sorted."""
        return tuple(template.id for template in self.templates)

    def get(self, template_id: str) -> Template:
        """The template with id ``template_id``; ``KeyError`` naming the known ids otherwise."""
        for template in self.templates:
            if template.id == template_id:
                return template
        raise KeyError(
            f"no template {template_id!r} in {self.family}/{self.version}; "
            f"known ids: {list(self.ids)!r}"
        )

    def __iter__(self) -> Iterator[Template]:
        return iter(self.templates)

    def __len__(self) -> int:
        return len(self.templates)

    @property
    def content_hash(self) -> str:
        """SHA-256 hex digest of the corpus family and every template's stored fields.

        Hashed: the UTF-8 (here pure ASCII) bytes of ``json.dumps`` with ``sort_keys=True``,
        ``ensure_ascii=True`` and ``separators=(",", ":")`` applied to
        ``{"family": family, "format": "probo.attacks.corpus/1", "templates": [...]}``, where
        the list holds each template's six stored fields, sorted by id, with ``date`` in ISO
        form. ``placeholders`` is derived from ``text`` and not included; neither is the
        corpus ``version``, so identical content under two versions has one hash. The hash
        therefore does not depend on file order, file names beyond the id, or file line
        endings (``tomllib`` reads CRLF as LF).
        """
        payload = {
            "family": self.family,
            "format": _HASH_FORMAT,
            "templates": [template.model_dump(mode="json") for template in self.templates],
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("ascii")).hexdigest()


_FILE_KEYS = frozenset(Template.model_fields)


def _check_family(family: str) -> None:
    if re.fullmatch(NAME_PATTERN, family) is None:
        raise CorpusError(f"corpus family {family!r} does not match {NAME_PATTERN}")


def _check_family_and_version(family: str, version: str) -> None:
    _check_family(family)
    if re.fullmatch(VERSION_PATTERN, version) is None:
        raise CorpusError(f"corpus version {version!r} is not of the form YYYY-MM")


def _read_template(entry: Traversable) -> Template:
    raw = entry.read_bytes()
    if raw.startswith(_BOM):
        raise CorpusError(f"{entry}: starts with a UTF-8 byte order mark, which is not allowed")
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise CorpusError(f"{entry}: not valid UTF-8 TOML: {error}") from error
    problems: list[str] = []
    if unknown := sorted(data.keys() - _FILE_KEYS):
        problems.append(f"unknown keys {unknown}")
    if missing := sorted(_FILE_KEYS - data.keys()):
        problems.append(f"missing keys {missing}")
    if problems:
        raise CorpusError(f"{entry}: {'; '.join(problems)}")
    try:
        return Template.model_validate(data)
    except ValidationError as error:
        raise CorpusError(f"{entry}: {error}") from error


def load_corpus_from(directory: Traversable, *, family: str, version: str) -> Corpus:
    """Load every ``*.toml`` file directly in ``directory`` as one template each.

    ``directory`` is a ``pathlib.Path`` or any ``importlib.resources`` ``Traversable`` (such as
    a ``zipfile.Path``). Other files and subdirectories are ignored. Raises ``CorpusError``,
    naming the file, for invalid TOML, unknown or missing keys, wrong types, invalid
    placeholders, an id that differs from the file stem, a family that differs from
    ``family``, or an id already loaded from another entry.
    """
    _check_family_and_version(family, version)
    if not directory.is_dir():
        raise CorpusError(f"{directory}: not a directory")
    loaded: dict[str, str] = {}
    templates: list[Template] = []
    for entry in sorted(directory.iterdir(), key=lambda entry: entry.name):
        if not entry.name.endswith(".toml") or not entry.is_file():
            continue
        template = _read_template(entry)
        stem = entry.name.removesuffix(".toml")
        if template.id != stem:
            raise CorpusError(f"{entry}: id {template.id!r} does not match the file stem {stem!r}")
        if template.family != family:
            raise CorpusError(
                f"{entry}: family {template.family!r} does not match the directory's {family!r}"
            )
        if template.id in loaded:
            raise CorpusError(
                f"{entry}: duplicate template id {template.id!r}, already loaded from "
                f"{loaded[template.id]}"
            )
        loaded[template.id] = str(entry)
        templates.append(template)
    return Corpus(version=version, family=family, templates=tuple(templates))


def _packaged(family: str) -> Traversable:
    return files("probo.attacks") / "corpus" / family


def available_versions(family: str) -> tuple[str, ...]:
    """The dated version directories packaged for ``family``, sorted; empty if there are none."""
    _check_family(family)
    root = _packaged(family)
    if not root.is_dir():
        return ()
    return tuple(
        sorted(
            entry.name
            for entry in root.iterdir()
            if entry.is_dir() and re.fullmatch(VERSION_PATTERN, entry.name) is not None
        )
    )


def load_corpus(family: str = "static", version: str = "2026-11") -> Corpus:
    """Load the packaged corpus ``probo/attacks/corpus/<family>/<version>/``.

    Reads through ``importlib.resources``, so it works from a source tree, an installed wheel
    and a zip archive. Raises ``CorpusError`` if that version is not packaged, listing the
    versions that are, or if any file in it is invalid (see ``load_corpus_from``).
    """
    _check_family_and_version(family, version)
    root = _packaged(family) / version
    if not root.is_dir():
        raise CorpusError(
            f"no packaged corpus {family}/{version}; available versions of {family!r}: "
            f"{list(available_versions(family))!r}"
        )
    return load_corpus_from(root, family=family, version=version)
