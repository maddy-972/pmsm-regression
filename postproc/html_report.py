"""Self-contained HTML report for a post-processed measurement."""
import base64
import html
import io
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .steady import K95

CSS = """
body{font-family:Segoe UI,Arial,sans-serif;max-width:1150px;margin:24px auto;padding:0 16px;color:#222}
h2{border-bottom:2px solid #ddd;padding-bottom:4px;margin-top:36px}
table{border-collapse:collapse;margin:8px 0 16px;font-size:14px} td,th{border:1px solid #ccc;padding:3px 9px;text-align:left}
th{background:#f3f3f3} tr.bad td{background:#fde8e8} tr.ok td{background:#eef8ee}
.verdict-PASS{color:#2e7d32} .verdict-FAIL{color:#b00020} img{max-width:100%}
"""


def _png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _limit_text(L) -> str:
    parts = ([f"≥ {L['min']:g}"] if L["min"] is not None else []) + \
            ([f"≤ {L['max']:g}"] if L["max"] is not None else [])
    return " and ".join(parts) + f" {L['unit']}"


def write_html(res: dict, limits: list[dict], cfg_path: Path, out: Path) -> Path:
    q, pts, truth = res["quality"], res["points"], res["truth"]
    verdict = "PASS" if all(L["passed"] for L in limits) else "FAIL"

    lim_rows = "".join(
        f"<tr class='{'ok' if L['passed'] else 'bad'}'><td>{html.escape(L['name'])}</td><td>{L['scope']}</td>"
        f"<td>{_limit_text(L)}</td><td>{L['value']:.4g} {L['unit']}</td>"
        f"<td>{'PASS' if L['passed'] else 'FAIL'}</td></tr>" for L in limits)
    ch_rows = "".join(
        f"<tr><td>{c['name']}</td><td>{html.escape(c['file_name'])}</td><td>{c['unit']}</td>"
        f"<td>{c['rate_Hz']:g}</td><td>{c['samples']}</td></tr>" for c in res["channels"])
    spikes = "".join(f"<li>{ch}: {len(v)} spike(s) at t = {v} s</li>" for ch, v in q["spikes"].items())
    frozen = "".join(f"<li>{ch}: {len(v)} segment(s) {v} s (blanked)</li>" for ch, v in q["frozen"].items())
    off = q.get("offset")
    off_txt = (f"{off['value']:.3f} ± {off['u']:.3f} Nm, from {off['n_samples']} standstill samples"
               if off else "not corrected")

    p = pts.assign(_n=pts["n_rpm"].round(0), _T=pts["torque_Nm"].round(0)).sort_values(["_n", "_T"])
    table = pd.DataFrame({
        "n / rpm": p["n_rpm"].round(0), "T / Nm": p["torque_Nm"].round(2),
        "P_shaft / W": p["P_shaft_W"].round(0), "P_el / W": p["P_el_W"].round(0),
        "P_dc / W": p["P_dc_W"].round(0),
        "η_motor / %": [f"{100 * e:.2f} ± {100 * K95 * u:.2f}" for e, u in zip(p["eta_motor"], p["u_eta_motor"])],
        "η_system / %": [f"{100 * e:.2f} ± {100 * K95 * u:.2f}" for e, u in zip(p["eta_system"], p["u_eta_system"])],
    }).to_html(index=False, border=0)

    truth_html = ""
    if truth is not None:
        f, miss = truth[truth["found"]], truth[~truth["found"]]
        cov = lambda k: (f[f"err_eta_{k}_pp"].abs() <= K95 * f[f"u_eta_{k}_pp"]).mean()
        miss_txt = ", ".join(f"{r.speed_rad_s:g} rad/s / {r.torque_Nm:g} Nm" for r in miss.itertuples()) or "none"
        truth_html = f"""<h2>Validation against ground truth</h2>
<table><tr><td>Points found</td><td>{len(f)} / {len(truth)} (missing: {miss_txt})</td></tr>
<tr><td>Max |speed error|</td><td>{f['err_speed'].abs().max():.4f} rad/s</td></tr>
<tr><td>Max |torque error|</td><td>{f['err_torque'].abs().max():.4f} Nm</td></tr>
<tr><td>η_motor errors within k·u</td><td>{cov('motor'):.0%}</td></tr>
<tr><td>η_system errors within k·u</td><td>{cov('system'):.0%}</td></tr>
<tr><td>Injected artefacts</td><td>{html.escape(str(res['meta'].get('artefacts', '-')))}</td></tr></table>"""

    figs = {k: _png(v) for k, v in res["figures"].items()}
    titles = {"signals": "Cleaned signals and detected steady-state windows", "maps": "Efficiency maps",
              "losses": "Loss breakdown", "uncertainty": "Uncertainty validation"}
    fig_html = "".join(f"<h3>{titles[k]}</h3><img src='data:image/png;base64,{v}'>" for k, v in figs.items())

    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Measurement report {html.escape(Path(res['file']).name)}</title><style>{CSS}</style></head><body>
<h1>Measurement report: <span class="verdict-{verdict}">{verdict}</span></h1>
<p>{html.escape(res['file'])} &middot; {res['duration_s']:.1f} s &middot; config {html.escape(cfg_path.name)}
&middot; generated {datetime.now():%Y-%m-%d %H:%M}</p>
<h2>Limit checks</h2>
<table><tr><th>Check</th><th>Scope</th><th>Limit</th><th>Actual</th><th>Result</th></tr>{lim_rows}</table>
<h2>Data quality</h2>
<ul>{spikes}{frozen}<li>Torque zero-point offset: {off_txt}</li>
<li>Steady-state operating points: {q['n_points']}</li></ul>
<h3>Channels</h3>
<table><tr><th>Internal</th><th>In file</th><th>Unit</th><th>Rate / Hz</th><th>Samples</th></tr>{ch_rows}</table>
<h2>Results</h2>{fig_html}
<h3>Operating points (uncertainty: k·u, 95 %)</h3>{table}
{truth_html}</body></html>"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return out