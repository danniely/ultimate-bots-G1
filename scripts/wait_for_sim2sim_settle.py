#!/usr/bin/env python3
"""Wait until the deployed G1 is upright and quiet before starting a motion."""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path


def numeric_rows(path: Path) -> list[list[float]]:
    try:
        with path.open(newline="") as handle:
            rows = list(csv.reader(handle))[1:]
    except (FileNotFoundError, OSError):
        return []
    parsed: list[list[float]] = []
    for row in rows:
        try:
            parsed.append([float(value) for value in row[5:]])
        except (ValueError, IndexError):
            continue
    return parsed


def up_component(quaternion: list[float]) -> float:
    _, x, y, _ = quaternion[:4]
    return 1.0 - 2.0 * (x * x + y * y)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("logs", type=Path)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--consecutive", type=int, default=25)
    parser.add_argument("--min-upright", type=float, default=0.95)
    parser.add_argument("--max-joint-speed", type=float, default=2.5)
    parser.add_argument("--max-base-angular-speed", type=float, default=0.6)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    deadline = time.monotonic() + args.timeout
    result: dict[str, float | int | bool | str] = {"settled": False}
    while time.monotonic() < deadline:
        quats = numeric_rows(args.logs / "base_quat.csv")
        joint_vel = numeric_rows(args.logs / "dq.csv")
        base_ang_vel = numeric_rows(args.logs / "base_ang_vel.csv")
        available = min(len(quats), len(joint_vel), len(base_ang_vel))
        if available >= args.consecutive:
            start = available - args.consecutive
            ups = [up_component(row) for row in quats[start:available]]
            joint_peak = max(abs(value) for row in joint_vel[start:available] for value in row)
            angular_peak = max(
                math.sqrt(sum(value * value for value in row[:3]))
                for row in base_ang_vel[start:available]
            )
            result = {
                "settled": min(ups) >= args.min_upright
                and joint_peak <= args.max_joint_speed
                and angular_peak <= args.max_base_angular_speed,
                "samples": args.consecutive,
                "upright_min": min(ups),
                "joint_speed_peak_rad_s": joint_peak,
                "base_angular_speed_peak_rad_s": angular_peak,
            }
            if result["settled"]:
                break
        time.sleep(0.2)

    result["reason"] = "stable_window" if result.get("settled") else "timeout"
    payload = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload)
    print(payload, end="")
    return 0 if result.get("settled") else 2


if __name__ == "__main__":
    raise SystemExit(main())
