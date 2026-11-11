from pathlib import Path

import numpy as np

from framework.result import UNITS, Result
from framework.runner import Mf4ReplayRunner
from framework.testcase import TestCase

ROOT = Path(__file__).resolve().parents[1]


def test_mf4_roundtrip(tmp_path):
    t = np.linspace(0, 1, 101)
    signals = {"t": t, **{k: np.sin(t) * i for i, k in enumerate(UNITS, start=1)}}
    r = Result(test_name="TC_dummy", version="9.9", param_file="params_x", signals=signals)

    r2 = Result.from_mf4(r.to_mf4(tmp_path / "dummy.mf4"))

    assert r2.test_name == "TC_dummy" and r2.version == "9.9"
    np.testing.assert_allclose(r2.t, t)
    for k in UNITS:
        np.testing.assert_allclose(r2[k], signals[k])


def test_replay_baselines():
    runner = Mf4ReplayRunner(ROOT / "baselines" / "v1.0")
    for p in sorted((ROOT / "testcases").glob("*.yaml")):
        tc = TestCase.from_yaml(p)
        r = runner.run(tc)
        assert r.version == "1.0"
        assert abs(r["wm"][-1] - 50) < 0.5      # every case ends at 50 rad/s