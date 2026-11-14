# SPDX-License-Identifier: Apache-2.0
"""Corpus loading: file validation, ordering, content hashing and the packaged corpus."""

import hashlib
import subprocess
import sys
import tomllib
import warnings
import zipfile
from datetime import date
from pathlib import Path

import pytest

import probo
from probo.attacks import (
    Corpus,
    CorpusError,
    Template,
    available_versions,
    load_corpus,
    load_corpus_from,
)

from .template_support import EXAMPLE_TEXT, template, toml_file, toml_string, write


def load(directory: Path) -> Corpus:
    return load_corpus_from(directory, family="static", version="2026-11")


def test_valid_file_loads(tmp_path: Path) -> None:
    """A TOML file becomes a template with the file's fields and the text's placeholders."""
    write(tmp_path, "reference-note.toml", toml_file())
    corpus = load(tmp_path)
    assert (corpus.version, corpus.family, len(corpus)) == ("2026-11", "static", 1)
    loaded = corpus.get("reference-note")
    assert loaded == Template(
        id="reference-note",
        family="static",
        technique="Adds a neutral reference line",
        provenance="hand-written for Probo",
        date=date(2026, 11, 1),
        text=EXAMPLE_TEXT,
    )
    assert loaded.placeholders == ("customer_name", "reference_code")


def test_corpus_accessors(tmp_path: Path) -> None:
    """``ids``, iteration, length and ``get``; an unknown id raises KeyError naming the known."""
    for name in ("b", "a"):
        write(tmp_path, f"{name}.toml", toml_file(name))
    corpus = load(tmp_path)
    assert corpus.ids == ("a", "b")
    assert [t.id for t in corpus] == ["a", "b"]
    assert len(corpus) == 2
    assert corpus.get("b").id == "b"
    with pytest.raises(
        KeyError, match=r"no template 'c' in static/2026-11; known ids: \['a', 'b'\]"
    ):
        corpus.get("c")


def test_id_must_match_file_stem(tmp_path: Path) -> None:
    path = write(tmp_path, "other-name.toml", toml_file("reference-note"))
    with pytest.raises(CorpusError, match="does not match the file stem 'other-name'") as caught:
        load(tmp_path)
    assert str(path) in str(caught.value)


def test_family_must_match_directory(tmp_path: Path) -> None:
    path = write(tmp_path, "reference-note.toml", toml_file(family="dynamic"))
    with pytest.raises(CorpusError, match="family 'dynamic' does not match") as caught:
        load(tmp_path)
    assert str(path) in str(caught.value)


def test_duplicate_ids_in_a_zip_archive_are_rejected(tmp_path: Path) -> None:
    """A directory cannot hold two files with one stem, but a zip can hold two equal entries."""
    archive = tmp_path / "corpus.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # zipfile warns about the duplicate name
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("static/2026-11/reference-note.toml", toml_file())
            zf.writestr("static/2026-11/reference-note.toml", toml_file())
    with zipfile.ZipFile(archive) as zf:
        root = zipfile.Path(zf, "static/2026-11/")
        with pytest.raises(CorpusError, match="duplicate template id 'reference-note'") as caught:
            load_corpus_from(root, family="static", version="2026-11")
    assert "corpus.zip/static/2026-11/reference-note.toml" in str(caught.value)


def test_corpus_rejects_duplicate_ids_and_foreign_families() -> None:
    """Building a Corpus directly applies the same checks as loading one."""
    with pytest.raises(CorpusError, match="duplicate template id 'reference-note'"):
        Corpus(version="2026-11", family="static", templates=(template(), template()))
    foreign = template().model_copy(update={"family": "dynamic"})
    with pytest.raises(CorpusError, match="not the corpus family 'static'"):
        Corpus(version="2026-11", family="static", templates=(foreign,))
    with pytest.raises(CorpusError, match="YYYY-MM"):
        Corpus(version="2026-13", family="static", templates=())
    with pytest.raises(CorpusError, match="corpus family 'Static' does not match"):
        Corpus(version="2026-11", family="Static", templates=())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "../Bad Id"),
        ("technique", "two\nlines"),
        ("text", "carriage\rreturn"),
        ("text", "{0.__class__}"),
        ("date", "2026-11-01"),
    ],
)
def test_corpus_revalidates_unvalidated_templates(field: str, value: object) -> None:
    """A ``model_construct`` instance that breaks the schema cannot enter a corpus."""
    broken = Template.model_construct(None, **{**template().model_dump(), field: value})
    with pytest.raises(CorpusError, match="corpus has an invalid template"):
        Corpus(version="2026-11", family="static", templates=(broken,))


