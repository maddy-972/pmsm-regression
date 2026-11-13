"""Measurement data cleaning: spikes, frozen sensors, zero-point offsets."""
import numpy as np
import pandas as pd


def noise_sigma(y) -> float:
    """Robust noise estimate from sample-to-sample differences (insensitive to steps)."""
    d = np.diff(np.asarray(y, float)[~np.isnan(y)])
    return float(1.4826 * np.median(np.abs(d)) / np.sqrt(2))


def remove_spikes(y, k: float = 8.0):
    """Replace single-sample spikes: a sample far from BOTH neighbours, while the
    neighbours agree with each other. Step edges are kept, since there the neighbours differ.
    Returns (cleaned array, indices of removed spikes)."""
    y = np.asarray(y, float).copy()
    thr = k * noise_sigma(y)
    d_prev, d_next = y[1:-1] - y[:-2], y[1:-1] - y[2:]
    cand = ((np.abs(d_prev) > thr) & (np.abs(d_next) > thr)
            & (np.sign(d_prev) == np.sign(d_next))
            & (np.abs(y[2:] - y[:-2]) < thr))
    idx = np.where(cand)[0] + 1
    y[idx] = 0.5 * (y[idx - 1] + y[idx + 1])
    return y, idx


def frozen_segments(y, min_len: int = 50) -> list[tuple[int, int]]:
    """Runs of exactly repeated values. A live sensor with noise never repeats exactly,
    so >= min_len identical samples means a frozen signal. Returns inclusive index ranges."""
    eq = np.diff(np.asarray(y)) == 0
    edges = np.diff(np.r_[0, eq.astype(int), 0])
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
    return [(int(s), int(e)) for s, e in zip(starts, ends) if e - s + 1 >= min_len]


def standstill_offset(n_rpm, y, n_max: float = 5.0, win: int = 300, n_std_max: float = 3.0):
    """Zero-point offset from steady standstill (true torque = 0). Samples passing through
    zero speed during acceleration or braking are excluded via a rolling speed std."""
    n = pd.Series(np.asarray(n_rpm, float))
    steady = (n.rolling(win, center=True).std() < n_std_max).to_numpy()
    still = (np.abs(n.to_numpy()) < n_max) & steady & ~np.isnan(y)
    vals = y[still]
    u = float(1.2533 * vals.std(ddof=1) / np.sqrt(vals.size))   # standard error of the median
    return float(np.median(vals)), u, int(vals.size)