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
    report.add_argument(
        "log", metavar="LOG", help="Inspect log (.eval or .json): a path or a remote URI."
    )
    report.add_argument(
        "--format", choices=("markdown", "json"), default="markdown", help="Output format."
    )
    report.add_argument("--output", metavar="FILE", help="Write to FILE instead of stdout.")
    return parser


def _error(message: str) -> int:
    print(f"probo: error: {' '.join(message.split())}", file=sys.stderr)
    return 1


def _is_remote(location: str) -> bool:
    return "://" in location


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line with `argv` (default `sys.argv[1:]`); returns the exit status.

    A remote LOG (a URI such as `s3://...`) is passed to Inspect unchanged. Exits 1 with a
    one-line error on stderr when the log is missing, is a directory, cannot be read or
    summarised, or is the output file; argparse exits 2 for invalid arguments. An incomplete
    run still exits 0: its report states that it is incomplete.
    """
    args = _parser().parse_args(argv)
    location: str = args.log
    output: str | None = args.output
    if not _is_remote(location):
        path = Path(location)
        if path.is_dir():
            return _error(f"log is a directory, not a log file: {location}")
        if not path.is_file():
            return _error(f"log not found: {location}")
        if output is not None and Path(output).resolve() == path.resolve():
            return _error(f"refusing to write the report over the log itself: {output}")
    try:
        log = read_eval_log(location)
    except Exception as ex:
        return _error(f"cannot read log {location}: {type(ex).__name__}: {ex}")
    try:
        summary = summarise(log)
    except ValueError as ex:
        return _error(f"cannot summarise log {location}: {ex}")
    text = render_markdown(summary) if args.format == "markdown" else summary.model_dump_json()
    if output is None:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
        return 0
    try:
        Path(output).write_text(text, encoding="utf-8")
    except OSError as ex:
        return _error(f"cannot write {output}: {ex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