def test_corpus_rejects_a_template_missing_a_field() -> None:
    fields = template().model_dump()
    del fields["text"]
    with pytest.raises(CorpusError, match="corpus has an invalid template"):
        Corpus("2026-11", "static", (Template.model_construct(None, **fields),))


@pytest.mark.parametrize(
    ("extra", "drop", "message"),
    [
        ('author = "someone"\n', None, r"unknown keys \['author'\]"),
        ("placeholders = []\n", None, r"unknown keys \['placeholders'\]"),
        ("", "technique", r"missing keys \['technique'\]"),
        ('Text = "x"\n', "text", r"unknown keys \['Text'\]; missing keys \['text'\]"),
    ],
)
def test_unknown_and_missing_keys_name_the_file(
    tmp_path: Path, extra: str, drop: str | None, message: str
) -> None:
    content = toml_file(raw={drop: None} if drop is not None else None, extra=extra)
    path = write(tmp_path, "reference-note.toml", content)
    with pytest.raises(CorpusError, match=message) as caught:
        load(tmp_path)
    assert str(caught.value).startswith(f"{path}: ")


@pytest.mark.parametrize(
    ("content", "field"),
    [
        (toml_file(raw={"date": '"2026-11-01"'}), "date"),
        (toml_file(raw={"date": "2026-11-01T09:30:00"}), "date"),
        (toml_file(raw={"date": "2026-11-01T09:30:00Z"}), "date"),
        (toml_file(raw={"date": "20261101"}), "date"),
        (toml_file(raw={"id": '["reference-note"]'}), "id"),
        (toml_file(raw={"text": "7"}), "text"),
        (toml_file(raw={"family": "true"}), "family"),
    ],
)
def test_wrong_types_name_the_file(tmp_path: Path, content: str, field: str) -> None:
    """``date`` must be a bare TOML local date; strings, datetimes and numbers are rejected."""
    path = write(tmp_path, "reference-note.toml", content)
    with pytest.raises(CorpusError) as caught:
        load(tmp_path)
    message = str(caught.value)
    assert message.startswith(f"{path}: ")
    assert f"\n{field}\n" in message


def test_invalid_placeholder_names_file_id_and_fragment(tmp_path: Path) -> None:
    path = write(tmp_path, "reference-note.toml", toml_file(text="Hello {name.attr}."))
    with pytest.raises(CorpusError) as caught:
        load(tmp_path)
    message = str(caught.value)
    assert message.startswith(f"{path}: ")
    assert "template 'reference-note': invalid brace syntax '{name.attr}'" in message


@pytest.mark.parametrize(
    "content", ["id = ", "id = 'a'\nid = 'b'\n", b"\xff\xfe".decode("latin-1")]
)
def test_unparseable_file_names_the_file(tmp_path: Path, content: str) -> None:
    path = tmp_path / "reference-note.toml"
    path.write_bytes(content.encode("latin-1"))
    with pytest.raises(CorpusError, match="not valid UTF-8 TOML") as caught:
        load(tmp_path)
    assert str(caught.value).startswith(f"{path}: ")


def test_other_entries_are_ignored(tmp_path: Path) -> None:
    """Only regular files ending in ``.toml`` are read; anything else is skipped unparsed."""
    write(tmp_path, "reference-note.toml", toml_file())
    write(tmp_path, "README.md", "# not a template {0}\n")
    write(tmp_path, "notes.txt", "id = broken")
    write(tmp_path, "reference-note.toml.bak", "id = broken")
    write(tmp_path, "upper.TOML", "id = broken")
    write(tmp_path / "nested.toml", "inner.toml", "id = broken")
    assert load(tmp_path).ids == ("reference-note",)


def test_empty_directory_loads_as_empty_corpus(tmp_path: Path) -> None:
    corpus = load(tmp_path)
    assert (len(corpus), corpus.ids, list(corpus)) == (0, (), [])


def test_missing_directory_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="not a directory"):
        load(tmp_path / "absent")


def test_byte_order_mark_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "reference-note.toml"
    path.write_bytes(b"\xef\xbb\xbf" + toml_file().encode("utf-8"))
    with pytest.raises(CorpusError) as caught:
        load(tmp_path)
    assert str(caught.value) == (
        f"{path}: starts with a UTF-8 byte order mark, which is not allowed"
    )


BAD_NAMES = [
    ("../x", "2026-11", "corpus family '../x' does not match"),
    ("static", "../2026-11", "corpus version '../2026-11' is not of the form YYYY-MM"),
    ("static", "2026-11/..", "corpus version '2026-11/..' is not of the form YYYY-MM"),
]


