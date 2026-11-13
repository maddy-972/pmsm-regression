"""Analyse a bench measurement: clean -> steady states -> operating points -> compare with truth."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .clean import frozen_segments, remove_spikes, standstill_offset
from .io import load_mf4
from .steady import compare_with_truth, operating_points, steady_windows

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "bench" / "data"
CHANNELS = ["n_rpm", "T_shaft", "Udc", "Idc", "id", "iq", "ud", "uq"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mf4", nargs="?", default=str(DATA / "bench_sweep_raw.mf4"))
    ap.add_argument("--truth", default=str(DATA / "sweep_truth.csv"))
    args = ap.parse_args()

    df, meta = load_mf4(args.mf4, master="T_shaft", channels=CHANNELS)
    print(f"Loaded {len(df)} samples, {df['t'].iat[-1]:.1f} s")

    T, spikes = remove_spikes(df["T_shaft"].to_numpy())
    print(f"Spikes removed:    {len(spikes)} at t = {[round(float(df['t'].iat[i]), 3) for i in spikes]}")
    segs = frozen_segments(T)
    for s, e in segs:
        T[s:e + 1] = np.nan
    print(f"Frozen segments:   {[(round(df['t'].iat[s], 3), round(df['t'].iat[e], 3)) for s, e in segs]}")

    off, n_still = standstill_offset(df["n_rpm"].to_numpy(), T)
    df["T_shaft"] = T - off
    print(f"Torque offset:     {off:.3f} Nm (from {n_still} standstill samples)")
    if "artefacts" in meta:
        print(f"Injected (truth):  {meta['artefacts']}")

    windows = steady_windows(df)
    pts = operating_points(df, windows)
    pts.to_csv(DATA / "operating_points.csv", index=False)
    print(f"\nSteady-state windows found: {len(windows)}")

    if Path(args.truth).exists():
        cmp_ = compare_with_truth(pts, pd.read_csv(args.truth))
        f = cmp_[cmp_["found"]]
        print(f"Matched {len(f)}/{len(cmp_)} truth points")
        if (~cmp_["found"]).any():
            print("Missing:\n" + cmp_.loc[~cmp_["found"], ["speed_rad_s", "torque_Nm", "t_start", "t_end"]]
                  .to_string(index=False))
        print(f"max |speed error|       {f['err_speed'].abs().max():.4f} rad/s")
        print(f"max |torque error|      {f['err_torque'].abs().max():.4f} Nm")
        print(f"max |eta_motor error|   {f['err_eta_motor_pp'].abs().max():.3f} %-points")
        print(f"max |eta_system error|  {f['err_eta_system_pp'].abs().max():.3f} %-points")

    fig, ax = plt.subplots(2, 1, figsize=(12, 5), sharex=True)
    ax[0].plot(df["t"], df["n_rpm"], lw=0.5); ax[0].set_ylabel("n / rpm")
    ax[1].plot(df["t"], df["T_shaft"], lw=0.5); ax[1].set_ylabel("T_shaft / Nm (cleaned)")
    for t0, t1 in windows:
        for a in ax:
            a.axvspan(t0, t1, color="tab:green", alpha=0.25)
    ax[1].set_xlabel("t / s")
    fig.savefig(DATA / "steady_state.png", dpi=110, bbox_inches="tight")


if __name__ == "__main__":
    main()