from pathlib import Path

from framework.testcase import TestCase

TC_DIR = Path(__file__).resolve().parents[1] / "testcases"


def test_all_testcases_load():
    cases = [TestCase.from_yaml(p) for p in TC_DIR.glob("*.yaml")]
    assert len(cases) >= 3


def test_step_profile():
    tc = TestCase.from_yaml(TC_DIR / "TC01_speed_step.yaml")
    assert tc.profiles()["w_ref_in"] == [[0, 0], [0.01, 0], [0.01, 50], [0.5, 50]]


def test_constant_profile():
    tc = TestCase.from_yaml(TC_DIR / "TC01_speed_step.yaml")
    assert tc.profiles()["TL_in"] == [[0, 0], [0.5, 0]]