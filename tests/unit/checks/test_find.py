# SPDX-License-Identifier: Apache-2.0
"""Finding a canary token in the text fields of one message, in every documented form."""

import base64
import codecs
import hashlib
import time
import urllib.parse
from collections.abc import Callable

import pytest

from probo.checks import CANARY_PREFIX, CanaryForm, CanaryMatch, derive_canary, find_canary

TOKENS = [
    derive_canary(seed, f"sample-{seed}", epoch, "record-1")
    for seed in range(4)
    for epoch in (0, 1)
]
OTHER = derive_canary(99, "sample-x", 0, "record-2")


def only(form: CanaryForm, *fields: int) -> list[CanaryMatch]:
    """The result for exactly one match of ``form`` in ``fields``."""
    return [CanaryMatch(form, fields)]


def hex_part(token: str) -> str:
    """The 32 hex characters after the prefix."""
    return token[len(CANARY_PREFIX) :]


def filler(size: int) -> bytes:
    """Deterministic pseudo-random bytes unrelated to any token."""
    out = b""
    counter = 0
    while len(out) < size:
        out += hashlib.sha256(b"filler" + counter.to_bytes(8, "big")).digest()
        counter += 1
    return out[:size]


# --- Plain-text forms ------------------------------------------------------------------------


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize(
    "template", ["{t}", "Hello, the id is {t}.", "x{t}y", "line one\n{t}\nline three"]
)
def test_verbatim_token_is_found(token: str, template: str) -> None:
    """The exact token anywhere in a field is a verbatim match in that field."""
    assert find_canary(token, [template.format(t=token)]) == only(CanaryForm.VERBATIM, 0)
    assert find_canary(token, ["subject", template.format(t=token)]) == only(CanaryForm.VERBATIM, 1)


CASE_CHANGES: list[Callable[[str], str]] = [
    str.upper,
    str.lower,
    str.swapcase,
    str.title,
    lambda t: t[:5].lower() + t[5:].upper(),
]


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize("transform", CASE_CHANGES)
def test_case_folded_token_is_found(token: str, transform: Callable[[str], str]) -> None:
    """The token with different ASCII letter case is a case-folded match."""
    changed = transform(token)
    assert changed != token
    assert find_canary(token, [f"see {changed} here"]) == only(CanaryForm.CASE_FOLDED, 0)


SEPARATORS = [" ", "-", ".", "_", "\n", "\r\n", " - ", "\u200b", "\u00a0", "=\r\n", "/"]


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize("separator", SEPARATORS)
def test_token_with_separators_between_characters_is_found(token: str, separator: str) -> None:
    """Non-alphanumeric characters between every character, in any case, are a separated match."""
    for variant in (token, token.upper()):
        spaced = separator.join(variant)
        assert find_canary(token, [f"note: {spaced} end"]) == only(CanaryForm.SEPARATED, 0)


@pytest.mark.parametrize("token", TOKENS)
def test_token_with_hyphens_removed_or_wrapped_is_found(token: str) -> None:
    """Dropping the hyphens, or wrapping the token over lines, is a separated match."""
    assert find_canary(token, [token.replace("-", "")]) == only(CanaryForm.SEPARATED, 0)
    wrapped = "\n".join(token[i : i + 8] for i in range(0, len(token), 8))
    assert find_canary(token, [wrapped]) == only(CanaryForm.SEPARATED, 0)
    assert find_canary(token, [token.replace("-", " ")]) == only(CanaryForm.SEPARATED, 0)


@pytest.mark.parametrize("token", TOKENS)
def test_token_split_across_two_fields_is_found_at_every_cut(token: str) -> None:
    """The end of one field and the start of the next together forming the token match."""
    for cut in range(1, len(token)):
        fields = [f"Re: {token[:cut]}", f"{token[cut:]} rest of body"]
        assert find_canary(token, fields) == only(CanaryForm.SPLIT_ACROSS_FIELDS, 0, 1)
        padded = [f"Re: {token[:cut].upper()} \n", f"\n  {token[cut:]}"]
        assert find_canary(token, padded) == only(CanaryForm.SPLIT_ACROSS_FIELDS, 0, 1)


