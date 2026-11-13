"""Pass/fail limit checks on operating points and data-quality figures."""
import math

import pandas as pd


def _select(pts: pd.DataFrame, where: dict | None) -> pd.DataFrame:
    m = pd.Series(True, index=pts.index)
    for col, (lo, hi) in (where or {}).items():
        m &= (pts[col] >= lo) & (pts[col] <= hi)
    return pts[m]


def evaluate_limits(limits: list[dict], res: dict) -> list[dict]:
    out = []
    for L in limits:
        if "quality" in L:
            value, scope = float(res["quality"][L["quality"]]), "data quality"
        else:
            sel = _select(res["points"], L.get("where"))
            value = float(getattr(sel[L["kpi"]], L.get("stat", "min"))()) if len(sel) else float("nan")
            scope = f"{L.get('stat', 'min')} over {len(sel)} points"
        lo, hi = L.get("min"), L.get("max")
        passed = (not math.isnan(value)) and (lo is None or value >= lo) and (hi is None or value <= hi)
        out.append({"name": L["name"], "value": value, "min": lo, "max": hi,
                    "unit": L.get("unit", ""), "scope": scope, "passed": passed})
    return out