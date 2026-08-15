#!/usr/bin/env python3
"""Summarize hardware-relevant signals from a frame-recorder CSV."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import statistics


def finite(value: str) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lo = math.floor(index)
    hi = math.ceil(index)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - index) + ordered[hi] * (index - lo)


def vector_norm(row: dict[str, str], columns: tuple[str, str, str]) -> float:
    values = [finite(row.get(column, "")) or 0.0 for column in columns]
    return math.sqrt(sum(value * value for value in values))


def contact_groups(header: list[str]) -> dict[str, list[tuple[str, str, str]]]:
    body_axes: dict[str, dict[str, str]] = {}
    for column in header:
        if not column.startswith("contact_force_w."):
            continue
        stem, axis = column.rsplit(".", 1)
        body = stem.removeprefix("contact_force_w.")
        body_axes.setdefault(body, {})[axis] = column

    groups = {"wrist_hand": [], "feet_ankles": [], "other": []}
    for body, axes in body_axes.items():
        if not all(axis in axes for axis in "xyz"):
            continue
        vector = (axes["x"], axes["y"], axes["z"])
        if any(token in body for token in ("wrist", "hand", "palm")):
            groups["wrist_hand"].append(vector)
        elif any(token in body for token in ("FOOT", "ankle")):
            groups["feet_ankles"].append(vector)
        else:
            groups["other"].append(vector)
    return groups


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with args.csv_file.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames or []
        rows = list(reader)
    if not rows:
        raise ValueError(f"No frame rows in {args.csv_file}")

    torque_columns = [column for column in header if column.startswith("applied_torque.")]
    velocity_columns = [column for column in header if column.startswith("actual_joint_vel.")]
    groups = contact_groups(header)

    torque_abs: list[float] = []
    velocity_abs: list[float] = []
    accelerations: list[float] = []
    contacts = {name: [] for name in groups}
    max_torque = {"value": -1.0, "frame": None, "joint": None}
    max_velocity = {"value": -1.0, "frame": None, "joint": None}
    previous_velocity: dict[str, float] = {}

    for frame_index, row in enumerate(rows):
        frame = int(finite(row.get("motion_frame", "")) or frame_index)
        for column in torque_columns:
            value = abs(finite(row.get(column, "")) or 0.0)
            torque_abs.append(value)
            if value > max_torque["value"]:
                max_torque = {
                    "value": value,
                    "frame": frame,
                    "joint": column.removeprefix("applied_torque."),
                }
        for column in velocity_columns:
            signed = finite(row.get(column, "")) or 0.0
            value = abs(signed)
            velocity_abs.append(value)
            if value > max_velocity["value"]:
                max_velocity = {
                    "value": value,
                    "frame": frame,
                    "joint": column.removeprefix("actual_joint_vel."),
                }
            if column in previous_velocity:
                accelerations.append(abs(signed - previous_velocity[column]) * args.fps)
            previous_velocity[column] = signed
        for name, vectors in groups.items():
            contacts[name].append(max((vector_norm(row, vector) for vector in vectors), default=0.0))

    termination_columns = [column for column in header if column.startswith("termination_flags.")]
    triggered = {
        column.removeprefix("termination_flags."): sum(
            1 for row in rows if (finite(row.get(column, "")) or 0.0) > 0.5
        )
        for column in termination_columns
    }

    summary = {
        "source": str(args.csv_file),
        "frames": len(rows),
        "fps": args.fps,
        "last_motion_frame": int(finite(rows[-1].get("motion_frame", "")) or len(rows) - 1),
        "torque_nm": {
            "peak": max_torque,
            "p99_abs": percentile(torque_abs, 0.99),
            "rms": math.sqrt(statistics.fmean(value * value for value in torque_abs)),
        },
        "joint_velocity_rad_s": {
            "peak": max_velocity,
            "p99_abs": percentile(velocity_abs, 0.99),
            "rms": math.sqrt(statistics.fmean(value * value for value in velocity_abs)),
        },
        "joint_acceleration_rad_s2": {
            "peak_abs": max(accelerations, default=None),
            "p99_abs": percentile(accelerations, 0.99),
        },
        "contact_force_n": {
            name: {
                "peak": max(values, default=0.0),
                "p99": percentile(values, 0.99),
                "mean": statistics.fmean(values) if values else None,
            }
            for name, values in contacts.items()
        },
        "termination_frame_counts": triggered,
    }

    output = args.output or args.csv_file.with_name(args.csv_file.stem + "_hardware_risk.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

