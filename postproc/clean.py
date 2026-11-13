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


def standstill_offset(n_rpm, y, n_max: float = 5.0) -> tuple[float, int]:
    """Zero-point offset of a sensor, estimated where the motor stands still (true value 0)."""
    still = (np.abs(n_rpm) < n_max) & ~np.isnan(y)
    return float(np.median(y[still])), int(still.sum())