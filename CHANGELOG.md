# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Project scaffold: `uv` project with `inspect-ai` pinned to an exact version and a lockfile,
  package layout under `src/probo`, and Ruff, Pyright (strict) and pytest configuration.
- Contract tests under `tests/contract/` that pin the Inspect and MCP SDK behaviour the harness
  relies on: the mock model, epochs and reducers, Wilson confidence intervals and clustered
  standard errors, scorers reading task state, model roles, log contents, re-scoring, the Docker
  sandbox lifecycle and network isolation, and MCP tools over stdio and inside the sandbox.
- Community and policy files: README, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, RESPONSIBLE_USE,
  NOTICE and CITATION.cff.

### Changed

- Licence changed from MIT to Apache-2.0.

[Unreleased]: https://github.com/Orange-Bucket/Probo/commits/main
