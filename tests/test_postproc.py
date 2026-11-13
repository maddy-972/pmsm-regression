import numpy as np
import pandas as pd

from postproc.clean import frozen_segments, remove_spikes
from postproc.steady import steady_windows

rng = np.random.default_rng(0)


def test_spike_removed_but_step_kept():
    y = np.r_[np.zeros(500), np.full(500, 50.0)] + rng.normal(0, 0.2, 1000)
    y[200] += 40
    clean, idx = remove_spikes(y)
    assert list(idx) == [200]
    assert abs(clean[200]) < 2
    assert np.allclose(clean[600:], y[600:])          # the step itself is untouched


def test_frozen_segment_detected():
    y = rng.normal(0, 0.2, 1000)
    y[300:400] = y[300]
    assert frozen_segments(y) == [(300, 399)]


def test_steady_windows_on_staircase():
    t = np.arange(0, 6, 1e-3)
    n = np.where(t < 0.5, t * 1000, 500) + rng.normal(0, 1, t.size)
    T = np.select([t < 2, t < 4], [10, 30], 50) + rng.normal(0, 0.2, t.size)
    win = steady_windows(pd.DataFrame({"t": t, "n_rpm": n, "T_shaft": T}))
    assert len(win) == 3