@pytest.mark.parametrize(("family", "version", "message"), BAD_NAMES)
def test_load_corpus_from_checks_names_before_reading(
    tmp_path: Path, family: str, version: str, message: str
) -> None:
    """The directory holds a file that fails to parse, so reading anything changes the error."""
    write(tmp_path, "poison.toml", "this is = not toml")
    with pytest.raises(CorpusError, match="not valid UTF-8 TOML"):
        load(tmp_path)
    with pytest.raises(CorpusError) as caught:
        load_corpus_from(tmp_path, family=family, version=version)
    assert str(caught.value).startswith(message)


def no_resource_access(_package: str) -> Path:
    raise AssertionError("packaged resources were accessed")


@pytest.mark.parametrize(("family", "version", "message"), BAD_NAMES)
def test_load_corpus_checks_names_before_touching_resources(
    monkeypatch: pytest.MonkeyPatch, family: str, version: str, message: str
) -> None:
    monkeypatch.setattr("probo.attacks.templates.files", no_resource_access)
    with pytest.raises(CorpusError) as caught:
        load_corpus(family, version)
    assert str(caught.value).startswith(message)


@pytest.mark.parametrize("family", ["../x", "static/..", "", "Static"])
def test_available_versions_checks_family_before_touching_resources(
    monkeypatch: pytest.MonkeyPatch, family: str
) -> None:
    monkeypatch.setattr("probo.attacks.templates.files", no_resource_access)
    with pytest.raises(CorpusError) as caught:
        available_versions(family)
    assert str(caught.value).startswith(f"corpus family {family!r} does not match")


def corpus_written(directory: Path, order: list[str], newline: str = "\n") -> Corpus:
    for name in order:
        write(
            directory,
            f"{name}.toml",
            toml_file(name, text=f"Line one {{a}}\nline {name}."),
            newline=newline,
        )
    return load(directory)


def test_order_is_by_id_not_by_file_creation(tmp_path: Path) -> None:
    first = corpus_written(tmp_path / "one", ["b-2", "a-1", "c-3"])
    second = corpus_written(tmp_path / "two", ["c-3", "b-2", "a-1"])
    assert first.ids == second.ids == ("a-1", "b-2", "c-3")
    assert first == second


def test_content_hash_ignores_file_order_and_line_endings(tmp_path: Path) -> None:
    lf = corpus_written(tmp_path / "lf", ["a-1", "b-2"])
    crlf = corpus_written(tmp_path / "crlf", ["b-2", "a-1"], newline="\r\n")
    assert crlf.get("a-1").text == "Line one {a}\nline a-1."
    assert len(lf.content_hash) == 64
    assert lf.content_hash == crlf.content_hash
    assert lf.content_hash == Corpus("2027-01", "static", lf.templates[::-1]).content_hash


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "reference-notes"),
        ("family", "statics"),
        ("technique", "Adds a neutral reference line."),
        ("provenance", "hand-written for Probo "),
        ("date", date(2026, 11, 2)),
        ("text", EXAMPLE_TEXT + " "),
    ],
)
def test_content_hash_changes_with_every_field(field: str, value: object) -> None:
    original = template()
    changed = Template.model_validate({**original.model_dump(), field: value})
    family = changed.family
    before = Corpus("2026-11", original.family, (original,)).content_hash
    assert Corpus("2026-11", family, (changed,)).content_hash != before


def test_content_hash_changes_when_a_template_is_added_or_removed() -> None:
    one = Corpus("2026-11", "static", (template(),))
    two = Corpus("2026-11", "static", (template(), template(template_id="second")))
    empty = Corpus("2026-11", "static", ())
    assert len({one.content_hash, two.content_hash, empty.content_hash}) == 3


