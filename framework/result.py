"""Simulation result: signals + metadata, with ASAM MDF (.mf4) I/O. No MATLAB dependency."""
import json
import html
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

UNITS = {
    "w_ref": "rad/s", "wm": "rad/s",
    "iq_ref": "A", "iq": "A", "iq_meas": "A", "id": "A",
    "ud": "V", "uq": "V",
    "Te": "Nm", "TL": "Nm",
}


@dataclass
class Result:
    test_name: str
    version: str
    param_file: str
    signals: dict[str, np.ndarray]
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def t(self) -> np.ndarray:
        return self.signals["t"]

    def __getitem__(self, name: str) -> np.ndarray:
        return self.signals[name]

    # ---------- ASAM MDF ----------
    def to_mf4(self, path: str | Path) -> Path:
        from asammdf import MDF, Signal

        meta = {"test_name": self.test_name, "version": self.version,
                "param_file": self.param_file, "created": self.created}
        mdf = MDF(version="4.10")
        mdf.header.comment = json.dumps(meta)        # metadata travels inside the file
        sigs = [Signal(samples=np.asarray(v, dtype=float), timestamps=self.t,
                       name=k, unit=UNITS.get(k, ""))
                for k, v in self.signals.items() if k != "t"]
        mdf.append(sigs, comment=self.test_name)
        mdf.save(path, overwrite=True)
        mdf.close()
        return Path(path)

    @classmethod
    def from_mf4(cls, path: str | Path) -> "Result":
        from asammdf import MDF

        with MDF(path) as mdf:
            txt = html.unescape(mdf.header.comment)                # may come back wrapped in XML
            meta = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
            signals, t = {}, None
            for name in UNITS:
                s = mdf.get(name)
                signals[name] = np.asarray(s.samples, dtype=float)
                t = np.asarray(s.timestamps, dtype=float)
        return cls(test_name=meta["test_name"], version=meta["version"],
                   param_file=meta["param_file"], signals={"t": t, **signals},
                   created=meta["created"])