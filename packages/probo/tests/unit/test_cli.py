# SPDX-License-Identifier: Apache-2.0
"""`probo report`: both formats, stdout and `--output`, and one-line errors."""

from pathlib import Path

import pytest
from inspect_ai.log import EvalLog

from probo.cli import main
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


def test_missing_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A missing log exits 1 with one line on stderr."""
    assert main(["report", str(tmp_path / "nope.eval")]) == 1
    assert "log not found" in one_line_error(capsys)


def test_unreadable_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A file that is not a log exits 1 with one line on stderr."""
    bad = tmp_path / "bad.eval"
    bad.write_text("not a log\nsecond line\n", encoding="utf-8")
    assert main(["report", str(bad)]) == 1
    assert "cannot read log" in one_line_error(capsys)


def test_bad_arguments_exit_2(log: EvalLog) -> None:
    """argparse rejects an unknown format."""
    with pytest.raises(SystemExit) as exit_info:
        main(["report", log.location, "--format", "html"])
    assert exit_info.value.code == 2


def test_directory_is_not_a_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A directory exits 1 saying so."""
    assert main(["report", str(tmp_path)]) == 1
    assert "is a directory" in one_line_error(capsys)


def test_output_over_the_log_is_refused(log: EvalLog, capsys: pytest.CaptureFixture[str]) -> None:
    """Writing the report over the log itself is refused and the log is kept."""
    before = Path(log.location).read_bytes()
    assert main(["report", log.location, "--output", log.location]) == 1
    assert "refusing to write the report over the log" in one_line_error(capsys)
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
