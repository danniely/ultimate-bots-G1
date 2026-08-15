#!/usr/bin/env python3
"""Summarize SONIC im_eval logs without depending on pandas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import statistics


FLOAT = r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"


def last_float(pattern: str, text: str) -> float | None:
    matches = re.findall(pattern, text)
    return float(matches[-1]) if matches else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    args.run_root.mkdir(parents=True, exist_ok=True)

    profiles: dict[str, list[dict[str, float | str | None]]] = {}
    for log in sorted(args.run_root.glob("*/seed_*.log")):
        text = log.read_text(encoding="utf-8", errors="replace")
        result = {
            "seed": log.stem.removeprefix("seed_"),
            "success_rate": last_float(r"Success Rate:\s*" + FLOAT, text),
            "progress_rate": last_float(r"Progress Rate:\s*" + FLOAT, text),
            "mpjpe_global_mm": last_float(r"All:\s+mpjpe_g:\s*" + FLOAT, text),
            "mpjpe_local_mm": last_float(r"All:.*?mpjpe_l:\s*" + FLOAT, text),
            "acceleration_distance": last_float(r"All:.*?accel_dist:\s*" + FLOAT, text),
            "velocity_distance": last_float(r"All:.*?vel_dist:\s*" + FLOAT, text),
        }
        profiles.setdefault(log.parent.name, []).append(result)

    summary: dict[str, dict] = {}
    for profile, runs in profiles.items():
        aggregate = {"runs": len(runs), "seeds": runs}
        for key in (
            "success_rate",
            "progress_rate",
            "mpjpe_global_mm",
            "mpjpe_local_mm",
            "acceleration_distance",
            "velocity_distance",
        ):
            values = [r[key] for r in runs if r[key] is not None]
            aggregate[f"mean_{key}"] = statistics.fmean(values) if values else None
            aggregate[f"min_{key}"] = min(values) if values else None
            aggregate[f"max_{key}"] = max(values) if values else None
        summary[profile] = aggregate

    output = args.run_root / "summary.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    lines = ["# v3 strict robustness matrix", ""]
    lines.append("| Profile | Runs | Mean success | Mean progress | Mean local MPJPE |")
    lines.append("|---|---:|---:|---:|---:|")
    for profile, values in summary.items():
        def fmt(key: str, digits: int = 3) -> str:
            value = values.get(key)
            return "n/a" if value is None else f"{value:.{digits}f}"

        lines.append(
            f"| {profile} | {values['runs']} | {fmt('mean_success_rate')} | "
            f"{fmt('mean_progress_rate')} | {fmt('mean_mpjpe_local_mm', 1)} mm |"
        )
    (args.run_root / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
