from pathlib import Path

from framework.regression import evaluate
from framework.report import write_report
from framework.result import Result
from framework.testcase import TestCase

ROOT = Path(__file__).resolve().parents[1]


def test_report_is_written(tmp_path):
    tc = TestCase.from_yaml(ROOT / "testcases" / "TC01_speed_step.yaml")
    base = Result.from_mf4(ROOT / "baselines" / "v1.0" / "TC01_speed_step.mf4")
    out = write_report([(tc, evaluate(tc, base, base), base, base)], tmp_path / "r.html", "demo")
    text = out.read_text(encoding="utf-8")
    assert "TC01_speed_step" in text and "data:image/png;base64" in text