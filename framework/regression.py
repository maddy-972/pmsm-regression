"""Regression engine: requirement checks + comparison against a golden baseline."""
import math
from dataclasses import dataclass, field

import numpy as np

from . import metrics
from .result import UNITS, Result
from .testcase import TestCase


@dataclass
class CheckResult:
    kind: str          # "REQ" = requirement, "BASE" = baseline comparison
    name: str
    value: float
    limit: float
    unit: str
    passed: bool


@dataclass
class TestReport:
    __test__ = False
    test_name: str
    version: str
    baseline_version: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)


def _ok(value: float, limit: float) -> bool:
    return (not math.isnan(value)) and value <= limit


def _requirement_value(c: dict, r: Result) -> float:
    t, y = r.t, r[c["signal"]]
    t0, t1 = c.get("t_start", 0.0), c.get("t_end")
    m = c["metric"]
    if m == "overshoot":
        return metrics.overshoot_pct(t, y, c["target"], t0, t1)
    if m == "settling_time":
        return metrics.settling_time(t, y, c["target"], t0, c.get("band", 0.02), t1, c.get("tol"))
    if m == "max_dip":
        return metrics.max_dip(t, y, c["target"], t0, t1)
    if m == "max":
        w = (t >= t0) & (t <= (t[-1] if t1 is None else t1))
        return float(np.max(y[w]))
    raise ValueError(f"Unknown metric {m!r}")


def evaluate(tc: TestCase, run: Result, baseline: Result | None = None) -> TestReport:
    rep = TestReport(tc.name, run.version, baseline.version if baseline else "-")

    for c in tc.checks.get("requirements", []):
        v = _requirement_value(c, run)
        rep.checks.append(CheckResult("REQ", c["name"], v, c["max"], c.get("unit", ""), _ok(v, c["max"])))

    if baseline is not None:
        for c in tc.checks.get("baseline", []):
            s, unit = c["signal"], UNITS.get(c["signal"], "")
            if len(run[s]) != len(baseline[s]):
                rep.checks.append(CheckResult("BASE", f"{s} length", len(run[s]), len(baseline[s]), "samples", False))
                continue
            dev = metrics.max_abs_dev(run[s], baseline[s])
            rms = metrics.rms_error(run[s], baseline[s])
            rep.checks.append(CheckResult("BASE", f"{s} max_dev", dev, c["max_dev"], unit, _ok(dev, c["max_dev"])))
            rep.checks.append(CheckResult("BASE", f"{s} rms", rms, c["rms"], unit, _ok(rms, c["rms"])))
    return rep