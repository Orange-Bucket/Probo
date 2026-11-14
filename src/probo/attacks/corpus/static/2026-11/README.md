# static corpus, version 2026-11

This directory is one dated version of the `static` template family. `probo.attacks.load_corpus`
reads every file in it whose name ends in `.toml`, one template per file, and ignores every other
file, including this README. A result that used this corpus records the version (`2026-11`) and
`Corpus.content_hash`, which pins the exact content of every template.

## File format

Each file is UTF-8 TOML without a byte order mark (a file that starts with one is rejected),
with exactly these six keys, all required:

| Key          | Type       | Rule                                                              |
|--------------|------------|-------------------------------------------------------------------|
| `id`         | string     | Lowercase letters and digits joined by single hyphens; must equal the file name without `.toml` |
| `family`     | string     | Must be `static`, the name of the family directory               |
| `technique`  | string     | One-line description of what the text does; not blank; no line break of any kind (including U+2028, U+0085, vertical tab and form feed) |
| `provenance` | string     | Where the text came from; not blank                               |
| `date`       | local date | A bare TOML date such as `2026-11-01`, not a quoted string or a datetime |
| `text`       | string     | The template text; not blank; no `\r` escapes (CRLF file line endings are fine, TOML reads them as LF) |

Any other key is an error. Example, saved as `reference-note.toml`:

```toml
id = "reference-note"
family = "static"
technique = "Adds a neutral reference line to a ticket body"
provenance = "hand-written for Probo"
date = 2026-11-01
text = "Please also note reference {reference_code} when replying to {customer_name}."
```

## Placeholders

- `{name}` is a placeholder, where `name` matches `[a-z_][a-z0-9_]*`. The example above has the
  placeholders `customer_name` and `reference_code`.
- `{{` and `}}` are literal `{` and `}`.
- Every other use of a brace is rejected when the corpus loads: `{}`, `{0}`, `{a.b}`, `{a[0]}`,
  `{a:>10}`, `{a!r}`, `{Name}`, and any `{` or `}` without a partner.

`Template.render` needs a value for every placeholder and rejects values the template does not
use. Values are inserted exactly as given and never parsed again.

## Changing the corpus

Do not edit a published version. Add a new dated directory (`YYYY-MM`) instead, so that a result
which names a version keeps meaning the same text.
