"""Steady-state detection, operating-point extraction with uncertainty, truth comparison."""
import numpy as np
import pandas as pd
K95 = 2.26


def steady_windows(df, win_s=0.3, n_std_max=3.0, T_std_max=0.5, n_min=50.0,
                   min_dur=0.8, margin=0.1) -> list[tuple[float, float]]:
    """Windows where speed and torque are both stable (rolling std below limits).
    margin trims the edges; windows shorter than min_dur after trimming are dropped."""
    dt = float(np.median(np.diff(df["t"])))
    w = max(3, int(round(win_s / dt)))
    n_std = df["n_rpm"].rolling(w, center=True).std()
    T_std = df["T_shaft"].rolling(w, center=True).std()
    ok = ((n_std < n_std_max) & (T_std < T_std_max) & (df["n_rpm"].abs() > n_min)).to_numpy()
    edges = np.diff(np.r_[0, ok.astype(int), 0])
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
    t = df["t"].to_numpy()
    out = []
    for s, e in zip(starts, ends):
        t0, t1 = t[s] + margin, t[e - 1] - margin
        if t1 - t0 >= min_dur:
            out.append((float(t0), float(t1)))
    return out


def _block_sem(x, n_blocks: int = 10) -> float:
    """Standard error of the mean from block means (robust to correlated samples)."""
    m = np.array([b.mean() for b in np.array_split(np.asarray(x, float), n_blocks)])
    return float(m.std(ddof=1) / np.sqrt(len(m)))


def operating_points(df, windows, u_T_offset: float = 0.0) -> pd.DataFrame:
    """Mean values, derived powers, efficiencies and their standard uncertainty per window."""
    rows = []
    for t0, t1 in windows:
        d = df[(df["t"] >= t0) & (df["t"] <= t1)]
        w = d["n_rpm"] * 2 * np.pi / 60
        ps = d["T_shaft"] * w 
        pe = 1.5 * (d["ud"] * d["id"] + d["uq"] * d["iq"])
        pd_ = d["Udc"] * d["Idc"]
        p_sh, p_el, p_dc = float(ps.mean()), float(pe.mean()), float(pd_.mean())
        eta_m, eta_s = p_sh / p_el, p_sh / p_dc
        u_sh, u_el, u_dc = _block_sem(ps), _block_sem(pe), _block_sem(pd_)
        rows.append({"t_start": t0, "t_end": t1, "speed_rad_s": float(w.mean()),
                     "torque_Nm": float(d["T_shaft"].mean()),
                     "P_shaft_W": p_sh, "P_el_W": p_el, "P_dc_W": p_dc,
                     "i_sq_A2": float((d["id"] ** 2 + d["iq"] ** 2).mean()),
                     "eta_motor": eta_m, "eta_system": eta_s,
                     "u_eta_motor": eta_m * float(np.hypot(np.hypot(u_sh / p_sh, u_T_offset / d["T_shaft"].mean()), u_el / p_el)),
                     "u_eta_system": eta_s * float(np.hypot(np.hypot(u_sh / p_sh, u_T_offset / d["T_shaft"].mean()), u_dc / p_dc))})
    return pd.DataFrame(rows)


def compare_with_truth(points: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    """Match detected points to truth by time; errors and uncertainties in %-points."""
    out = truth.copy()
    out["found"] = False
    cols = ("err_speed", "err_torque", "err_eta_motor_pp", "err_eta_system_pp",
            "u_eta_motor_pp", "u_eta_system_pp")
    for col in cols:
        out[col] = np.nan
    for _, p in points.iterrows():
        mid = (p.t_start + p.t_end) / 2
        m = (truth["t_start"] <= mid) & (truth["t_end"] >= mid)
        if m.any():
            i = truth.index[m][0]
            out.loc[i, "found"] = True
            out.loc[i, "err_speed"] = p.speed_rad_s - truth.at[i, "speed_rad_s"]
            out.loc[i, "err_torque"] = p.torque_Nm - truth.at[i, "torque_Nm"]
            out.loc[i, "err_eta_motor_pp"] = 100 * (p.eta_motor - truth.at[i, "eta_motor"])
            out.loc[i, "err_eta_system_pp"] = 100 * (p.eta_system - truth.at[i, "eta_system"])
            out.loc[i, "u_eta_motor_pp"] = 100 * p.u_eta_motor
            out.loc[i, "u_eta_system_pp"] = 100 * p.u_eta_system
    return out