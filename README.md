# Probo

Probo is a firing range and proof harness for attacks on AI agents, built as a Python extension
package on [Inspect](https://inspect.aisi.org.uk/) (`inspect-ai`). It is planned to ship small,
deliberately vulnerable agent applications, attack them through tool results, retrieved documents
and MCP server behaviour, and count an attack as successful only when a deterministic check
observes its side effect. LLM judges are planned to run on the same trials and be scored against
those checks.

## Status: pre-release

Probo has not been released and is not usable as a tool yet. The repository contains:

- the project scaffold (package layout, `uv` project, lockfile, lint and type-check configuration);
- contract tests under [`tests/contract/`](tests/contract/) that pin the Inspect and MCP SDK
  behaviour the harness will depend on, so that an upgrade which changes that behaviour fails the
  test suite.

No scenario, attack, check, judge or result exists yet. The Method, Roadmap and Limits sections
below describe the design, not working code.

## Method

These are the design principles the harness is being built to.

- **Side effects, not opinions.** An attack counts as successful only when a deterministic check
  observes its effect: a planted per-run canary reaching a sink, a state change, a specific tool
  call, or one tenant reading another tenant's record.
- **Ground truth before attacks.** A scenario is admitted only if a scripted attack trips its
  check and a benign run passes its utility check.
- **Deterministic checks before LLM judges.** A judge never overrules a check. Judges are measured
  against the checks as precision and recall, with the base rate shown.
- **Delivery check.** A trial in which the injection never reached the agent's context is excluded,
  not counted as a defence.
- **Repeated trials.** Every rate comes from repeated trials, is reported with a Wilson interval
  and states its estimand.
- **Failure labelling.** Every failed trial is labelled as a model, harness, environment or
  provider failure before any rate is computed.
- **Evidence, not proof.** A result is evidence that a system is vulnerable. It is never proof
  that a system is robust.

## Roadmap

Planned, not promised. Scope and order may change.

- **v0.1** - one scenario, `helpdesk-exfil`: an attacker-authored support ticket makes a helpdesk
  agent e-mail a customer record out. In-process tools, canary and tool-call checks, a utility
  check, a delivery check, hand-written injection templates, epochs with Wilson intervals,
  mechanical outcome labels, and a reply-only LLM judge with a confusion matrix against the checks.
- **v0.2** - a containerised range: an internal-only network, an egress sidecar, a self-test, a
  scope file, a run manifest, cost accounting and a `check` pre-flight command.
- **v0.3** - more scenarios (a malicious MCP server that turns after N calls; a cross-tenant read
  through a real broken-object-level-authorisation flaw in a back-end API; a business-logic or
  system-prompt-leak scenario), a trace-aware judge and calibration report, the full outcome
  taxonomy, and a finding report with a replayable proof of concept.
- **Later** - record and replay, SARIF output, an adaptive attacker.

## Limits

What Probo will not show, even once the roadmap is built:

- The bundled scenarios will be few and hand-authored. They cover a small part of the ways agents
  can be attacked.
- Results on the bundled range do not transfer to other systems. A model or agent that resists an
  attack here may fail against the same attack elsewhere, and the reverse.
- A low attack success rate is not robustness. It means the attacks that were tried did not work
  in the trials that were run.
- Weak local models often fail an attack because they cannot carry out the attacker's goal at
  all, not because they resisted it. A low success rate for such a model says little about its
  security.

## Development

Requirements: [uv](https://docs.astral.sh/uv/) and Python 3.11 or newer (uv can install it).
Docker with the Compose plugin is needed only for the tests marked `docker`; they are skipped when
Docker is not available.

```bash
uv sync               # create .venv and install the locked dependencies
uv run pytest         # run the test suite
uv run ruff check .   # lint
uv run pyright        # type-check (strict)
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the checks a pull request must pass and the
conventions for commits, branches and tests.

## Responsible use

Probo is meant to be pointed only at its bundled range, or at systems you own or are authorised
in writing to test, and never at third-party hosted agents or services. Read
[RESPONSIBLE_USE.md](RESPONSIBLE_USE.md) before running it, and report security problems in
Probo itself as described in [SECURITY.md](SECURITY.md).

## Prior art

Probo builds on, or takes ideas from, the following work:

- [Inspect](https://inspect.aisi.org.uk/) (UK AI Security Institute) - the evaluation substrate:
  tasks, solvers, scorers, sandboxes and logs.
- [AgentDojo](https://agentdojo.spylab.ai/) - a utility check and a security check per task,
  injection vectors with benign defaults, and verifying ground truths before use.
- [MiDojo](https://blog.trustyai.org/blog/midojo-intro/) (TrustyAI) - marking trials in which the
  injection was not delivered to the agent as not applicable.
- [Inspect Cyber](https://inspect.cyber.aisi.org.uk/) - declarative scenario packs with
  solvability checks.
- [WASP](https://arxiv.org/abs/2504.18575) - separating attempted from completed attacks.
- ["The Attacker Moves Second"](https://arxiv.org/abs/2510.09023) - static attack sets overstate
  how well defences hold; the motivation for a later adaptive attacker.

## AI assistance

Probo is developed with AI assistance. See
[AI assistance in CONTRIBUTING.md](CONTRIBUTING.md#ai-assistance) for how that is handled.

## Licence

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Copyright 2026 Orange Bucket.
