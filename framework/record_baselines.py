"""Record golden baselines: run all test cases on one release and save as .mf4."""
import argparse
from pathlib import Path

from .runner import MatlabRunner
from .testcase import TestCase

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params_v1_0")
    ap.add_argument("--force", action="store_true", help="overwrite existing baselines")
    args = ap.parse_args()

    cases = [TestCase.from_yaml(p) for p in sorted((ROOT / "testcases").glob("*.yaml"))]
    with MatlabRunner(ROOT / "model") as runner:
                for tc in cases:
            out = ROOT / "baselines" / "v1.0" / f"{tc.name}.mf4"
            if out.exists() and not args.force:
                print(f"SKIP {out.name} (exists, use --force to overwrite)")
                continue
            r = runner.run(tc, args.params)
            out = ROOT / "baselines" / f"v{r.version}" / f"{tc.name}.mf4"
            out.parent.mkdir(parents=True, exist_ok=True)
            r.to_mf4(out)
            print(f"saved {out.relative_to(ROOT)}  ({out.stat().st_size / 1024:.0f} kB)")