# Contributing to Probo

Thank you for considering a contribution. Probo is pre-release: the repository holds the project
scaffold and contract tests, and the harness itself is still being built (see the roadmap in
[README.md](README.md#roadmap)). Before starting on anything larger than a small fix, open an
issue in the [issue tracker](https://github.com/Orange-Bucket/Probo/issues) so the approach can be
agreed first.

By taking part you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Do not report
security vulnerabilities in public issues; follow [SECURITY.md](SECURITY.md) instead. Work on
attack content must stay within [RESPONSIBLE_USE.md](RESPONSIBLE_USE.md).

## Development setup

You need [uv](https://docs.astral.sh/uv/) and Python 3.11 or newer. Docker with the Compose plugin
is needed only to run the tests marked `docker`; without it those tests are skipped.

```bash
git clone https://github.com/Orange-Bucket/Probo.git
cd Probo
uv sync
```

`uv sync` creates `.venv` and installs the locked runtime and development dependencies from
`uv.lock`. Use `uv add` and `uv remove` to change dependencies so that `pyproject.toml` and
`uv.lock` stay in step, and commit both.

The repository uses [pre-commit](https://pre-commit.com/) hooks. Install them once with:

```bash
uvx pre-commit install
```

## Checks that must pass

Every pull request must pass these locally and in CI:

```bash
uv run ruff check .          # lint
uv run ruff format --check . # formatting
uv run pyright               # type-check, strict mode
uv run pytest                # tests
uv build                     # the package builds
```

Run `uv run ruff format .` to apply formatting. Pyright runs in strict mode over `src/` and
`tests/`; do not silence an error with `# pyright: ignore` without a comment saying why.

## Tests

- Tests must not need network access or API keys. Use Inspect's `mockllm` model with scripted
  outputs instead of a real provider (see `tests/contract/fixtures/support.py`).
- Tests that need a Docker daemon are marked `docker` (`pytestmark = pytest.mark.docker` or
  `@pytest.mark.docker`). They are skipped automatically when Docker, Compose or the pinned image
  is not available. Markers are strict, so an unregistered marker is an error.
- A test that depends on a property of the host it cannot control must skip with a reason that
  names that property, not fail.
- Every source file starts with `# SPDX-License-Identifier: Apache-2.0`.

### Adding a contract test

The harness relies on specific behaviour of `inspect-ai` and the `mcp` SDK. `inspect-ai` is pinned
to an exact version, and each behaviour the harness depends on is pinned by a contract test under
`tests/contract/`, so that an upgrade which changes it fails loudly instead of silently changing
results. When new code starts relying on an Inspect or MCP SDK behaviour that no contract test
covers yet:

1. Add a test to the matching `tests/contract/test_<area>.py`, or create a new file for a new area.
   Each file opens with a docstring of the form `"""Contract: <what is pinned>."""`.
2. Assert the specific behaviour you rely on, through Inspect's public API, with the smallest task
   that shows it. Use the helpers in `tests/contract/fixtures/support.py` (`run_eval`,
   `run_docker_eval`, `mock_model`, `only_sample`) rather than calling `eval` directly.
3. Put any fixture files (Compose files, MCP servers, Dockerfiles) under
   `tests/contract/fixtures/`. Container images are pinned by digest; reuse the `IMAGE` constant
   in `support.py` rather than adding a new image.
4. Mark the test `docker` if it needs a sandbox.
5. In the pull request, say which harness code depends on the behaviour.

When upgrading `inspect-ai` or `mcp`, run the full contract suite with Docker available and treat
any failure as a behaviour change to understand before changing the test.

## Commits

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>[(scope)][!]: <description>

[body]

[footers]
```

- `type` is one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`,
  `chore`. `style` is for formatting only.
- The description is imperative, lowercase (identifiers and proper nouns keep their casing), has
  no trailing period, and keeps the subject line under 72 characters.
- The body says what changed and why.
- Mark a breaking change with `!` after the type or scope, or a `BREAKING CHANGE:` footer.

Example: `test(contract): pin MCP tool error propagation`

## Branches and pull requests

Use one branch and one pull request per unit of work. Do not mix unrelated changes in a pull
request.

Branch names take the form `<type>/<description>`:

- `type` is one of `feat`, `fix`, `hotfix` (urgent fix to a release), `release`, `chore`.
- `description` uses lowercase letters, digits and single hyphens only, for example
  `feat/canary-check`. Add the issue number when there is one: `fix/issue-12-epoch-reducer`.
- Dots appear only in release branches: `release/v0.1.0`.

A pull request should describe what changed and why, link the issue it addresses, and update
[CHANGELOG.md](CHANGELOG.md) under `[Unreleased]` when the change is visible to users.

## Licensing of contributions

Probo is licensed under the [Apache License 2.0](LICENSE). Contributions you submit are licensed
under the same terms, as set out in section 5 of the licence. A Developer Certificate of Origin
sign-off is not required, and there is no contributor licence agreement.

## AI assistance

Probo is developed with AI assistance. Commits that contain AI-written changes carry
`Co-Authored-By` trailers naming the models that wrote them. A human maintainer reviews every
change and is accountable for it.

If you use AI tools to contribute, do the same: credit the models in `Co-Authored-By` trailers,
review what they produced, and make sure you understand everything you submit.
