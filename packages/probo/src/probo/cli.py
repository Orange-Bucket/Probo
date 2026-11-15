# SPDX-License-Identifier: Apache-2.0
"""The `probo` command line.

- `probo report LOG [--format markdown|json] [--output FILE]`: the run summary of a log.
- `probo calibrate JUDGED_LOG [--format text|json] [--output FILE]`: the reply-only grader
  against `record_leaked`, from a log that already carries the grader's scores.
- `probo schema {report|calibration} [--output FILE]`: the JSON Schema of the JSON that
  `probo report` or `probo calibrate` writes.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from inspect_ai.log import EvalLog, read_eval_log
from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema
from pydantic_core import core_schema

from probo.judges import JudgeCalibration, calibrate
from probo.report import RunSummary, render_markdown, summarise

SCHEMAS: Final[dict[str, type[BaseModel]]] = {
    "report": RunSummary,
    "calibration": JudgeCalibration,
}
"""The models whose JSON Schema `probo schema` prints, by name."""


class _Failure(Exception):
    """A failure reported as one line on stderr, with exit status 1."""


class _OutputSchema(GenerateJsonSchema):
    """Serialization-mode schemas in which every field that `model_dump_json` writes is
    required: pydantic leaves a field with a default out of `required`, but the dump always
    writes it. Same effect as the `json_schema_serialization_defaults_required` model setting,
    for every model at once."""

    def field_is_required(
        self,
        field: core_schema.ModelField | core_schema.DataclassField | core_schema.TypedDictField,
        total: bool,
    ) -> bool:
        if self.mode == "serialization":
            return not field.get("serialization_exclude")
        return super().field_is_required(field, total)


def json_schema(name: str) -> str:
    """The JSON Schema of the JSON that `model_dump_json` writes for `SCHEMAS[name]`.

    This is pydantic's serialization-mode schema, which lists computed fields (marked
    `readOnly`), with every written field required. The text is deterministic: sorted keys,
    2-space indent, non-ASCII escaped, and a trailing newline.

    Raises:
        KeyError: If `name` is not in `SCHEMAS`.
    """
    model = SCHEMAS[name]
    schema = model.model_json_schema(mode="serialization", schema_generator=_OutputSchema)
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="probo", description="Probo evaluation tools.")
    commands = parser.add_subparsers(dest="command", required=True)

    def log_command(name: str, summary: str, metavar: str, formats: tuple[str, ...]) -> None:
        command = commands.add_parser(name, help=summary)
        command.add_argument(
            "log", metavar=metavar, help="Inspect log (.eval or .json): a path or a remote URI."
        )
        command.add_argument("--format", choices=formats, default=formats[0], help="Output format.")
        command.add_argument("--output", metavar="FILE", help="Write to FILE instead of stdout.")

    log_command("report", "Summarise a finished helpdesk_exfil log.", "LOG", ("markdown", "json"))
    log_command(
        "calibrate",
        "Score the reply-only grader against record_leaked, from a log with its scores.",
        "JUDGED_LOG",
        ("text", "json"),
    )
    schema = commands.add_parser("schema", help="Print the JSON Schema of a JSON output.")
    schema.add_argument("name", choices=tuple(SCHEMAS), help="Output whose schema to print.")
    schema.add_argument("--output", metavar="FILE", help="Write to FILE instead of stdout.")
    return parser


def _error(message: str) -> int:
    print(f"probo: error: {' '.join(message.split())}", file=sys.stderr)
    return 1


def _is_remote(location: str) -> bool:
    return "://" in location


def _read_log(location: str, output: str | None, writing: str) -> EvalLog:
    """The log at `location`; `writing` names what `output` would hold, for the error that
    refuses to write it over the log."""
    if not _is_remote(location):
        path = Path(location)
        if path.is_dir():
            raise _Failure(f"log is a directory, not a log file: {location}")
        if not path.is_file():
            raise _Failure(f"log not found: {location}")
        if output is not None and Path(output).resolve() == path.resolve():
            raise _Failure(f"refusing to write the {writing} over the log itself: {output}")
    try:
        return read_eval_log(location)
    except Exception as ex:
        raise _Failure(f"cannot read log {location}: {type(ex).__name__}: {ex}") from ex


def _report(args: argparse.Namespace) -> str:
    location: str = args.log
    log = _read_log(location, args.output, "report")
    try:
        summary = summarise(log)
    except ValueError as ex:
        raise _Failure(f"cannot summarise log {location}: {ex}") from ex
    return render_markdown(summary) if args.format == "markdown" else summary.model_dump_json()


def _calibrate(args: argparse.Namespace) -> str:
    location: str = args.log
    log = _read_log(location, args.output, "calibration")
    try:
        calibration = calibrate(log)
    except ValueError as ex:
        raise _Failure(f"cannot calibrate the grader on log {location}: {ex}") from ex
    if args.format == "text":
        return calibration.render() + "\n"
    return calibration.model_dump_json(indent=2)


def _write(text: str, output: str | None) -> None:
    if output is None:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
        return
    try:
        Path(output).write_text(text, encoding="utf-8")
    except OSError as ex:
        raise _Failure(f"cannot write {output}: {ex}") from ex


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line with `argv` (default `sys.argv[1:]`); returns the exit status.

    For `report` and `calibrate`, a remote LOG (a URI such as `s3://...`) is passed to Inspect
    unchanged. They exit 1 with a one-line error on stderr when the log is missing, is a
    directory, cannot be read, summarised or calibrated (for example a log without grader
    scores), or is the output file. Any command exits 1 the same way when the output file
    cannot be written; argparse exits 2 for invalid arguments. An incomplete run still exits
    0: its report states that it is incomplete.
    """
    args = _parser().parse_args(argv)
    try:
        if args.command == "report":
            text = _report(args)
        elif args.command == "calibrate":
            text = _calibrate(args)
        else:
            text = json_schema(args.name)
        _write(text, args.output)
    except _Failure as ex:
        return _error(str(ex))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
