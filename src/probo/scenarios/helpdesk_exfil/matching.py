# SPDX-License-Identifier: Apache-2.0
"""Text normalisation for matching facts in e-mail replies.

`clean` applies, in order:

1. Simple HTML tags are removed. Inline formatting tags (`a abbr b code em i mark small span
   strong sub sup u`) are deleted, so `21<sup>st</sup>` reads `21st`; any other tag (`<br>`,
   `<p>`, `<div>`, ...) becomes a line break.
2. HTML character references are unescaped (`&nbsp;`, `&#8209;`, `&amp;`).
3. Unicode hyphens and dashes (U+2010 to U+2015, U+2212, U+FE58, U+FE63, U+FF0D) become `-`;
   no-break and narrow spaces (U+00A0, U+2007, U+202F) become a space; the soft hyphen
   (U+00AD) and zero-width characters (U+200B to U+200D, U+2060, U+FEFF) are deleted, since
   they are invisible when the text is shown.
4. Markdown backslash escapes before ASCII punctuation are dropped (`EG\\-40213`).
5. The text is case-folded.

`normalise` also collapses every whitespace run to one space. `sentences` splits cleaned
text at line breaks and after `.`, `!`, `?` or `;` followed by whitespace.
"""

import html
import re
import string

_INLINE_TAGS = "a|abbr|b|code|em|i|mark|small|span|strong|sub|sup|u"
_INLINE_TAG = re.compile(rf"</?(?:{_INLINE_TAGS})(?:\s[^<>]*)?/?>", re.IGNORECASE)
_OTHER_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?/?>")
_MARKDOWN_ESCAPE = re.compile(rf"\\([{re.escape(string.punctuation)}])")
_SENTENCE_BREAK = re.compile(r"\n|(?<=[.!?;])\s+")

_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63\uff0d"
_SPACES = "\u00a0\u2007\u202f"
_INVISIBLE = "\u00ad\u200b\u200c\u200d\u2060\ufeff"
_TRANSLATION = str.maketrans(
    {**dict.fromkeys(_DASHES, "-"), **dict.fromkeys(_SPACES, " "), **dict.fromkeys(_INVISIBLE)}
)


def clean(text: str) -> str:
    """Apply steps 1 to 5 of the module docstring; line breaks are kept."""
    text = _INLINE_TAG.sub("", text)
    text = _OTHER_TAG.sub("\n", text)
    text = html.unescape(text).translate(_TRANSLATION)
    text = _MARKDOWN_ESCAPE.sub(r"\1", text)
    return text.casefold()


def collapse(text: str) -> str:
    """Collapse every whitespace run to a single space and strip the ends."""
    return " ".join(text.split())


def normalise(text: str) -> str:
    """`clean` the text and collapse its whitespace."""
    return collapse(clean(text))


def sentences(text: str) -> list[str]:
    """The non-empty sentences of `clean(text)`, each with its whitespace collapsed."""
    parts = (collapse(part) for part in _SENTENCE_BREAK.split(clean(text)))
    return [part for part in parts if part]
