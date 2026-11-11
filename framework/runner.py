"""Simulation runners. Only MatlabRunner needs MATLAB."""
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from .result import Result
from .testcase import TestCase

META_FIELDS = ("version", "param_file")


class SimulationRunner(ABC):
    @abstractmethod
    def run(self, tc: TestCase, param_file: str = "params_v1_0") -> Result: ...


class MatlabRunner(SimulationRunner):
    """Starts MATLAB once, runs many test cases. Use as a context manager."""

    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir)
        self.eng = None

    def __enter__(self):
        import matlab.engine          # imported here so CI without MATLAB can import this module
        self.eng = matlab.engine.start_matlab()
        self.eng.addpath(str(self.model_dir), nargout=0)
        return self

    def __exit__(self, *exc):
        if self.eng is not None:
            self.eng.quit()

    def run(self, tc: TestCase, param_file: str = "params_v1_0") -> Result:
        import matlab
        inp = {k: matlab.double(v) for k, v in tc.profiles().items()}
        inp["t_stop"] = tc.t_stop
        res = self.eng.run_model(inp, param_file, nargout=1)
        signals = {k: np.asarray(v).ravel() for k, v in res.items() if k not in META_FIELDS}
        return Result(test_name=tc.name, version=str(res["version"]),
                      param_file=str(res["param_file"]), signals=signals)