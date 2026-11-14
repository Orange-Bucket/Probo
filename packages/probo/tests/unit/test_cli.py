# SPDX-License-Identifier: Apache-2.0
"""`probo report` and `probo schema`: formats, stdout and `--output`, and one-line errors.

The log checks are shared with `probo calibrate`, whose other tests are in
`judges/test_calibrate_command.py`.
"""

import json
from pathlib import Path

import pytest
from inspect_ai.log import EvalLog
from jsonschema import Draft202012Validator, validate

from probo.cli import SCHEMAS, json_schema, main
from probo.report import EVIDENCE_SENTENCE, RunSummary, render_markdown, summarise

from .outcomes.outcome_support import corpus_args, leak, other_task, run_plan
from .scenarios.helpdesk_support import run


@pytest.fixture(scope="module")
def log(tmp_path_factory: pytest.TempPathFactory) -> EvalLog:
    return run_plan(tmp_path_factory.mktemp("cli"), leak)


def test_markdown_to_stdout(log: EvalLog, capsys: pytest.CaptureFixture[str]) -> None:
    """The default format is the Markdown report, on stdout."""
    assert main(["report", log.location]) == 0
    out = capsys.readouterr().out
    assert out == render_markdown(summarise(log))
    assert EVIDENCE_SENTENCE in out


def test_json_to_stdout(log: EvalLog, capsys: pytest.CaptureFixture[str]) -> None:
    """`--format json` prints the summary JSON, which loads back."""
    assert main(["report", log.location, "--format", "json"]) == 0
    loaded = RunSummary.model_validate_json(capsys.readouterr().out)
    assert loaded == summarise(log)


@pytest.mark.parametrize("fmt", ["markdown", "json"])
def test_output_file(
    log: EvalLog, tmp_path: Path, fmt: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--output` writes the report to the file and nothing to stdout."""
    target = tmp_path / "report.out"
    assert main(["report", log.location, "--format", fmt, "--output", str(target)]) == 0
    assert capsys.readouterr().out == ""
    text = target.read_text(encoding="utf-8")
    summary = summarise(log)
    if fmt == "json":
        assert RunSummary.model_validate_json(text) == summary
    else:
        assert text == render_markdown(summary)


def one_line_error(capsys: pytest.CaptureFixture[str]) -> str:
    captured = capsys.readouterr()
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("probo: error: ")
    return lines[0]


COMMANDS = pytest.mark.parametrize("command", ["report", "calibrate"])
"""The commands that read a log."""


def test_json_matches_its_schema(log: EvalLog, capsys: pytest.CaptureFixture[str]) -> None:
    """The report JSON validates against the schema `probo schema report` prints."""
    assert main(["report", log.location, "--format", "json"]) == 0
    schema = json.loads(json_schema("report"))
    validate(json.loads(capsys.readouterr().out), schema, cls=Draft202012Validator)


@COMMANDS
def test_missing_log(command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A missing log exits 1 with one line on stderr."""
    assert main([command, str(tmp_path / "nope.eval")]) == 1
    assert "log not found" in one_line_error(capsys)


@COMMANDS
def test_unreadable_log(command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A file that is not a log exits 1 with one line on stderr."""
    bad = tmp_path / "bad.eval"
    bad.write_text("not a log\nsecond line\n", encoding="utf-8")
    assert main([command, str(bad)]) == 1
    assert "cannot read log" in one_line_error(capsys)


@pytest.mark.parametrize(
    "argv",
    [
        ["report", "run.eval", "--format", "html"],
        ["report", "run.eval", "--format", "text"],
        ["calibrate", "run.eval", "--format", "markdown"],
        ["schema", "summary"],
        ["schema"],
    ],
)
def test_bad_arguments_exit_2(argv: list[str]) -> None:
    """argparse rejects an unknown format or schema name, and a missing one."""
    with pytest.raises(SystemExit) as exit_info:
        main(argv)
    assert exit_info.value.code == 2


@COMMANDS
def test_directory_is_not_a_log(
    command: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A directory exits 1 saying so."""
    assert main([command, str(tmp_path)]) == 1
    assert "is a directory" in one_line_error(capsys)


@pytest.mark.parametrize(
    ("command", "writing"), [("report", "report"), ("calibrate", "calibration")]
)
def test_output_over_the_log_is_refused(
    log: EvalLog, command: str, writing: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Writing the output over the log itself is refused, before the log is read, and the
    log is kept."""
    before = Path(log.location).read_bytes()
    assert main([command, log.location, "--output", log.location]) == 1
    assert f"refusing to write the {writing} over the log" in one_line_error(capsys)
    assert Path(log.location).read_bytes() == before


def test_remote_uri_is_passed_to_inspect(log: EvalLog, capsys: pytest.CaptureFixture[str]) -> None:
    """A URI is read by Inspect unchanged, not checked as a local path."""
    assert main(["report", Path(log.location).as_uri()]) == 0
    assert capsys.readouterr().out == render_markdown(summarise(log))


def test_log_without_samples(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A run logged without samples exits 1 with one line that a CLI user can act on."""
    empty = run(tmp_path / "logs", task_args=corpus_args(tmp_path), log_samples=False)
    assert main(["report", empty.location]) == 1
    line = one_line_error(capsys)
    assert "cannot summarise log" in line and "logged without samples" in line


def test_log_of_another_task(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Another task's log exits 1 naming the task."""
    other = run(tmp_path / "logs", task=other_task())
    assert main(["report", other.location]) == 1
    assert "'other_task', not helpdesk_exfil" in one_line_error(capsys)


def test_calibrate_log_without_judge_scores(
    log: EvalLog, capsys: pytest.CaptureFixture[str]
) -> None:
    """A log the grader never scored exits 1 with one line naming the missing scores."""
    assert main(["calibrate", log.location]) == 1
    line = one_line_error(capsys)
    assert "cannot calibrate the grader on log" in line
    assert "has no 'reply_only_judge' scores" in line


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_schema_to_stdout(name: str, capsys: pytest.CaptureFixture[str]) -> None:
    """The schema is pydantic's serialization schema as sorted, indented ASCII JSON."""
    assert main(["schema", name]) == 0
    out = capsys.readouterr().out
    assert out == json_schema(name)
    assert out.isascii() and out.endswith("}\n")
    schema = json.loads(out)
    assert out == json.dumps(schema, indent=2, sort_keys=True) + "\n"
    assert schema["title"] == SCHEMAS[name].__name__
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_schema_output_file(name: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`--output` writes the same text, trailing newline included, and nothing to stdout."""
    target = tmp_path / f"{name}.schema.json"
    assert main(["schema", name, "--output", str(target)]) == 0
    assert capsys.readouterr().out == ""
    assert target.read_bytes().decode("utf-8") == json_schema(name)


def test_schema_lists_derived_and_defaulted_fields_as_required() -> None:
    """Computed fields are in the schema (read-only) and every field the dump writes,
    defaulted ones included, is required."""
    report = json.loads(json_schema("report"))["$defs"]
    assert {"per_attempt", "per_trial"} <= set(report["AttackSuccess"]["required"])
    assert report["Proportion"]["properties"]["estimate"]["readOnly"] is True
    calibration = json.loads(json_schema("calibration"))
    assert "level" in calibration["required"]
    assert "sample_error" in calibration["$defs"]["Exclusions"]["required"]


def test_schema_unwritable_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """An output path that cannot be written exits 1 with one line on stderr."""
    assert main(["schema", "report", "--output", str(tmp_path)]) == 1
    assert "cannot write" in one_line_error(capsys)
