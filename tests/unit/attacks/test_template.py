# SPDX-License-Identifier: Apache-2.0
"""Template: field rules, placeholder parsing and exact rendering."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from probo.attacks import Template

from .template_support import EXAMPLE_TEXT, template

FIELDS = {
    "id": "reference-note",
    "family": "static",
    "technique": "Adds a neutral reference line",
    "provenance": "hand-written for Probo",
    "date": date(2026, 11, 1),
    "text": EXAMPLE_TEXT,
}


def test_fields_and_placeholders() -> None:
    """Stored fields come back unchanged; placeholders are the distinct names, sorted."""
    loaded = Template.model_validate(FIELDS)
    assert loaded.model_dump() == FIELDS
    assert loaded.placeholders == ("customer_name", "reference_code")
    assert template("{b} {a} {b} {_x1}").placeholders == ("_x1", "a", "b")
    assert template("no placeholders").placeholders == ()


def test_model_is_frozen_and_round_trips() -> None:
    """Assignment fails; dumps validate back; render re-checks an unvalidated instance."""
    loaded = template()
    for name in Template.model_fields:
        with pytest.raises(ValidationError, match="frozen"):
            setattr(loaded, name, "changed")
    assert Template.model_validate(loaded.model_dump()) == loaded
    assert Template.model_validate_json(loaded.model_dump_json()) == loaded
    unvalidated = Template.model_construct(None, **{**FIELDS, "text": "{0.__class__}"})
    with pytest.raises(ValueError, match="invalid brace syntax"):
        unvalidated.render({})
    with pytest.raises(ValidationError, match="Extra inputs"):
        Template.model_validate({**FIELDS, "placeholders": ["customer_name"]})


def test_render_substitutes_every_placeholder() -> None:
    """Each occurrence of a placeholder is replaced by its value."""
    rendered = template("{a}-{b}-{a}").render({"a": "1", "b": "2"})
    assert rendered == "1-2-1"
    assert template().render({"reference_code": "R-1", "customer_name": "Sam"}) == (
        "Please also note reference R-1 when replying to Sam."
    )
    assert template("plain").render({}) == "plain"


def test_render_lists_missing_and_unexpected_values() -> None:
    """A missing value and an unused key are both errors, each listed by name."""
    with pytest.raises(ValueError, match=r"missing values for \['customer_name'\]"):
        template().render({"reference_code": "R-1"})
    with pytest.raises(ValueError, match=r"unexpected values for \['other'\]"):
        template("{a}").render({"a": "1", "other": "2"})
    with pytest.raises(ValueError) as caught:
        template("{a} {b}").render({"b": "1", "c": "2", "d": "3"})
    message = str(caught.value)
    assert "'reference-note'" in message
    assert "missing values for ['a']" in message
    assert "unexpected values for ['c', 'd']" in message


@pytest.mark.parametrize(
    "value", ["{other}", "{{", "}}", "{0}", "{a.__class__}", "{a[0]}", "{a!r:>9}", "{"]
)
def test_render_inserts_values_verbatim(value: str) -> None:
    """Braces in a value are never interpreted, escaped or substituted."""
    assert template("[{a}] {b}").render({"a": value, "b": value}) == f"[{value}] {value}"


def test_escaped_braces_become_single_braces() -> None:
    """``{{`` and ``}}`` render as literal braces and never start a placeholder."""
    assert template("{{a}}").placeholders == ()
    assert template("{{a}}").render({}) == "{a}"
    assert template("{{{a}}}").render({"a": "x"}) == "{x}"
    assert template("}}{{").render({}) == "}{"
    assert template("{{}}").render({}) == "{}"


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("positional {} here", "{}"),
        ("index {0} here", "{0}"),
        ("attribute {a.b} here", "{a.b}"),
        ("item {a[0]} here", "{a[0]}"),
        ("spec {a:>10} here", "{a:>10}"),
        ("conversion {a!r} here", "{a!r}"),
        ("upper {Name} here", "{Name}"),
        ("spaced { a } here", "{ a }"),
        ("digit first {1a} here", "{1a}"),
        ("nested {a{b}} here", "{a{b}"),
        ("unclosed {a here", "{a here"),
        ("unopened a} here", "}"),
        ("odd closing {a}} here", "}"),
        ("trailing {", "{"),
    ],
)
def test_invalid_brace_syntax_is_rejected(text: str, fragment: str) -> None:
    """Every brace use other than ``{name}``, ``{{`` and ``}}`` fails, naming id and fragment."""
    with pytest.raises(ValidationError) as caught:
        template(text, template_id="bad-braces")
    message = str(caught.value)
    assert "template 'bad-braces'" in message
    assert f"invalid brace syntax {fragment!r}" in message


def test_long_fragment_is_truncated() -> None:
    """An unclosed brace reports at most 40 characters of what follows it."""
    with pytest.raises(ValidationError) as caught:
        template("{" + "a" * 100)
    assert f"invalid brace syntax {'{' + 'a' * 39!r} at offset 0" in str(caught.value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "Upper"),
        ("id", "double--hyphen"),
        ("id", "-leading"),
        ("id", "trailing-"),
        ("id", "under_score"),
        ("id", ""),
        ("family", "Static"),
        ("family", "a b"),
        ("technique", ""),
        ("technique", "   "),
        ("technique", "two\nlines"),
        ("technique", "carriage\rreturn"),
        ("technique", "trailing newline\n"),
        ("technique", "line\u2028separator"),
        ("technique", "paragraph\u2029separator"),
        ("technique", "next\x85line"),
        ("technique", "vertical\x0btab"),
        ("technique", "form\x0cfeed"),
        ("technique", "file\x1cseparator"),
        ("technique", "group\x1dseparator"),
        ("technique", "record\x1eseparator"),
        ("provenance", ""),
        ("provenance", " \t"),
        ("text", ""),
        ("text", "\n  \n"),
        ("text", "windows\r\nline"),
    ],
)
def test_invalid_field_values_are_rejected(field: str, value: str) -> None:
    """Ids and families follow the name rule; text fields are non-blank; technique is one line."""
    with pytest.raises(ValidationError):
        Template.model_validate({**FIELDS, field: value})


@pytest.mark.parametrize("value", ["2026-11-01", datetime(2026, 11, 1), 20261101, None])
def test_date_must_be_a_date(value: object) -> None:
    """Strict: a string, a datetime or a number is not accepted as ``date``."""
    with pytest.raises(ValidationError):
        Template.model_validate({**FIELDS, "date": value})


def test_unknown_field_is_rejected() -> None:
    """Extra fields are forbidden."""
    with pytest.raises(ValidationError, match="Extra inputs"):
        Template.model_validate({**FIELDS, "author": "someone"})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "../Bad Id"),
        ("family", "Bad Family"),
        ("technique", "two\nlines"),
        ("provenance", " "),
        ("date", "2026-11-01"),
        ("text", "carriage\rreturn"),
        ("text", "{0}"),
    ],
)
def test_model_copy_revalidates(field: str, value: object) -> None:
    """Unlike pydantic's default, ``model_copy(update=...)`` applies every field rule."""
    with pytest.raises(ValidationError):
        template().model_copy(update={field: value})


def test_model_copy_applies_valid_updates() -> None:
    copied = template().model_copy(update={"text": "Hi {who}."}, deep=True)
    assert (copied.text, copied.placeholders, copied.id) == (
        "Hi {who}.",
        ("who",),
        "reference-note",
    )