@pytest.mark.parametrize("token", TOKENS)
def test_token_split_across_more_than_two_fields_is_found(token: str) -> None:
    """A token spanning several fields lists each non-empty field it touches."""
    three = ["a " + token[:10], token[10:20], token[20:] + " z"]
    assert find_canary(token, three) == only(CanaryForm.SPLIT_ACROSS_FIELDS, 0, 1, 2)
    gap = ["a " + token[:10], "", "  ", token[10:]]
    assert find_canary(token, gap) == only(CanaryForm.SPLIT_ACROSS_FIELDS, 0, 3)
    assert find_canary(token, ["", token[:20], token[20:], ""]) == only(
        CanaryForm.SPLIT_ACROSS_FIELDS, 1, 2
    )


def test_several_forms_in_one_message_are_each_reported_in_stable_order() -> None:
    """Different forms and fields are reported once each, by field indices then form."""
    for token in TOKENS:
        encoded = base64.b64encode(token.encode()).decode()
        fields = [
            f"{token} and {token.upper()} and {token} again",
            encoded + " " + " ".join(token),
            token[:20],
            token[20:] + " " + token.encode().hex(),
        ]
        expected = [
            CanaryMatch(CanaryForm.VERBATIM, (0,)),
            CanaryMatch(CanaryForm.CASE_FOLDED, (0,)),
            CanaryMatch(CanaryForm.SEPARATED, (1,)),
            CanaryMatch(CanaryForm.BASE64, (1,)),
            CanaryMatch(CanaryForm.SPLIT_ACROSS_FIELDS, (2, 3)),
            CanaryMatch(CanaryForm.HEX, (3,)),
        ]
        assert find_canary(token, fields) == expected
        assert find_canary(token, fields) == find_canary(token, list(fields))


# --- Encoded forms ---------------------------------------------------------------------------

# Prefix bytes that make the URL-safe and standard encodings of the payload differ.
EDGE_BYTES = b"\xfb\xff\xfe\xfa\xf8"


def b64_variants(payload: bytes) -> list[str]:
    """The payload in both alphabets, padded and unpadded."""
    std = base64.b64encode(payload).decode()
    url = base64.urlsafe_b64encode(payload).decode()
    return [std, std.rstrip("="), url, url.rstrip("=")]


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize("hex_only", [False, True])
def test_base64_of_token_is_found_at_every_offset_alphabet_and_padding(
    token: str, hex_only: bool
) -> None:
    """Base64 of the token or its hex part, inside any payload, is a base64 match."""
    data = (hex_part(token) if hex_only else token).encode()
    for before in range(6):
        for after in range(4):
            payload = EDGE_BYTES[:before] + data + EDGE_BYTES[:after]
            for encoded in b64_variants(payload):
                assert find_canary(token, [f"attachment: {encoded}"]) == only(
                    CanaryForm.BASE64, 0
                ), (before, after, encoded)


def test_url_safe_alphabet_case_is_exercised() -> None:
    """The offset test above really produces payloads whose two encodings differ."""
    payload = EDGE_BYTES[:2] + TOKENS[0].encode() + EDGE_BYTES[:2]
    assert base64.b64encode(payload) != base64.urlsafe_b64encode(payload)


@pytest.mark.parametrize("token", TOKENS)
def test_base64_with_line_breaks_or_across_fields_is_found(token: str) -> None:
    """MIME line wrapping is ignored, and base64 running across fields lists both fields."""
    record = b"name: Jane Example\nnotes: " + token.encode() + b"\n" + filler(300)
    mime = base64.encodebytes(record).decode()
    assert "\n" in mime.strip()
    assert find_canary(token, [mime]) == only(CanaryForm.BASE64, 0)
    encoded = base64.b64encode(token.encode()).decode()
    middle = len(encoded) // 2
    fields = [f"part one {encoded[:middle]}", f"{encoded[middle:]} part two"]
    assert find_canary(token, fields) == only(CanaryForm.BASE64, 0, 1)


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize("hex_only", [False, True])
def test_hex_of_token_is_found_in_any_case_and_layout(token: str, hex_only: bool) -> None:
    """The ASCII bytes as hex, upper or lower case, spaced or embedded, is a hex match."""
    digits = (hex_part(token) if hex_only else token).encode().hex()
    pairs = [digits[i : i + 2] for i in range(0, len(digits), 2)]
    dump = filler(16).hex() + digits + filler(16).hex()
    for layout in (digits, digits.upper(), " ".join(pairs), ":".join(pairs).upper(), dump):
        assert find_canary(token, [f"bytes: {layout}"]) == only(CanaryForm.HEX, 0), layout
    middle = len(digits) // 2 + 1
    fields = [f"x {digits[:middle]}", f"{digits[middle:]} y"]
    assert find_canary(token, fields) == only(CanaryForm.HEX, 0, 1)


