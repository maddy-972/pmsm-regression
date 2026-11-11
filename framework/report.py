"""HTML problem report. Self-contained: plots are embedded as base64 PNG."""
import base64
import html
import io
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                      # render without a window
import matplotlib.pyplot as plt
import numpy as np
import yaml

from .regression import TestReport
from .result import UNITS, Result
from .testcase import TestCase

CSS = """
body{font-family:Segoe UI,Arial,sans-serif;max-width:1150px;margin:24px auto;padding:0 16px;color:#222}
h1{margin-bottom:4px} h2{border-bottom:2px solid #ddd;padding-bottom:4px;margin-top:40px}
table{border-collapse:collapse;margin:8px 0 16px} td,th{border:1px solid #ccc;padding:4px 10px;text-align:left}
th{background:#f3f3f3} tr.bad td{background:#fde8e8} tr.ok td{background:#eef8ee}
.sev-High{color:#b00020;font-weight:bold} .sev-Medium{color:#b26a00;font-weight:bold} .sev-None{color:#2e7d32;font-weight:bold}
pre,code{background:#f6f6f6;padding:2px 6px} pre{padding:8px} img{max-width:100%;margin:6px 0}
.meta td:first-child{font-weight:bold;background:#fafafa}
"""


def severity(rep: TestReport) -> tuple[str, str]:
    if any(c.kind == "REQ" and not c.passed for c in rep.checks):
        return "High", "Requirement violated"
    if not rep.passed:
        return "Medium", "Behaviour changed vs baseline - review required"
    return "None", "No deviation"


def _png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _overlay(sig: str, run: Result, base: Result, zoom: float = 0.02) -> str:
    """Left: full run. Right: zoom around the largest deviation."""
    t, y, yb = run.t, run[sig], base[sig]
    tc = t[int(np.argmax(np.abs(y - yb)))] if len(y) == len(yb) else t[len(t) // 2]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.2))
    for a, (lo, hi) in zip(ax, [(t[0], t[-1]), (tc - zoom, tc + zoom)]):
        a.plot(base.t, yb, lw=1.8, label=f"baseline v{base.version}")
        a.plot(t, y, "--", lw=1.3, label=f"v{run.version}")
        a.set_xlim(lo, hi); a.grid(alpha=0.3)
        a.set_xlabel("t / s"); a.set_ylabel(f"{sig} / {UNITS.get(sig, '')}")
    ax[0].set_title(f"{sig}: full run")
    ax[1].set_title(f"zoom at max deviation (t = {tc:.4f} s)")
    ax[0].legend()
    return _png(fig)


def _section(tc: TestCase, rep: TestReport, run: Result, base: Result, command: str) -> str:
    sev, why = severity(rep)
    failed = [c.name for c in rep.checks if not c.passed]
    title = f"{tc.name}: " + (", ".join(failed[:3]) + (" ..." if len(failed) > 3 else "")
                              if failed else "all checks passed")
    rows = "".join(
        f"<tr class='{'ok' if c.passed else 'bad'}'><td>{c.kind}</td><td>{html.escape(c.name)}</td>"
        f"<td>&le; {c.limit:g} {c.unit}</td><td>{c.value:.4g} {c.unit}</td>"
        f"<td>{'PASS' if c.passed else 'FAIL'}</td></tr>" for c in rep.checks)
    signals = ["wm"] + [c["signal"] for c in tc.checks.get("baseline", []) if c["signal"] != "wm"]
    plots = "".join(f"<img src='data:image/png;base64,{_overlay(s, run, base)}'>" for s in signals)
    return f"""
<h2 id="{tc.name}">{html.escape(title)}</h2>
<table class="meta">
<tr><td>Severity</td><td class="sev-{sev}">{sev}</td></tr>
<tr><td>Assessment</td><td>{why}</td></tr>
<tr><td>Release under test</td><td>v{run.version} ({run.param_file})</td></tr>
<tr><td>Baseline</td><td>v{base.version} ({base.param_file}, recorded {base.created})</td></tr>
<tr><td>Description</td><td>{html.escape(tc.description)}</td></tr>
</table>
<h3>Steps to reproduce</h3>
<ol><li>Check out tag <code>model-v{run.version}</code></li>
<li>Run <code>{html.escape(command)}</code></li>
<li>Test case <code>testcases/{tc.name}.yaml</code>, inputs:<pre>{html.escape(yaml.safe_dump(tc.inputs, sort_keys=False))}</pre></li></ol>
<h3>Expected vs actual</h3>
<table><tr><th>Type</th><th>Check</th><th>Expected</th><th>Actual</th><th>Result</th></tr>{rows}</table>
<h3>Signals: baseline vs release</h3>{plots}
"""


def write_report(items: list, path: str | Path, command: str) -> Path:
    """items: list of (TestCase, TestReport, run Result, baseline Result)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    run0, base0 = items[0][2], items[0][3]
    n_pass = sum(rep.passed for _, rep, _, _ in items)
    summary = "".join(
        f"<tr class='{'ok' if rep.passed else 'bad'}'><td><a href='#{tc.name}'>{tc.name}</a></td>"
        f"<td>{'PASS' if rep.passed else 'FAIL'}</td>"
        f"<td class='sev-{severity(rep)[0]}'>{severity(rep)[0]}</td></tr>" for tc, rep, _, _ in items)
    body = "".join(_section(tc, rep, run, base, command) for tc, rep, run, base in items)
    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Regression report v{run0.version} vs v{base0.version}</title><style>{CSS}</style></head><body>
<h1>Regression report: v{run0.version} vs baseline v{base0.version}</h1>
<p>Generated {datetime.now():%Y-%m-%d %H:%M} &middot; {n_pass}/{len(items)} test cases passed</p>
<table><tr><th>Test case</th><th>Result</th><th>Severity</th></tr>{summary}</table>
{body}</body></html>"""
    path.write_text(doc, encoding="utf-8")
    return path