"""Load multi-rate MF4 measurements onto one common time grid."""
import html
import json

import numpy as np
import pandas as pd
from asammdf import MDF


def load_mf4(path, master: str, channels: list[str]):
    """Resample all channels onto the native time base of `master` (linear interpolation).
    Returns (DataFrame with column 't' + channels, header metadata dict)."""
    with MDF(path) as mdf:
        ref = mdf.get(master)
        t = np.asarray(ref.timestamps, dtype=float)
        data = {"t": t, master: np.asarray(ref.samples, dtype=float)}
        for name in channels:
            if name == master:
                continue
            s = mdf.get(name)
            data[name] = np.interp(t, np.asarray(s.timestamps, float), np.asarray(s.samples, float))
        txt = html.unescape(mdf.header.comment or "")
        meta = json.loads(txt[txt.find("{"): txt.rfind("}") + 1]) if "{" in txt else {}
    return pd.DataFrame(data), meta

def channel_info(path, channels: dict) -> list[dict]:
    """Unit, sample rate and sample count per channel (internal name -> file name)."""
    out = []
    with MDF(path) as mdf:
        for key, name in channels.items():
            s = mdf.get(name)
            ts = np.asarray(s.timestamps, float)
            out.append({"name": key, "file_name": name, "unit": s.unit,
                        "rate_Hz": round(float(1 / np.median(np.diff(ts))), 1), "samples": int(ts.size)})
    return out