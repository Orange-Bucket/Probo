# SPDX-License-Identifier: Apache-2.0
"""`probo calibrate` on a log with grader scores: both formats, stdout and `--output`.

The log checks it shares with `probo report` are tested in `test_cli.py`.
"""

import json
from pathlib import Path

import pytest
from inspect_ai.log import EvalLog
from jsonschema import Draft202012Validator, validate

from probo.cli import json_schema, main
from probo.judges import JudgeCalibration, calibrate


def test_text_to_stdout(mix_log: EvalLog, capsys: pytest.CaptureFixture[str]) -> None:
    """The default format is the rendered calibration, on stdout."""
    assert main(["calibrate", mix_log.location]) == 0
    assert capsys.readouterr().out == calibrate(mix_log).render() + "\n"


def test_json_to_stdout(mix_log: EvalLog, capsys: pytest.CaptureFixture[str]) -> None:
    """`--format json` prints the calibration as indented JSON, which loads back and
    validates against `probo schema calibration`."""
    assert main(["calibrate", mix_log.location, "--format", "json"]) == 0
    out = capsys.readouterr().out
    expected = calibrate(mix_log)
    assert out == expected.model_dump_json(indent=2) + "\n"
    assert JudgeCalibration.model_validate_json(out) == expected
    validate(json.loads(out), json.loads(json_schema("calibration")), cls=Draft202012Validator)


@pytest.mark.parametrize("fmt", ["text", "json"])
def test_output_file(
    mix_log: EvalLog, tmp_path: Path, fmt: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--output` writes the calibration to the file and nothing to stdout; the text file is
    exactly what stdout would show."""
    target = tmp_path / "calibration.out"
    assert main(["calibrate", mix_log.location, "--format", fmt, "--output", str(target)]) == 0
    assert capsys.readouterr().out == ""
    text = target.read_bytes().decode("utf-8")
    expected = calibrate(mix_log)
    if fmt == "json":
        assert text == expected.model_dump_json(indent=2)
        assert JudgeCalibration.model_validate_json(text) == expected
    else:
        assert text == expected.render() + "\n"


def test_remote_uri_is_passed_to_inspect(
    mix_log: EvalLog, capsys: pytest.CaptureFixture[str]
) -> None:
    """A URI is read by Inspect unchanged, not checked as a local path."""
    assert main(["calibrate", Path(mix_log.location).as_uri()]) == 0
    assert capsys.readouterr().out == calibrate(mix_log).render() + "\n"