# --- The hex part without the prefix ---------------------------------------------------------

DAMAGED_PREFIXES = ["", "id ", "PROBO-CANARI-", "CANARY-", "probo canary z", "PROBO%2DCANARY%2D"]


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize("prefix", DAMAGED_PREFIXES)
def test_hex_part_without_the_prefix_is_found(token: str, prefix: str) -> None:
    """The hex part alone or after a damaged prefix, in any case or spacing, is prefix-stripped."""
    digits = hex_part(token)
    for variant in (
        digits,
        digits.upper(),
        " ".join(digits),
        "-".join(digits[i : i + 4] for i in range(0, 32, 4)),
    ):
        assert find_canary(token, [f"{prefix}{variant} end"]) == only(CanaryForm.PREFIX_STRIPPED, 0)
        assert find_canary(token, ["subject", f"{prefix}{variant}"]) == only(
            CanaryForm.PREFIX_STRIPPED, 1
        )


@pytest.mark.parametrize("token", TOKENS)
def test_hex_part_split_across_fields_is_found_at_every_cut(token: str) -> None:
    """The hex part running across consecutive fields lists each field it touches."""
    digits = hex_part(token)
    for cut in range(1, 32):
        fields = [f"ref {digits[:cut]}", f"{digits[cut:].upper()} \n rest"]
        assert find_canary(token, fields) == only(CanaryForm.PREFIX_STRIPPED, 0, 1)
    spread = ["a " + digits[:10], "", digits[10:20], digits[20:]]
    assert find_canary(token, spread) == only(CanaryForm.PREFIX_STRIPPED, 0, 2, 3)


@pytest.mark.parametrize("token", TOKENS)
def test_a_full_token_is_one_match_not_also_prefix_stripped(token: str) -> None:
    """Each plain-text form of the full token is reported alone; a second, bare copy is not."""
    for fields, form, indices in [
        ([token], CanaryForm.VERBATIM, (0,)),
        ([token.upper()], CanaryForm.CASE_FOLDED, (0,)),
        ([" ".join(token)], CanaryForm.SEPARATED, (0,)),
        ([token[:20], token[20:]], CanaryForm.SPLIT_ACROSS_FIELDS, (0, 1)),
        ([CANARY_PREFIX, hex_part(token)], CanaryForm.SPLIT_ACROSS_FIELDS, (0, 1)),
    ]:
        assert find_canary(token, fields) == only(form, *indices)
    both = [f"{token} and again {hex_part(token)}"]
    assert find_canary(token, both) == [
        CanaryMatch(CanaryForm.VERBATIM, (0,)),
        CanaryMatch(CanaryForm.PREFIX_STRIPPED, (0,)),
    ]


@pytest.mark.parametrize("token", TOKENS)
def test_near_misses_of_the_hex_part_are_not_found(token: str) -> None:
    """31 of the 32 hex characters, or all 32 with one digit changed, are not matches."""
    digits = hex_part(token)
    near: list[str] = [digits[:31], digits[1:], digits[:16] + digits[17:]]
    for position in range(32):
        for replacement in "0123456789abcdef":
            if replacement != digits[position]:
                near.append(digits[:position] + replacement + digits[position + 1 :])
    for candidate in near:
        for fields in (
            [f"id {candidate} end"],
            [candidate.upper()],
            [" ".join(candidate)],
            [candidate[:10], candidate[10:]],
            [CANARY_PREFIX + candidate],
        ):
            assert find_canary(token, fields) == [], fields


# --- What must not match -----------------------------------------------------------------------


