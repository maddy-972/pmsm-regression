"""Smoke test: run one simulation of the FOC model from Python."""
import time
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matlab.engine

MODEL_DIR = Path(__file__).resolve().parents[1] / "model"

# Test inputs as [time, value] tables -> matlab.double matrices
inp = {
    "w_ref_in":     matlab.double([[0, 0], [0.01, 0], [0.01, 50], [1, 50]]),
    "TL_in":        matlab.double([[0, 0], [0.5, 0], [0.5, 50], [1, 50]]),
    "iq_offset_in": matlab.double([[0, 0], [1, 0]]),
    "t_stop":       1.0,
}

t0 = time.time()
eng = matlab.engine.start_matlab()
eng.addpath(str(MODEL_DIR), nargout=0)
print(f"MATLAB started in {time.time() - t0:.1f} s")

t0 = time.time()
res = eng.run_model(inp, nargout=1)     # Python dict -> MATLAB struct -> dict
print(f"Simulation took {time.time() - t0:.1f} s")
eng.quit()

# matlab.double -> numpy
sig = {k: np.asarray(v).ravel() for k, v in res.items()
       if k not in ("version", "param_file")}

print("Signals:", list(sig.keys()))
print("Samples:", sig["t"].size)
print(f"Final speed: {sig['wm'][-1]:.2f} rad/s")
print("Model version:", res["version"], "| params:", res["param_file"])

plt.plot(sig["t"], sig["w_ref"], label="w_ref")
plt.plot(sig["t"], sig["wm"], label="wm")
plt.xlabel("t / s"); plt.ylabel("rad/s"); plt.grid(); plt.legend()
plt.show()