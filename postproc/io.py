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