#!/usr/bin/env python3
"""Summarize landing, recovery, and final-hold hardware signals for V8."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import statistics


PHASES = {
    "landing": (168, 296),
    "recovery": (297, 391),
    "final_hold": (392, 466),
}


def number(row: dict[str, str], column: str) -> float:
    try:
        value = float(row.get(column, "0"))
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) else 0.0


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lo, hi = math.floor(index), math.ceil(index)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - index) + ordered[hi] * (index - lo)


def stats(values: list[float]) -> dict[str, float | None]:
    return {
        "peak": max(values, default=None),
        "p99": percentile(values, 0.99),
        "rms": math.sqrt(statistics.fmean(v * v for v in values)) if values else None,
    }


def vector_norm(row: dict[str, str], prefix: str) -> float:
    return math.sqrt(sum(number(row, f"{prefix}.{axis}") ** 2 for axis in "xyz"))


def phase_summary(rows: list[dict[str, str]], header: list[str]) -> dict[str, object]:
    velocity_columns = [c for c in header if c.startswith("actual_joint_vel.")]
    torque_columns = [c for c in header if c.startswith("applied_torque.")]
    foot_bodies = (
        "left_ankle_pitch_link", "left_ankle_roll_link", "LL_FOOT",
        "right_ankle_pitch_link", "right_ankle_roll_link", "LR_FOOT",
    )
    joint_velocity = [abs(number(row, c)) for row in rows for c in velocity_columns]
    torque = [abs(number(row, c)) for row in rows for c in torque_columns]
    foot_contact = [
        max(vector_norm(row, f"contact_force_w.{body}") for body in foot_bodies)
        for row in rows
    ]
    pelvis_speed_xy = [
        math.hypot(
            number(row, "actual_pelvis_lin_vel_w.0"),
            number(row, "actual_pelvis_lin_vel_w.1"),
        )
        for row in rows
    ]
    capture_point_error = []
    for row in rows:
        z = max(number(row, "actual_pelvis_pos_w.2"), 0.0)
        horizon = math.sqrt(z / 9.81)
        capture_x = number(row, "actual_pelvis_pos_w.0") + horizon * number(
            row, "actual_pelvis_lin_vel_w.0"
        )
        capture_y = number(row, "actual_pelvis_pos_w.1") + horizon * number(
            row, "actual_pelvis_lin_vel_w.1"
        )
        support_x = 0.5 * (
            number(row, "actual_body_pos_w.left_ankle_roll_link.x")
            + number(row, "actual_body_pos_w.right_ankle_roll_link.x")
        )
        support_y = 0.5 * (
            number(row, "actual_body_pos_w.left_ankle_roll_link.y")
            + number(row, "actual_body_pos_w.right_ankle_roll_link.y")
        )
        capture_point_error.append(math.hypot(capture_x - support_x, capture_y - support_y))
    return {
        "samples": len(rows),
        "joint_velocity_rad_s": stats(joint_velocity),
        "torque_nm": stats(torque),
        "foot_contact_force_n": stats(foot_contact),
        "pelvis_horizontal_speed_m_s": stats(pelvis_speed_xy),
        "capture_point_to_ankle_midpoint_m": stats(capture_point_error),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with args.csv_file.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        header = reader.fieldnames or []
    result = {"source": str(args.csv_file), "phases": {}}
    for phase, (start, end) in PHASES.items():
        selected = [row for row in rows if start <= int(number(row, "motion_frame")) <= end]
        result["phases"][phase] = phase_summary(selected, header)
    output = args.output or args.csv_file.with_name(args.csv_file.stem + "_v8_phase_risk.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
