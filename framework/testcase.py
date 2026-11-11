"""Test case definition, loaded from YAML. No MATLAB dependency."""
from dataclasses import dataclass
from pathlib import Path

import yaml

Profile = list[list[float]]
INPUTS = ("w_ref", "TL", "iq_offset")   # YAML key -> MATLAB variable <key>_in


def _to_profile(spec, t_stop: float) -> Profile:
    """Convert a YAML input spec into a [time, value] table."""
    if spec is None:
        spec = 0
    if isinstance(spec, (int, float)):
        return [[0.0, float(spec)], [t_stop, float(spec)]]
    kind = spec.get("type")
    if kind == "step":
        t, a, b = float(spec["time"]), float(spec.get("initial", 0)), float(spec["final"])
        return [[0.0, a], [t, a], [t, b], [t_stop, b]]
    if kind == "points":
        return [[float(t), float(v)] for t, v in spec["points"]]
    raise ValueError(f"Unknown input type: {kind!r}")


@dataclass
class TestCase:
    __test__ = False
    name: str
    description: str
    t_stop: float
    inputs: dict

    @classmethod
    def from_yaml(cls, path: str | Path) -> "TestCase":
        with open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f)
        return cls(name=d["name"], description=d.get("description", ""),
                   t_stop=float(d["t_stop"]), inputs=d.get("inputs", {}))

    def profiles(self) -> dict[str, Profile]:
        """Input tables keyed by the MATLAB variable names."""
        return {f"{k}_in": _to_profile(self.inputs.get(k), self.t_stop) for k in INPUTS}