"""Validate a model release against golden baselines. Exit code 1 if anything fails."""
import argparse
import sys
from contextlib import nullcontext
from pathlib import Path

from .regression import evaluate
from .result import Result
from .runner import MatlabRunner, Mf4ReplayRunner
from .testcase import TestCase

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params_v1_0", help="parameter file of the release under test")
    ap.add_argument("--baseline", default="v1.0", help="baseline folder in baselines/")
    ap.add_argument("--replay", help="folder of recorded .mf4 runs (no MATLAB)")
    args = ap.parse_args()

    cases = [TestCase.from_yaml(p) for p in sorted((ROOT / "testcases").glob("*.yaml"))]
    base_dir = ROOT / "baselines" / args.baseline
    runner_cm = nullcontext(Mf4ReplayRunner(args.replay)) if args.replay else MatlabRunner(ROOT / "model")

    reports = []
    with runner_cm as runner:
        for tc in cases:
            run = runner.run(tc, args.params)
            if not args.replay:                                   # keep the run for the report
                p = ROOT / "reports" / "runs" / f"v{run.version}" / f"{tc.name}.mf4"
                p.parent.mkdir(parents=True, exist_ok=True)
                run.to_mf4(p)
            reports.append(evaluate(tc, run, Result.from_mf4(base_dir / f"{tc.name}.mf4")))

    for rep in reports:
        print(f"\n{rep.test_name}  [{'PASS' if rep.passed else 'FAIL'}]  "
              f"v{rep.version} vs baseline v{rep.baseline_version}")
        for c in rep.checks:
            print(f"  {c.kind:<4} {c.name:<16} {c.value:10.4g} {c.unit:<6} <= {c.limit:<8g} "
                  f"{'PASS' if c.passed else 'FAIL'}")

    n_fail = sum(not r.passed for r in reports)
    print(f"\n{len(reports) - n_fail}/{len(reports)} test cases passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())