"""Analyse a bench measurement: clean -> steady states -> operating points -> maps -> truth check."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from .steady import K95, compare_with_truth, operating_points, steady_windows

from .clean import frozen_segments, remove_spikes, standstill_offset
from .io import load_mf4
from .maps import RPM, add_losses, plot_eta_map, torque_envelope
from .steady import compare_with_truth, operating_points, steady_windows

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "bench" / "data"
CHANNELS = ["n_rpm", "T_shaft", "Udc", "Idc", "id", "iq", "ud", "uq"]
MOTOR = {"p": 4, "psi": 0.07, "Lq": 1.2e-3, "Rs": 0.02,        # datasheet values (params_v1_0)
         "Umax": 300 / np.sqrt(3), "Imax": 250}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mf4", nargs="?", default=str(DATA / "bench_sweep_raw.mf4"))
    ap.add_argument("--truth", default=str(DATA / "sweep_truth.csv"))
    args = ap.parse_args()

    # ---------- load + clean ----------
    df, meta = load_mf4(args.mf4, master="T_shaft", channels=CHANNELS)
    print(f"Loaded {len(df)} samples, {df['t'].iat[-1]:.1f} s")
    T, spikes = remove_spikes(df["T_shaft"].to_numpy())
    print(f"Spikes removed:    {len(spikes)} at t = {[round(float(df['t'].iat[i]), 3) for i in spikes]}")
    segs = frozen_segments(T)
    for s, e in segs:
        T[s:e + 1] = np.nan
    print(f"Frozen segments:   {[(round(float(df['t'].iat[s]), 3), round(float(df['t'].iat[e]), 3)) for s, e in segs]}")
    off, u_off, n_still = standstill_offset(df["n_rpm"].to_numpy(), T)
    df["T_shaft"] = T - off
    print(f"Torque offset:     {off:.3f} ± {u_off:.3f} Nm (from {n_still} standstill samples)")
    if "artefacts" in meta:
        print(f"Injected (truth):  {meta['artefacts']}")

    # ---------- operating points ----------
    windows = steady_windows(df)
    pts = add_losses(operating_points(df, windows, u_off), MOTOR["Rs"])
    pts.to_csv(DATA / "operating_points.csv", index=False)
    print(f"\nSteady-state windows found: {len(windows)}")

    rejected = None
    if Path(args.truth).exists():
        cmp_ = compare_with_truth(pts, pd.read_csv(args.truth))
        f = cmp_[cmp_["found"]]
        rejected = cmp_[~cmp_["found"]]
        print(f"Matched {len(f)}/{len(cmp_)} truth points")
        print(f"max |speed error|       {f['err_speed'].abs().max():.4f} rad/s")
        print(f"max |torque error|      {f['err_torque'].abs().max():.4f} Nm")
        for k in ("motor", "system"):
            err, u = f[f"err_eta_{k}_pp"].abs(), f[f"u_eta_{k}_pp"]
            worst = f.loc[err.idxmax()]
            print(f"eta_{k:<6}: max |error| {err.max():.3f} %-pt at {worst.speed_rad_s:.0f} rad/s / "
                 f"{worst.torque_Nm:.0f} Nm;  within k·u: {(err <= K95 * u).mean():.0%} of points")

    # ---------- efficiency maps ----------
    n_env = np.linspace(0, 1400, 300)
    env = (n_env, torque_envelope(n_env, MOTOR["p"], MOTOR["psi"], MOTOR["Lq"], MOTOR["Rs"],
                                  MOTOR["Umax"], MOTOR["Imax"]))
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    for a, col, title in ((ax[0], "eta_motor", "Motor efficiency / %  (P_shaft / P_el)"),
                          (ax[1], "eta_system", "System efficiency / %  (P_shaft / P_dc)")):
        fig.colorbar(plot_eta_map(a, pts, col, title, env, rejected), ax=a)
    fig.savefig(DATA / "eta_maps.png", dpi=120, bbox_inches="tight")

    # ---------- loss breakdown ----------
    pl = (pts.assign(_n=(pts["speed_rad_s"] * RPM).round(0), _T=pts["torque_Nm"].round(0))
       .sort_values(["_n", "_T"]).reset_index(drop=True))
    x = np.arange(len(pl))
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.bar(x, pl["P_cu_W"], label="copper  1.5·Rs·|i|²")
    ax.bar(x, pl["P_motor_other_W"], bottom=pl["P_cu_W"], label="other motor (friction)")
    ax.bar(x, pl["P_dc_side_W"], bottom=pl["P_cu_W"] + pl["P_motor_other_W"],
           label="DC side  P_dc − P_el (inverter + iron)")
    ax.set_xticks(x, [f"{s * RPM:.0f}/{t:.0f}" for s, t in zip(pl["speed_rad_s"], pl["torque_Nm"])],
                  rotation=90, fontsize=7)
    ax.set(xlabel="operating point  n / rpm  /  T / Nm", ylabel="loss / W")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    fig.savefig(DATA / "losses.png", dpi=120, bbox_inches="tight")

    # ---------- uncertainty check ----------
    if rejected is not None:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(f["P_dc_W"] / 1000, f["err_eta_system_pp"].abs(), "o", label="|error| vs truth")
        ax.plot(f["P_dc_W"] / 1000, 2 * f["u_eta_system_pp"], "r_", ms=14, mew=2,
                label="2u estimated (95 %)")
        ax.set(xlabel="P_dc / kW", ylabel="η_system error / %-points",
               title="Measurement uncertainty vs operating power")
        ax.legend(); ax.grid(alpha=0.3)
        fig.savefig(DATA / "uncertainty.png", dpi=120, bbox_inches="tight")
    print(f"\nFigures: eta_maps.png, losses.png, uncertainty.png in {DATA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()