"""Simulation result: signals + metadata. No MATLAB dependency."""
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np


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