@pytest.mark.parametrize("token", TOKENS)
def test_a_different_valid_token_does_not_match_in_any_form(token: str) -> None:
    """Every form of another token, and every other derived token, is not a match."""
    others = [t for t in [*TOKENS, OTHER] if t != token]
    for other in others:
        fields = [
            other,
            other.upper(),
            " ".join(other),
            other[:20],
            other[20:],
            base64.b64encode(other.encode()).decode(),
            base64.b64encode(hex_part(other).encode()).decode(),
            other.encode().hex(),
            hex_part(other).encode().hex(),
        ]
        assert find_canary(token, fields) == []


@pytest.mark.parametrize("token", TOKENS)
def test_truncated_tokens_do_not_match(token: str) -> None:
    """No proper prefix or suffix of the hex part, with or without the prefix, matches."""
    digits = hex_part(token)
    for i in range(32):
        for truncated in (digits[:i], digits[i + 1 :]):
            for text in (CANARY_PREFIX + truncated, f"{CANARY_PREFIX}{truncated} tail"):
                assert find_canary(token, [text]) == [], text
                assert find_canary(token, [text.upper()]) == [], text
                assert find_canary(token, [base64.b64encode(text.encode()).decode()]) == []
                assert find_canary(token, [text.encode().hex()]) == []


@pytest.mark.parametrize(
    "texts",
    [
        [],
        [""],
        ["", "", ""],
        ["canary"],
        ["CANARY canary Canary"],
        [CANARY_PREFIX],
        ["PROBO-CANARY"],
        [CANARY_PREFIX * 50],
        ["probo canary " * 100],
        [CANARY_PREFIX, ""],
    ],
)
def test_prefix_words_and_empty_messages_do_not_match(texts: list[str]) -> None:
    """The word canary, the prefix alone, and empty messages are not matches."""
    for token in TOKENS:
        assert find_canary(token, texts) == []


def test_unrelated_hex_and_base64_text_does_not_match() -> None:
    """Long runs of unrelated hex and base64, in both alphabets, are not matches."""
    data = filler(20_000)
    fields = [
        data.hex(),
        data.hex().upper(),
        base64.b64encode(data).decode(),
        base64.urlsafe_b64encode(data).decode(),
        base64.encodebytes(data).decode(),
        hashlib.sha256(b"x").hexdigest() * 100,
    ]
    for token in TOKENS:
        assert find_canary(token, fields) == []


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize("position", [0, 1, 30, 31])
def test_a_token_differing_in_one_hex_digit_does_not_match_in_any_form(
    token: str, position: int
) -> None:
    """Changing any one edge digit, even to one sharing its high bits, defeats every form.

    Base64 packs the first and last digits into characters shared with the neighbouring bytes,
    so this pins that the bits of those shared characters are checked too.
    """
    digits = hex_part(token)
    for replacement in "0123456789abcdef":
        if replacement == digits[position]:
            continue
        near = CANARY_PREFIX + digits[:position] + replacement + digits[position + 1 :]
        fields = [near, near.upper(), " ".join(near), near.encode().hex()]
        for data in (near.encode(), hex_part(near).encode()):
            for before in range(3):
                fields.extend(b64_variants(EDGE_BYTES[:before] + data + EDGE_BYTES[:2]))
                fields.extend(b64_variants(EDGE_BYTES[:before] + data))
        for field in fields:
            assert find_canary(token, [field]) == [], field


LIMITS: dict[str, Callable[[str], list[str]]] = {
    "rot13": lambda t: [codecs.encode(t, "rot13")],
    "reversed": lambda t: [t[::-1]],
    "0x-prefixed hex": lambda t: [" ".join(f"0x{b:02x}" for b in t.encode())],
    "backslash-x hex": lambda t: ["".join(f"\\x{b:02x}" for b in t.encode())],
    "base64 of base64": lambda t: [base64.b64encode(base64.b64encode(t.encode())).decode()],
    "base64 of upper-cased token": lambda t: [base64.b64encode(t.upper().encode()).decode()],
    "base32": lambda t: [base64.b32encode(t.encode()).decode()],
    "html entities": lambda t: ["".join(f"&#{b};" for b in t.encode())],
    "letters between hex digits": lambda t: [CANARY_PREFIX + "z".join(hex_part(t))],
    "full-width digits": lambda t: [t.translate({ord(d): 0xFF10 + int(d) for d in "0123456789"})],
    "words between split parts": lambda t: [t[:20] + " and", t[20:]],
    "non-consecutive fields": lambda t: [t[:20], "middle words", t[20:]],
    "hex split by words": lambda t: [hex_part(t)[:16] + " and", hex_part(t)[16:]],
    "hex in non-consecutive fields": lambda t: [hex_part(t)[:16], "x", hex_part(t)[16:]],
}


