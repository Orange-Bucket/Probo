# SPDX-License-Identifier: Apache-2.0
"""Canary token derivation and the exact token format."""

import hashlib
from typing import cast

import pytest

from probo.checks import CANARY_PATTERN, CANARY_PREFIX, derive_canary, is_canary

INPUTS: list[tuple[int, tuple[str | int, ...]]] = [
    (seed, (f"sample-{sample}", epoch, f"record-{record}"))
    for seed in range(10)
    for sample in range(5)
    for epoch in range(4)
    for record in range(5)
]


def test_tokens_have_the_exact_format() -> None:
    """Every derived token is the prefix plus 32 lowercase hex characters."""
    for seed, parts in INPUTS:
        token = derive_canary(seed, *parts)
        assert is_canary(token)
        assert token.startswith(CANARY_PREFIX)
        assert len(token) == len(CANARY_PREFIX) + 32


def test_derivation_is_deterministic() -> None:
    """The same inputs give the same token on every call."""
    for seed, parts in INPUTS:
        assert derive_canary(seed, *parts) == derive_canary(seed, *parts)


def test_derivation_is_pinned_to_its_documented_encoding() -> None:
    """The token is SHA-256 over the domain tag and tagged, length-prefixed items.

    Pinned so that a published run's tokens can be reproduced by later versions.
    """

    def item(tag: bytes, payload: bytes) -> bytes:
        return tag + len(payload).to_bytes(8, "big") + payload

    data = b"probo-canary-v1\x00" + b"".join(
        [item(b"i", b"\x00"), item(b"s", b"sample-1"), item(b"i", b"\x01"), item(b"s", b"record-7")]
    )
    expected = CANARY_PREFIX + hashlib.sha256(data).hexdigest()[:32]
    assert derive_canary(0, "sample-1", 1, "record-7") == expected
    assert expected == "PROBO-CANARY-f8ddf6342275295b46aca4044ec79056"


def test_negative_int_encoding_is_pinned() -> None:
    """Negative ints are signed two's complement in (bit_length + 8) // 8 bytes.

    -128 takes two bytes (ff80), one more than minimal; the encoding is kept for stability.
    """

    def item(tag: bytes, payload: bytes) -> bytes:
        return tag + len(payload).to_bytes(8, "big") + payload

    data = b"probo-canary-v1\x00" + b"".join(
        [item(b"i", b"\xf9"), item(b"s", b"sample-1"), item(b"i", b"\xff"), item(b"i", b"\xff\x80")]
    )
    expected = CANARY_PREFIX + hashlib.sha256(data).hexdigest()[:32]
    assert derive_canary(-7, "sample-1", -1, -128) == expected
    assert expected == "PROBO-CANARY-7fd6cdad57c2e6c0b2662b7e9fcecb66"


def test_distinct_inputs_give_distinct_tokens() -> None:
    """A thousand distinct input tuples give a thousand distinct tokens."""
    tokens = {derive_canary(seed, *parts) for seed, parts in INPUTS}
    assert len(tokens) == len(INPUTS)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ((0, "ab", "c"), (0, "a", "bc")),
        ((0, "a", ""), (0, "a")),
        ((0, ""), (0,)),
        ((0, "1"), (0, 1)),
        ((1,), (0, 1)),
        ((0, 1), (0, -1)),
        ((1,), (-1,)),
        ((0, -1), (0, 255)),
        ((0, -128), (0, 128)),
        ((0, 2**200), (0, 2**200 + 1)),
        ((0, "a\x00b"), (0, "a", "b")),
        ((0, "\ud800"), (0, "\udfff")),
    ],
)
def test_ambiguous_concatenations_give_different_tokens(
    left: tuple[int, *tuple[str | int, ...]], right: tuple[int, *tuple[str | int, ...]]
) -> None:
    """Inputs that would collide under naive concatenation or str() give different tokens."""
    assert derive_canary(*left) != derive_canary(*right)


@pytest.mark.parametrize("bad", [True, False, 1.5, None, b"bytes"])
def test_non_int_or_str_inputs_are_refused(bad: object) -> None:
    """Only str and int are accepted, and bool is refused so it cannot alias 0 or 1."""
    with pytest.raises(TypeError):
        derive_canary(0, cast("str", bad))
    with pytest.raises(TypeError, match="seed"):
        derive_canary(cast("int", bad))


@pytest.mark.parametrize("bad", ["0", "", "seed"])
def test_a_str_seed_is_refused(bad: str) -> None:
    """The seed must be an int; a str is accepted only as a part."""
    with pytest.raises(TypeError, match="seed must be an int"):
        derive_canary(cast("int", bad))
    assert is_canary(derive_canary(0, bad))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "canary",
        CANARY_PREFIX,
        CANARY_PREFIX + "0" * 31,
        CANARY_PREFIX + "0" * 33,
        CANARY_PREFIX + "A" * 32,
        CANARY_PREFIX + "g" * 32,
        "probo-canary-" + "0" * 32,
        "PROBO_CANARY_" + "0" * 32,
        " " + CANARY_PREFIX + "0" * 32,
        CANARY_PREFIX + "0" * 32 + "\n",
        CANARY_PREFIX + "0" * 32 + " ",
    ],
)
def test_is_canary_rejects_anything_but_the_exact_format(text: str) -> None:
    """Wrong length, case, alphabet, prefix or surrounding text is not a token."""
    assert not is_canary(text)


def test_pattern_finds_tokens_inside_text() -> None:
    """The compiled pattern locates a token inside longer text."""
    token = derive_canary(3, "sample", 0, "record")
    found = CANARY_PATTERN.search(f"id: {token}.")
    assert found is not None
    assert found.group() == token
