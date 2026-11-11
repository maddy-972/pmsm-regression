import numpy as np
import pytest

from framework import metrics as m

t = np.linspace(0, 1, 100001)


def test_first_order_has_no_overshoot_and_settles_at_3_9_tau():
    tau = 0.05
    y = 1 - np.exp(-t / tau)
    assert m.overshoot_pct(t, y, 1.0, 0.0) == 0.0
    assert m.settling_time(t, y, 1.0, 0.0, band=0.02) == pytest.approx(tau * np.log(50), rel=1e-3)


def test_second_order_overshoot_matches_theory():
    zeta, wn = 0.5, 50.0
    wd = wn * np.sqrt(1 - zeta**2)
    y = 1 - np.exp(-zeta * wn * t) / np.sqrt(1 - zeta**2) * np.sin(wd * t + np.arccos(zeta))
    expected = 100 * np.exp(-np.pi * zeta / np.sqrt(1 - zeta**2))   # 16.3 %
    assert m.overshoot_pct(t, y, 1.0, 0.0) == pytest.approx(expected, rel=1e-3)


def test_baseline_comparison():
    y_ref = np.sin(t)
    assert m.max_abs_dev(y_ref, y_ref) == 0.0
    assert m.max_abs_dev(y_ref + 0.1, y_ref) == pytest.approx(0.1)
    assert m.rms_error(y_ref + 0.1, y_ref) == pytest.approx(0.1)


def test_not_settled_returns_nan():
    y = np.full_like(t, 0.5)                  # never reaches target 1.0
    assert np.isnan(m.settling_time(t, y, 1.0, 0.0))