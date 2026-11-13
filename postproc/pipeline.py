"""Config-driven post-processing pipeline: load -> clean -> steady states -> points -> figures."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .clean import frozen_segments, remove_spikes, standstill_offset
from .io import channel_info, load_mf4
from .maps import RPM, add_losses, plot_eta_map, torque_envelope
from .steady import K95, compare_with_truth, operating_points, steady_windows


def run(cfg: dict, root: Path) -> dict:
    m = cfg["measurement"]
    path = root / m["file"]
    chans = m["channels"]                                     # internal -> file name
    df, meta = load_mf4(path, chans[m["master"]], list(chans.values()))
    df = df.rename(columns={v: k for k, v in chans.items()})

    q = {"spikes": {}, "frozen": {}}
    c = cfg.get("cleaning", {})

    for ch in c.get("spikes", {}).get("channels", []):
        y, idx = remove_spikes(df[ch].to_numpy(), k=c["spikes"].get("k", 8.0))
        df[ch] = y
        q["spikes"][ch] = [round(float(df["t"].iat[i]), 3) for i in idx]

    for ch in c.get("frozen", {}).get("channels", []):
        y = df[ch].to_numpy().copy()
        segs = frozen_segments(y, c["frozen"].get("min_len", 50))
        for s, e in segs:
            y[s:e + 1] = np.nan
        df[ch] = y
        q["frozen"][ch] = [(round(float(df["t"].iat[s]), 3), round(float(df["t"].iat[e]), 3)) for s, e in segs]

    u_off = 0.0
    if "offset" in c:
        o = c["offset"]
        off, u_off, n = standstill_offset(df["n_rpm"].to_numpy(), df[o["channel"]].to_numpy(),
                                          n_max=o.get("n_max_rpm", 5.0))
        df[o["channel"]] = df[o["channel"]] - off
        q["offset"] = {"channel": o["channel"], "value": off, "u": u_off, "n_samples": n}

    windows = steady_windows(df, **cfg.get("steady_state", {}))
    pts = operating_points(df, windows, u_off)
    if cfg.get("motor"):
        pts = add_losses(pts, cfg["motor"]["Rs"])
    pts["n_rpm"] = pts["speed_rad_s"] * RPM
    pts["P_loss_total_W"] = pts["P_dc_W"] - pts["P_shaft_W"]

    truth = None
    if m.get("truth") and (root / m["truth"]).exists():
        truth = compare_with_truth(pts, pd.read_csv(root / m["truth"]))

    q["n_points"] = len(pts)
    q["n_spikes"] = sum(len(v) for v in q["spikes"].values())
    q["frozen_s"] = round(sum(e - s for v in q["frozen"].values() for s, e in v), 3)
    q["offset_Nm"] = abs(q["offset"]["value"]) if "offset" in q else 0.0

    res = {"file": m["file"], "meta": meta, "duration_s": float(df["t"].iat[-1] - df["t"].iat[0]),
           "channels": channel_info(path, chans), "quality": q, "df": df,
           "windows": windows, "points": pts, "truth": truth}
    res["figures"] = make_figures(res, cfg)
    return res


def make_figures(res: dict, cfg: dict) -> dict:
    df, pts, truth, figs = res["df"], res["points"], res["truth"], {}

    fig, ax = plt.subplots(2, 1, figsize=(12, 4.5), sharex=True)
    ax[0].plot(df["t"], df["n_rpm"], lw=0.5); ax[0].set_ylabel("n / rpm")
    ax[1].plot(df["t"], df["T_shaft"], lw=0.5); ax[1].set_ylabel("T_shaft / Nm")
    for t0, t1 in res["windows"]:
        for a in ax:
            a.axvspan(t0, t1, color="tab:green", alpha=0.25)
    ax[1].set_xlabel("t / s")
    figs["signals"] = fig

    mot, env = cfg.get("motor"), None
    if mot:
        n_env = np.linspace(0, 1400, 300)
        env = (n_env, torque_envelope(n_env, mot["p"], mot["psi"], mot["Lq"], mot["Rs"],
                                      mot["Udc"] / np.sqrt(3), mot["Imax"]))
    rejected = None if truth is None else truth[~truth["found"]]
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    for a, col, title in ((ax[0], "eta_motor", "Motor efficiency / %  (P_shaft / P_el)"),
                          (ax[1], "eta_system", "System efficiency / %  (P_shaft / P_dc)")):
        fig.colorbar(plot_eta_map(a, pts, col, title, env, rejected), ax=a)
    figs["maps"] = fig

    if mot:
        pl = (pts.assign(_n=pts["n_rpm"].round(0), _T=pts["torque_Nm"].round(0))
                 .sort_values(["_n", "_T"]).reset_index(drop=True))
        x = np.arange(len(pl))
        fig, ax = plt.subplots(figsize=(14, 4))
        ax.bar(x, pl["P_cu_W"], label="copper  1.5·Rs·|i|²")
        ax.bar(x, pl["P_motor_other_W"], bottom=pl["P_cu_W"], label="other motor (friction)")
        ax.bar(x, pl["P_dc_side_W"], bottom=pl["P_cu_W"] + pl["P_motor_other_W"],
               label="DC side  P_dc − P_el (inverter + iron)")
        ax.set_xticks(x, [f"{n:.0f}/{t:.0f}" for n, t in zip(pl["_n"], pl["_T"])], rotation=90, fontsize=7)
        ax.set(xlabel="operating point  n / rpm  /  T / Nm", ylabel="loss / W")
        ax.legend(); ax.grid(axis="y", alpha=0.3)
        figs["losses"] = fig

    if truth is not None:
        f = truth[truth["found"]]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(f["P_dc_W"] / 1000, f["err_eta_system_pp"].abs(), "o", label="|error| vs truth")
        ax.plot(f["P_dc_W"] / 1000, K95 * f["u_eta_system_pp"], "r_", ms=14, mew=2,
                label="k·u estimated (95 %)")
        ax.set(xlabel="P_dc / kW", ylabel="η_system error / %-points",
               title="Measurement uncertainty vs operating power")
        ax.legend(); ax.grid(alpha=0.3)
        figs["uncertainty"] = fig
    return figs