@pytest.mark.parametrize("name", sorted(LIMITS))
def test_documented_limits_are_not_detected(name: str) -> None:
    """Each form the module docstring lists as undetected is indeed not detected.

    If one of these starts matching, update the module docstring with it.
    """
    for token in TOKENS:
        fields = LIMITS[name](token)
        assert token not in "".join(fields)
        assert find_canary(token, fields) == [], fields


def test_standard_url_encoding_leaves_the_token_detectable() -> None:
    """URL encoders leave the token's characters unescaped, so it is still found verbatim."""
    for token in TOKENS:
        url = "https://example.test/?q=" + urllib.parse.quote(token)
        assert find_canary(token, [url]) == only(CanaryForm.VERBATIM, 0)
        every_byte = "".join(f"%{b:02X}" for b in token.encode())
        assert find_canary(token, [url, every_byte]) == [
            CanaryMatch(CanaryForm.VERBATIM, (0,)),
            CanaryMatch(CanaryForm.HEX, (1,)),
        ]


# --- Arguments and performance -----------------------------------------------------------------


@pytest.mark.parametrize(
    "canary",
    [
        "",
        "canary",
        CANARY_PREFIX,
        TOKENS[0].upper(),
        TOKENS[0][:-1],
        TOKENS[0] + "0",
        f" {TOKENS[0]}",
        f"{TOKENS[0]}\n",
        hex_part(TOKENS[0]),
    ],
)
def test_a_malformed_canary_argument_is_refused(canary: str) -> None:
    """Only a token in the exact format can be searched for."""
    with pytest.raises(ValueError, match="not a canary token"):
        find_canary(canary, [TOKENS[0]])


def test_a_bare_string_instead_of_fields_is_refused() -> None:
    """Passing one str, which is itself a sequence of characters, is a TypeError."""
    with pytest.raises(TypeError, match="sequence of fields"):
        find_canary(TOKENS[0], TOKENS[0])


MEGABYTE = 1_000_000


