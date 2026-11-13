"""Efficiency maps, operating envelope and loss breakdown from operating points."""
import matplotlib.tri as mtri
import numpy as np

RPM = 60 / (2 * np.pi)


def add_losses(pts, Rs: float):
    """Loss split. Copper loss from measured currents and the winding resistance."""
    p = pts.copy()
    p["P_cu_W"] = 1.5 * Rs * p["i_sq_A2"]
    p["P_motor_other_W"] = p["P_el_W"] - p["P_shaft_W"] - p["P_cu_W"]
    p["P_dc_side_W"] = p["P_dc_W"] - p["P_el_W"]
    return p


def torque_envelope(n_rpm, p, psi, Lq, Rs, Umax, Imax):
    """Max torque vs speed for id = 0: current limit, then voltage limit (no field weakening)."""
    iq = np.linspace(0, Imax, 2001)
    T = []
    for n in n_rpm:
        we = p * n / RPM
        ok = iq[np.hypot(we * Lq * iq, we * psi + Rs * iq) <= Umax]
        T.append(1.5 * p * psi * ok.max() if ok.size else 0.0)
    return np.array(T)


def plot_eta_map(ax, pts, col, title, envelope=None, rejected=None):
    n, T, z = pts["speed_rad_s"] * RPM, pts["torque_Nm"], 100 * pts[col]
    tri = mtri.Triangulation(n, T)
    levels = np.arange(np.floor(z.min() / 2) * 2, np.ceil(z.max() / 2) * 2 + 2, 2)
    cf = ax.tricontourf(tri, z, levels=levels, cmap="viridis")
    cl = ax.tricontour(tri, z, levels=levels[::2], colors="k", linewidths=0.5)
    ax.clabel(cl, fmt="%.0f", fontsize=7)
    ax.plot(n, T, "k.", ms=3, label="measured points")
    if rejected is not None and len(rejected):
        ax.plot(rejected["speed_rad_s"] * RPM, rejected["torque_Nm"], "rx", ms=10, mew=2,
                label="rejected (sensor freeze)")
    if envelope is not None:
        ax.plot(*envelope, "r-", lw=2, label="torque limit (id = 0)")
    ax.set(title=title, xlabel="n / rpm", ylabel="T / Nm", xlim=(0, 1400), ylim=(0, 115))
    ax.legend(loc="lower left", fontsize=7)
    return cf