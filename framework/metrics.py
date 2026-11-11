"""Signal metrics for regression checks. Pure NumPy, no MATLAB."""
import numpy as np


def _window(t, t_start, t_end):
    t_end = t[-1] if t_end is None else t_end
    return (t >= t_start) & (t <= t_end)


def max_abs_dev(y, y_ref):
    """Largest absolute difference between a run and the baseline."""
    return float(np.max(np.abs(np.asarray(y) - np.asarray(y_ref))))


def rms_error(y, y_ref):
    """Root-mean-square difference between a run and the baseline."""
    return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(y_ref)) ** 2)))


def overshoot_pct(t, y, target, t_start, t_end=None):
    """Overshoot beyond target, in % of the step size. 0 if no overshoot."""
    w = _window(t, t_start, t_end)
    y0 = y[w][0]
    step = target - y0
    if step == 0:
        return 0.0
    beyond = np.sign(step) * (y[w] - target)          # positive = past the target
    return float(max(0.0, beyond.max()) / abs(step) * 100)


def settling_time(t, y, target, t_start, band=0.02, t_end=None):
    """Time after t_start until y stays within +-band*|step| of target. NaN if never."""
    w = _window(t, t_start, t_end)
    tw, yw = t[w], y[w]
    tol = band * abs(target - yw[0])
    outside = np.where(np.abs(yw - target) > tol)[0]
    if outside.size == 0:
        return 0.0
    last = outside[-1]
    if last == len(yw) - 1:
        return float("nan")                            # still outside at the end
    return float(tw[last + 1] - t_start)


def max_dip(t, y, target, t_start, t_end=None):
    """Largest drop below target (e.g. speed dip after a load step)."""
    w = _window(t, t_start, t_end)
    return float(max(0.0, target - y[w].min()))