from pathlib import Path

from framework.regression import evaluate
from framework.result import Result
from framework.testcase import TestCase

ROOT = Path(__file__).resolve().parents[1]


def test_baseline_passes_against_itself():
    for p in sorted((ROOT / "testcases").glob("*.yaml")):
        tc = TestCase.from_yaml(p)
        base = Result.from_mf4(ROOT / "baselines" / "v1.0" / f"{tc.name}.mf4")
        rep = evaluate(tc, base, base)
        assert rep.passed, [c for c in rep.checks if not c.passed]


def test_deviation_is_detected():
    tc = TestCase.from_yaml(ROOT / "testcases" / "TC01_speed_step.yaml")
    base = Result.from_mf4(ROOT / "baselines" / "v1.0" / "TC01_speed_step.mf4")
    shifted = Result(base.test_name, "x", "x", {**base.signals, "wm": base["wm"] + 1.0})
    rep = evaluate(tc, shifted, base)
    assert not rep.passed
    assert any(c.name == "wm max_dev" and not c.passed for c in rep.checks)