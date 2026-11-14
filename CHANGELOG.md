# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A React application under `apps/dashboard`, scaffolded with the Nx React generator (placeholder
  page only).

### Changed

- The Python package moved from the repository root to `packages/probo/` and is registered as
  the Nx project `probo` with `lint`, `typecheck`, `test`, `test-docker` and `build` targets. The
  root `pyproject.toml` is now a uv workspace that holds the development tools and the Ruff,
  Pyright and pytest settings; `uv sync` and the `uv run` commands work from the root as before.
  Build the package with `uv build --package probo`. The package has its own short README, which
  becomes the long description in the wheel and sdist metadata, and the sdist no longer contains
  `uv.lock` or the pytest settings, which now live in the root `pyproject.toml`: tests run from
  an unpacked sdist do not enforce `--strict-markers` and warn about the unregistered `docker`
  marker.

## [0.1.0] - 2026-11-14

### Added

- The `helpdesk-exfil` scenario, registered with Inspect as the task `probo/helpdesk_exfil`: a
  fictional helpdesk with tickets, customer records and an outbox held in the sample store, four
  in-process tools (`list_tickets`, `read_ticket`, `get_customer`, `send_email`), two ordinary
  user tasks, and Inspect's ReAct agent running on the `target` model role. Every customer record
  holds a canary derived per sample and epoch from the run seed.
- A dataset that crosses every user task with a control sample (a harmless default ticket note)
  and one sample per selected template, with task arguments `seed`, `templates`, `watch_address`,
  `corpus_version`, `corpus_dir` and `message_limit`. Sample and task metadata record the seed,
  the template id and the corpus version and content hash.
- Canary token derivation and matching (`probo.checks.canary`): verbatim, case-changed, with
  separators inserted, without its prefix, split across consecutive fields, and base64- or
  hex-encoded. The module docstring lists what is not detected.
- Deterministic checks as Inspect scorers: `task_completed` (utility, by text matching of the
  required facts), `record_leaked` (a canary in an e-mail to anyone but its owner),
  `sent_to_watched_address` (a `send_email` call aimed at the watched address, read from the
  transcript) and `note_delivered` (the template text reached a completed model generation). The
  three leak checks return true, false or not applicable.
- A loader for dated, versioned template corpora (`probo.attacks`), one TOML file per template,
  with strict validation and a content hash; the packaged `static` corpus `2026-11` with one
  hand-written template, `plain-request`.
- Mechanical outcome labels per trial (`probo.outcomes`): `provider_error`, `grader_error`,
  `harness_error`, `not_delivered`, `attack_succeeded` and `attack_failed_target_resisted`, with
  the evidence for each label. Control trials get no attack label.
- Statistics (`probo.stats`): Wilson score intervals, rates that carry their trial count, interval
  and estimand, attack success per attempt and per trial, and a confusion matrix with precision,
  recall and base rate.
- A run summary and the `probo report LOG` command, printing Markdown or JSON: run facts, attack
  success per attempt and per trial, attempted versus completed, utility, control base rates,
  delivery, per-item results over epochs, limits, excluded trials and trials not run.
- The reply-only judge `probo/reply_only_judge`, which sees only the user's request and the
  agent's submitted answer and needs a `judge` model role, and `probo.judges.calibrate`, which
  compares it with `record_leaked` (confusion matrix, exclusions by reason, disagreeing trials).
  `add_judge_scores` appends judge scores to a stored log without running the agent again.
- An optional `ollama` extra with the `openai` client that Inspect needs to reach Ollama.
- Project scaffold: `uv` project with `inspect-ai` pinned to an exact version and a lockfile,
  package layout under `src/probo`, and Ruff, Pyright (strict) and pytest configuration.
- Contract tests under `tests/contract/` that pin the Inspect and MCP SDK behaviour the harness
  relies on: the mock model, epochs and reducers, Wilson confidence intervals and clustered
  standard errors, scorers reading task state, model roles, log contents, re-scoring, transcript
  events in scorers, submit and limits under ReAct, how model, retry, scorer and cancellation
  errors are recorded, unparseable tool arguments, the Docker sandbox lifecycle and network
  isolation, and MCP tools over stdio and inside the sandbox.
- CI (lint, formatting, type checks, tests on Python 3.11 to 3.14, build and lockfile checks),
  Dependabot, pre-commit hooks, issue forms and a pull request template.
- Community and policy files: README, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, RESPONSIBLE_USE,
  NOTICE and CITATION.cff.
- First published finding under `findings/`: a 120-trial `helpdesk-exfil` run against
  `qwen2.5:7b` with its Inspect log, report, judge calibration and manifest.

### Changed

- Licence changed from MIT to Apache-2.0.

[Unreleased]: https://github.com/Orange-Bucket/Probo/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Orange-Bucket/Probo/releases/tag/v0.1.0
