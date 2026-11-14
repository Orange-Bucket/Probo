# SPDX-License-Identifier: Apache-2.0
"""The `probo` command line: `probo report LOG [--format markdown|json] [--output FILE]`."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from inspect_ai.log import read_eval_log

from probo.report import render_markdown, summarise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="probo", description="Probo evaluation tools.")
    commands = parser.add_subparsers(dest="command", required=True)
    report = commands.add_parser("report", help="Summarise a finished helpdesk_exfil log.")
    report.add_argument("log", metavar="LOG", help="Inspect log file (.eval or .json).")
    report.add_argument(
        "--format", choices=("markdown", "json"), default="markdown", help="Output format."
    )
    report.add_argument("--output", metavar="FILE", help="Write to FILE instead of stdout.")
    return parser


def _error(message: str) -> int:
    print(f"probo: error: {' '.join(message.split())}", file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line with `argv` (default `sys.argv[1:]`); returns the exit status.

    Exits 1 with a one-line error on stderr when the log is missing or cannot be read or
    summarised; argparse exits 2 for invalid arguments.
    """
    args = _parser().parse_args(argv)
    path = Path(args.log)
    if not path.is_file():
        return _error(f"log not found: {path}")
    try:
        log = read_eval_log(str(path))
    except Exception as ex:
        return _error(f"cannot read log {path}: {type(ex).__name__}: {ex}")
    try:
        summary = summarise(log)
    except ValueError as ex:
        return _error(f"cannot summarise log {path}: {ex}")
    text = render_markdown(summary) if args.format == "markdown" else summary.model_dump_json()
    if args.output is None:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
        return 0
    try:
        Path(args.output).write_text(text, encoding="utf-8")
    except OSError as ex:
        return _error(f"cannot write {args.output}: {ex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
