"""Run all YAML test cases against one model release."""
import time
from pathlib import Path

from .runner import MatlabRunner
from .testcase import TestCase

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    cases = [TestCase.from_yaml(p) for p in sorted((ROOT / "testcases").glob("*.yaml"))]
    print(f"Found {len(cases)} test cases")
    with MatlabRunner(ROOT / "model") as runner:
        for tc in cases:
            t0 = time.time()
            r = runner.run(tc)
            print(f"{tc.name:<24} {time.time() - t0:5.1f} s   "
                  f"final wm = {r['wm'][-1]:6.2f} rad/s   max iq = {r['iq'].max():6.1f} A")