def test_available_versions_lists_dated_directories_sorted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only ``YYYY-MM`` directories count; files and other names are skipped."""
    family = tmp_path / "corpus" / "static"
    for name in ("2026-11", "2025-03", "2026-02", "drafts", "2026-13"):
        (family / name).mkdir(parents=True)
    write(family, "2027-01", "a file, not a version")

    def packaged_files(_package: str) -> Path:
        return tmp_path

    monkeypatch.setattr("probo.attacks.templates.files", packaged_files)
    assert available_versions("static") == ("2025-03", "2026-02", "2026-11")
    assert available_versions("unknown") == ()
    with pytest.raises(CorpusError, match="available versions of 'static': "):
        load_corpus("static", "2024-01")


def test_packaged_versions_include_2026_11() -> None:
    versions = available_versions("static")
    assert "2026-11" in versions
    assert list(versions) == sorted(versions)


def test_packaged_corpus_loads_and_every_template_renders() -> None:
    """Assumes no template count: loading succeeds and each template renders when filled."""
    corpus = load_corpus()
    assert (corpus.family, corpus.version) == ("static", "2026-11")
    assert corpus == load_corpus("static", "2026-11")
    assert len(corpus.content_hash) == 64
    for loaded in corpus:
        rendered = loaded.render({name: f"<{name}>" for name in loaded.placeholders})
        assert all(f"<{name}>" in rendered for name in loaded.placeholders)


ZIP_SCRIPT = """
import sys
import tomllib
sys.path.insert(0, sys.argv[1])
import probo.attacks as attacks
assert attacks.__file__.startswith(sys.argv[1]), attacks.__file__
corpus = attacks.load_corpus()
print(corpus.ids, attacks.available_versions("static"))
print(corpus.get("reference-note").render({"reference_code": "R-1", "customer_name": "Sam"}))
"""


def test_packaged_corpus_loads_from_a_zip(tmp_path: Path) -> None:
    """``load_corpus`` reads through importlib.resources, so a zipped package works."""
    package = Path(probo.__file__).parent
    archive = tmp_path / "probo.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in sorted(package.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                zf.write(path, Path("probo") / path.relative_to(package))
        zf.writestr("probo/attacks/corpus/static/2026-11/reference-note.toml", toml_file())
    result = subprocess.run(
        [sys.executable, "-I", "-c", ZIP_SCRIPT, str(archive)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        f"('reference-note',) {available_versions('static')!r}",
        "Please also note reference R-1 when replying to Sam.",
    ]


# Golden values. Changing either digest changes the content_hash of every published corpus, so
# results that pinned a hash stop matching: only change them together with the hash format tag.
EMPTY_STATIC_HASH = "9f74e2b2fe48a2853032f200ce468d27e12479a3501cb9d5dbb0aac408afa200"
EXAMPLE_HASH = "dfba82b12e3bbc3eca9ca6d16e50331611899f1861e2836840f7a06e9b527487"
EXAMPLE_SERIALISATION = (
    '{"family":"static","format":"probo.attacks.corpus/1","templates":[{"date":"2026-11-01",'
    '"family":"static","id":"reference-note","provenance":"hand-written for Probo",'
    '"technique":"Adds a neutral reference line","text":"Please also note reference '
    '{reference_code} when replying to {customer_name}."}]}'
)


def test_content_hash_golden_values() -> None:
    """The digests are pinned, and are SHA-256 of the serialisation the docstring describes."""
    assert Corpus("2026-11", "static", ()).content_hash == EMPTY_STATIC_HASH
    assert Corpus("2026-11", "static", (template(),)).content_hash == EXAMPLE_HASH
    assert hashlib.sha256(EXAMPLE_SERIALISATION.encode("ascii")).hexdigest() == EXAMPLE_HASH


def test_content_hash_covers_family_but_not_version() -> None:
    """Empty corpora of different families differ; the same content under two versions does not."""
    assert Corpus("2026-11", "dynamic", ()).content_hash != EMPTY_STATIC_HASH
    assert Corpus("2030-01", "static", ()).content_hash == EMPTY_STATIC_HASH


TRICKY_STRINGS = [
    "\nleading newline",
    "trailing newline\n",
    "\n\n",
    'quote " and triple """ quotes',
    "back\\slash \\n not an escape \\",
    "tab\there",
    "control \x00 \x08 \x1f \x7f",
    "carriage \r return",
    "non-ASCII \u2028 \u00e9 \U0001f600",
    "{{braces}} {name}",
    "'''",
]


@pytest.mark.parametrize("value", TRICKY_STRINGS)
@pytest.mark.parametrize("multiline", [False, True])
def test_toml_string_helper_is_exact(value: str, multiline: bool) -> None:
    """The test helper itself: every string parses back unchanged, with LF or CRLF files."""
    source = f"v = {toml_string(value, multiline=multiline)}\n"
    assert tomllib.loads(source)["v"] == value
    assert tomllib.loads(source.replace("\n", "\r\n"))["v"] == value


def test_toml_file_helper_keeps_a_leading_newline(tmp_path: Path) -> None:
    write(tmp_path, "reference-note.toml", toml_file(text="\nX"), newline="\r\n")
    assert load(tmp_path).get("reference-note").text == "\nX"


def test_toml_string_helper_rejects_surrogates() -> None:
    with pytest.raises(ValueError, match="surrogate"):
        toml_string("\ud800")
