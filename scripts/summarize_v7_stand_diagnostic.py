#!/usr/bin/env python3
"""Summarize repeated official MuJoCo G1 standing-settle trials."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


LIMITS = {
    "upright_min": (">=", 0.95),
    "joint_speed_peak_rad_s": ("<=", 2.5),
    "base_angular_speed_peak_rad_s": ("<=", 0.6),
}


def failed_metrics(payload: dict) -> list[str]:
    failures: list[str] = []
    for name, (operator, limit) in LIMITS.items():
        value = payload.get(name)
        if value is None:
            failures.append(f"missing:{name}")
        elif operator == ">=" and value < limit:
            failures.append(name)
        elif operator == "<=" and value > limit:
            failures.append(name)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    runs: list[dict] = []
    for run_dir in sorted(args.output_dir.glob("run_*")):
        result_path = run_dir / "initial_settle.json"
        result = json.loads(result_path.read_text()) if result_path.exists() else {}
        runs.append(
            {
                "run": run_dir.name,
                "settled": bool(result.get("settled")),
                "reason": result.get("reason", "missing_result"),
                "upright_min": result.get("upright_min"),
                "joint_speed_peak_rad_s": result.get("joint_speed_peak_rad_s"),
                "base_angular_speed_peak_rad_s": result.get("base_angular_speed_peak_rad_s"),
                "failed_metrics": failed_metrics(result),
            }
        )

    summary = {
        "runs": len(runs),
        "settled": sum(run["settled"] for run in runs),
        "criteria": LIMITS,
        "results": runs,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
