"""Virtual test bench: run a speed-torque sweep on the Simulink model and turn it
into a realistic bench measurement (.mf4) with multi-rate channels and sensor effects."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from asammdf import MDF, Signal

from framework.runner import MatlabRunner
from framework.testcase import TestCase

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "bench" / "data"

# ---------- sweep definition ----------
SPEEDS = [20, 40, 60, 80, 100, 120]          # rad/s
TORQUES = [10, 25, 40, 55, 70, 85, 100]      # Nm
T_IDLE, T_RAMP, T_HOLD = 0.5, 0.5, 1.5       # s
P_POLE, B = 4, 0.01                          # must match params_v1_0

# ---------- synthetic loss model (added outside Simulink, documented) ----------
K_HYST, K_EDDY = 0.5, 0.01                   # iron losses  [W/Hz], [W/Hz^2]
K_SW, K_COND = 0.8, 0.006                    # inverter     [W/A],  [W/A^2]

# ---------- sensor effects ----------
TORQUE_OFFSET, TORQUE_NOISE = 0.3, 0.2       # Nm
SPEED_NOISE_RPM = 1.0
rng = np.random.default_rng(42)              # fixed seed -> reproducible measurement


def speed_run(w):
    """One run: standstill, ramp to w, torque staircase, unload."""
    t = T_IDLE + T_RAMP
    w_pts = [[0, 0], [T_IDLE, 0], [t, w]]
    tl_pts = [[0, 0], [t, 0]]
    points = []
    for T in TORQUES:
        tl_pts += [[t, T], [t + T_HOLD, T]]
        points.append((w, T, t, t + T_HOLD))
        t += T_HOLD
    tl_pts += [[t, 0], [t + T_RAMP + T_IDLE, 0]]
    w_pts += [[t, w], [t + T_RAMP, 0]]        # decelerate to standstill
    t += T_RAMP + T_IDLE
    tc = TestCase(name=f"sweep_{w}", description="bench sweep", t_stop=t,
                  inputs={"w_ref": {"type": "points", "points": w_pts},
                          "TL": {"type": "points", "points": tl_pts},
                          "iq_offset": 0})
    return tc, points


def physics(r):
    """True (noise-free) bench quantities from one simulation result."""
    wm, Te = r["wm"], r["Te"]
    id_, iq, ud, uq = r["id"], r["iq"], r["ud"], r["uq"]
    f_el = P_POLE * np.abs(wm) / (2 * np.pi)
    i_amp = np.hypot(id_, iq)
    p_el = 1.5 * (ud * id_ + uq * iq)                       # motor terminal power
    p_dc = p_el + K_HYST * f_el + K_EDDY * f_el**2 + K_SW * i_amp + K_COND * i_amp**2
    return {"wm": wm, "t_shaft": Te - B * wm, "p_el": p_el, "p_dc": p_dc,
            "id": id_, "iq": iq, "ud": ud, "uq": uq}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    chunks, truth, t_off = [], [], 0.0

    with MatlabRunner(ROOT / "model") as runner:
        for w in SPEEDS:
            tc, points = speed_run(w)
            r = runner.run(tc)
            ch = physics(r)
            for ww, T, t0, t1 in points:                     # truth: last 1 s of each hold
                m = (r.t >= t1 - 1.0) & (r.t < t1)
                p_sh = float(np.mean(ch["t_shaft"][m] * ch["wm"][m]))
                p_el, p_dc = float(np.mean(ch["p_el"][m])), float(np.mean(ch["p_dc"][m]))
                truth.append({"speed_rad_s": ww, "torque_Nm": T,
                              "t_start": round(t0 + t_off, 4), "t_end": round(t1 + t_off, 4),
                              "P_shaft_W": round(p_sh, 1), "P_el_W": round(p_el, 1),
                              "P_dc_W": round(p_dc, 1),
                              "eta_motor": round(p_sh / p_el, 4), "eta_system": round(p_sh / p_dc, 4)})
            ch["t"] = r.t + t_off
            chunks.append(ch)
            t_off += tc.t_stop + 1e-4
            print(f"speed {w:>3} rad/s done  ({tc.t_stop:.1f} s simulated)")

    d = {k: np.concatenate([c[k] for c in chunks]) for k in chunks[0]}
    t10k = d["t"]

    # Inverter ECU channels, 10 kHz, light noise
    inv = {k: d[k] + rng.normal(0, 0.5 if k in ("id", "iq") else 0.2, t10k.size)
           for k in ("id", "iq", "ud", "uq")}

    # Test bench channels, 1 kHz: noise, torque offset, spikes, one sensor freeze
    t1k = t10k[::10]
    n_rpm = d["wm"][::10] * 60 / (2 * np.pi) + rng.normal(0, SPEED_NOISE_RPM, t1k.size)
    T_sh = d["t_shaft"][::10] + TORQUE_OFFSET + rng.normal(0, TORQUE_NOISE, t1k.size)
    spikes = sorted(int(i) for i in rng.integers(0, t1k.size, 3))
    T_sh[spikes] += 40
    i0 = int(0.6 * t1k.size)
    T_sh[i0:i0 + 300] = T_sh[i0]                            # 0.3 s frozen sensor

    # Power analyzer, 100 Hz (10 ms block averages)
    n = d["p_dc"].size // 100 * 100
    p_blk = d["p_dc"][:n].reshape(-1, 100).mean(axis=1)
    t100 = t10k[:n].reshape(-1, 100)[:, 0]
    Udc = 300 - 0.05 * p_blk / 300 + rng.normal(0, 0.3, t100.size)
    Idc = p_blk / Udc + rng.normal(0, 0.1, t100.size)

    f32 = np.float32
    mdf = MDF(version="4.10")
    mdf.header.comment = json.dumps({
        "source": "virtual test bench (Simulink PMSM FOC v1.0 + synthetic losses/sensors)",
        "seed": 42, "artefacts": {"torque_spikes_s": [round(float(t1k[i]), 3) for i in spikes],
                                  "torque_freeze_s": [round(float(t1k[i0]), 3), round(float(t1k[i0 + 299]), 3)],
                                  "torque_offset_Nm": TORQUE_OFFSET}})
    mdf.append([Signal(v.astype(f32), t10k, name=k, unit="A" if k[0] == "i" else "V")
                for k, v in inv.items()], comment="Inverter ECU, 10 kHz")
    mdf.append([Signal(n_rpm.astype(f32), t1k, name="n_rpm", unit="rpm"),
                Signal(T_sh.astype(f32), t1k, name="T_shaft", unit="Nm")], comment="Test bench, 1 kHz")
    mdf.append([Signal(Udc.astype(f32), t100, name="Udc", unit="V"),
                Signal(Idc.astype(f32), t100, name="Idc", unit="A")], comment="Power analyzer, 100 Hz")
    out = OUT / "bench_sweep_raw.mf4"
    mdf.save(out, overwrite=True)
    mdf.close()

    with open(OUT / "sweep_truth.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(truth[0]))
        wr.writeheader()
        wr.writerows(truth)

    fig, ax = plt.subplots(3, 1, figsize=(12, 7), sharex=True)
    ax[0].plot(t1k, n_rpm, lw=0.6); ax[0].set_ylabel("n / rpm")
    ax[1].plot(t1k, T_sh, lw=0.6); ax[1].set_ylabel("T_shaft / Nm")
    ax[2].plot(t100, Udc * Idc / 1000, lw=0.6); ax[2].set_ylabel("P_dc / kW")
    ax[2].set_xlabel("t / s")
    for a in ax: a.grid(alpha=0.3)
    fig.savefig(OUT / "overview.png", dpi=110, bbox_inches="tight")

    print(f"\nsaved {out.relative_to(ROOT)}  ({out.stat().st_size / 1e6:.1f} MB), "
          f"{len(truth)} operating points, total {t10k[-1]:.1f} s")


if __name__ == "__main__":
    main()