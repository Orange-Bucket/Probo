# probo

Probo is an evaluation harness for AI agent safety, built as a Python extension package on
[Inspect](https://inspect.aisi.org.uk/) (`inspect-ai`). It runs an agent against a small,
deliberately vulnerable application, places attacker-written text in the data the agent reads,
and counts an attack as successful only when a deterministic check observes its side effect.

Installing the package registers the Inspect task `probo/helpdesk_exfil` and the `probo`
command line tool.

## Install

Probo requires Python 3.11 or newer. From a checkout of the repository, at its root:

```bash
uv sync
```

This installs the package and the development tools into `.venv`. To build a wheel and an
sdist instead:

```bash
uv build --package probo
```

The `ollama` extra adds the OpenAI client that Inspect needs to talk to an Ollama server.

## Documentation

The method, usage, reports and published findings are described in the
[repository README](https://github.com/Orange-Bucket/Probo).

## License

Apache License 2.0. See LICENSE and NOTICE.