@pytest.mark.parametrize(
    "chunk",
    [
        "lorem ipsum dolor sit amet ",
        CANARY_PREFIX + "0123456789abcdef0123456789abcde ",
        "a-" * 10,
        "Ab+/" * 10,
        "-" * 10,
    ],
)
def test_one_megabyte_text_is_searched_quickly(chunk: str) -> None:
    """A 1 MB field of prose, near-miss tokens, hex, base64 or separators takes well under 1 s."""
    for token in TOKENS[:2]:
        body = chunk * (MEGABYTE // len(chunk))
        started = time.perf_counter()
        assert find_canary(token, ["subject", body]) == []
        found = find_canary(token, ["subject", body + token, body])
        elapsed = time.perf_counter() - started
        assert found == only(CanaryForm.VERBATIM, 1)
        assert elapsed < 1.0, elapsed


# --- Review follow-ups -------------------------------------------------------------------------


def printable(chunk: bytes) -> str:
    """The character column of a hex dump."""
    return "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)


def hexdump_c(data: bytes) -> str:
    """``hexdump -C`` layout: offset, two groups of eight bytes, character column."""
    lines: list[str] = []
    for offset in range(0, len(data), 16):
        chunk = data[offset : offset + 16]
        left = " ".join(f"{b:02x}" for b in chunk[:8])
        right = " ".join(f"{b:02x}" for b in chunk[8:])
        lines.append(f"{offset:08x}  {left:<23}  {right:<23}  |{printable(chunk)}|")
    return "\n".join(lines)


def xxd(data: bytes) -> str:
    """Default ``xxd`` layout: offset, two-byte groups, character column."""
    lines: list[str] = []
    for offset in range(0, len(data), 16):
        chunk = data[offset : offset + 16]
        groups = " ".join(chunk[i : i + 2].hex() for i in range(0, len(chunk), 2))
        lines.append(f"{offset:08x}: {groups:<39}  {printable(chunk)}")
    return "\n".join(lines)


def xxd_plain(data: bytes) -> str:
    """``xxd -p`` layout: plain hex, 30 bytes per line."""
    digits = data.hex()
    return "\n".join(digits[i : i + 60] for i in range(0, len(digits), 60))


@pytest.mark.parametrize("token", TOKENS)
def test_hex_dumps_with_offsets_are_not_detected_but_plain_hex_is(token: str) -> None:
    """Offset and character columns break the hex run; ``xxd -p`` output is still hex."""
    for before in range(17):
        data = b"r" * before + token.encode() + b" end of record"
        assert find_canary(token, [hexdump_c(data)]) == [], before
        assert find_canary(token, [xxd(data)]) == [], before
        assert find_canary(token, [xxd_plain(data)]) == only(CanaryForm.HEX, 0), before


@pytest.mark.parametrize("token", TOKENS)
def test_encoded_token_changed_only_in_its_prefix_is_still_found(token: str) -> None:
    """Base64 or hex of a token whose prefix alone changed matches via the encoded hex part."""
    digits = hex_part(token)
    for variant in ("probo-canary-" + digits, "PROBO CANARY " + digits, "P R O B O" + digits):
        data = variant.encode()
        assert find_canary(token, [base64.b64encode(data).decode()]) == only(CanaryForm.BASE64, 0)
        assert find_canary(token, [data.hex()]) == only(CanaryForm.HEX, 0)


@pytest.mark.parametrize("token", TOKENS)
def test_encoded_token_changed_inside_its_hex_part_is_not_found(token: str) -> None:
    """Base64 or hex of a token whose hex characters changed case or gained separators fails."""
    digits = hex_part(token)
    for changed in (digits.upper(), " ".join(digits), digits[:16] + "-" + digits[16:]):
        for prefix in (CANARY_PREFIX, ""):
            data = (prefix + changed).encode()
            assert find_canary(token, [base64.b64encode(data).decode()]) == [], changed
            assert find_canary(token, [data.hex()]) == [], changed


@pytest.mark.parametrize("token", TOKENS)
def test_encoded_token_split_in_its_prefix_region_is_one_match(token: str) -> None:
    """A full-token encoding split across fields is not reported again for its hex part."""
    digits = token.encode().hex()
    assert find_canary(token, ["x " + digits[:10], digits[10:]]) == only(CanaryForm.HEX, 0, 1)
    encoded = base64.b64encode(token.encode()).decode()
    assert find_canary(token, ["x " + encoded[:8], encoded[8:]]) == only(CanaryForm.BASE64, 0, 1)


def flip(data: bytes, index: int, bit: int) -> bytes:
    """``data`` with one bit flipped."""
    return data[:index] + bytes([data[index] ^ (1 << bit)]) + data[index + 1 :]


@pytest.mark.parametrize("token", TOKENS[:4])
@pytest.mark.parametrize("before", [0, 1, 2])
@pytest.mark.parametrize("after", [0, 1, 2])
def test_every_bit_of_the_encoded_hex_part_is_checked(token: str, before: int, after: int) -> None:
    """Flipping any bit of the hex part's bytes defeats the base64 and hex matches.

    Flipping a bit of the prefix's bytes leaves the encoded hex part, which still matches once;
    flipping a bit of a neighbouring byte never prevents the match.
    """
    head, tail = EDGE_BYTES[:before], EDGE_BYTES[-after:] if after else b""
    payload = head + token.encode() + tail
    hex_start = len(head) + len(CANARY_PREFIX)
    hex_end = hex_start + 32
    for index in range(len(payload)):
        for bit in range(8):
            flipped = flip(payload, index, bit)
            for form, text in (
                (CanaryForm.BASE64, base64.b64encode(flipped).decode()),
                (CanaryForm.BASE64, base64.urlsafe_b64encode(flipped).decode().rstrip("=")),
                (CanaryForm.HEX, flipped.hex()),
            ):
                expected = [] if hex_start <= index < hex_end else only(form, 0)
                assert find_canary(token, [text]) == expected, (index, bit, form)
