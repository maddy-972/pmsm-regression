"""Config-driven post-processing report.  Usage: python -m postproc.report <config.yaml>"""
import argparse
import sys
from pathlib import Path

import yaml

from .html_report import write_html
from .kpi import evaluate_limits
from .pipeline import run

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("-o", "--out", help="output HTML path")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    res = run(cfg, ROOT)
    limits = evaluate_limits(cfg.get("limits", []), res)
    out = Path(args.out) if args.out else ROOT / "reports" / f"{cfg_path.stem}_report.html"
    write_html(res, limits, cfg_path, out)

    for L in limits:
        print(f"{'PASS' if L['passed'] else 'FAIL'}  {L['name']:<22} {L['value']:10.4g} {L['unit']}")
    print(f"\n{res['quality']['n_points']} operating points | report: {out}")
    return 0 if all(L["passed"] for L in limits) else 1


if __name__ == "__main__":
    sys.exit(main())