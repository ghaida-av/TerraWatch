"""python -m evals [--md PATH] [--json PATH]   (exit code 1 if any non-known scenario fails)"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.run import format_markdown, format_table, run_all, to_json  # noqa: E402

ap = argparse.ArgumentParser(prog="python -m evals")
ap.add_argument("--md", help="write a markdown report to this path")
ap.add_argument("--json", help="write machine-readable results to this path")
args = ap.parse_args()

results = run_all()
print(format_table(results))
if args.md:
    Path(args.md).write_text(format_markdown(results))
if args.json:
    Path(args.json).write_text(to_json(results))
fixed = [o.scenario.id for o in results if o.status == "FIXED"]
if fixed:
    print(f"\nNote: {', '.join(fixed)} now pass. Remove their known_issue in evals/scenarios.py.")
sys.exit(1 if any(o.status in ("FAIL", "FIXED") for o in results) else 0)
