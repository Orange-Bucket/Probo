# Security policy

## Supported versions

Only the latest release receives security fixes. The first release is 0.1.0.

| Version | Supported |
| ------- | --------- |
| Latest release | Yes |
| Older releases | No |
| Unreleased `main` | Fixes land here first |

## Reporting a vulnerability

Report vulnerabilities privately through GitHub private vulnerability reporting:

https://github.com/Orange-Bucket/Probo/security/advisories/new

Do not report a vulnerability in a public issue, pull request, discussion or any other public
channel. If you are unsure whether something is a security issue, report it privately anyway.

Please include:

- the Probo commit or version, Python version, operating system, and Docker version if relevant;
- what an attacker can do and under what conditions (for example, what range content or
  configuration they need to control);
- steps to reproduce, ideally a minimal scenario, fixture or command;
- what you expected to happen and what happened;
- any suggested fix or mitigation.

Do not include real credentials, personal data, or data taken from a system you were not
authorised to test.

## What to expect

- The maintainer aims to acknowledge a report within 7 days.
- After triage you will be told whether the report is accepted as a vulnerability, and kept
  informed while a fix is prepared.
- Disclosure is coordinated: the fix and a GitHub security advisory are published together, and
  you are credited in the advisory unless you ask not to be. Please do not disclose the issue
  publicly until the advisory is published or a disclosure date has been agreed.

Probo is a small project, so these are targets, not guarantees.

## Scope

Probo contains deliberately vulnerable scenario applications (one in 0.1.0, `helpdesk-exfil`; see
the [README](README.md#how-a-trial-is-judged)). Their intended flaws, such as an agent that can be
made to e-mail a record out, are vulnerable by design and are not security issues. Reports that a bundled
scenario can be attacked in the way it was built to be attacked are out of scope.

In scope is anything in Probo itself that lets range content, scenario code, a model's output or
an MCP server:

- affect the operator's machine outside the sandbox, or escape the sandbox;
- read or leak the operator's credentials, such as model provider API keys;
- reach hosts outside the declared scope;
- tamper with checks, results or logs so that a run reports something other than what happened;
- run script, load remote content or otherwise act in the browser of someone viewing the findings
  dashboard, which renders text taken from logs.

Vulnerabilities in Inspect, the MCP SDK, Docker or other dependencies should be reported to those
projects. If Probo uses a dependency in a way that makes such a vulnerability exploitable, report
that here as well.
