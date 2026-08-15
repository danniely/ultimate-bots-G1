#!/usr/bin/env python3
"""Summarize official C++ SONIC MuJoCo closed-loop regression runs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def read_csv(path: Path) -> list[list[str]]:
    with path.open(newline="") as handle:
        rows = list(csv.reader(handle))
    return rows[1:]


def up_component(row: list[str]) -> float:
    _, x, y, _ = map(float, row[5:9])
    return 1.0 - 2.0 * (x * x + y * y)


def signal_array(path: Path) -> np.ndarray:
    return np.asarray([[float(value) for value in row[5:]] for row in read_csv(path)])


def summarize_run(run_dir: Path) -> dict[str, float | int | bool | str]:
    logs = run_dir / "logs"
    playing = read_csv(logs / "motion_playing.csv")
    quat = read_csv(logs / "base_quat.csv")
    active = [index for index, row in enumerate(playing) if float(row[5]) > 0.5]
    completed = "completed." in (run_dir / "deploy.log").read_text(errors="replace")
    if not active:
        return {"run": run_dir.name, "command_completed": completed, "has_motion": False}

    first, last = min(active), max(active)
    recovery_last = min(len(quat) - 1, last + 100)
    up = np.asarray([up_component(row) for row in quat])
    speed = np.abs(signal_array(logs / "dq.csv"))
    torque = np.abs(signal_array(logs / "motor_torque.csv"))
    motion_slice = slice(first, last + 1)
    return {
        "run": run_dir.name,
        "command_completed": completed,
        "has_motion": True,
        "motion_frames": last - first + 1,
        "upright_start": float(up[first]),
        "upright_motion_end": float(up[last]),
        "upright_after_2s": float(up[recovery_last]),
        "recovered_upright": bool(up[recovery_last] >= 0.8),
        "joint_speed_peak_rad_s": float(speed[motion_slice].max()),
        "joint_speed_p99_rad_s": float(np.quantile(speed[motion_slice], 0.99)),
        "torque_peak_nm": float(torque[motion_slice].max()),
        "torque_p99_nm": float(np.quantile(torque[motion_slice], 0.99)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix_dir", type=Path)
    args = parser.parse_args()
    runs = [summarize_run(path) for path in sorted(args.matrix_dir.glob("run_*"))]
    valid = [run for run in runs if run.get("has_motion")]
    summary = {
        "runs_requested": len(runs),
        "commands_completed": sum(bool(run.get("command_completed")) for run in runs),
        "motions_with_181_frames": sum(run.get("motion_frames") == 181 for run in valid),
        "recovered_upright_after_2s": sum(bool(run.get("recovered_upright")) for run in valid),
        "upright_motion_end_mean": float(np.mean([run["upright_motion_end"] for run in valid])),
        "upright_after_2s_mean": float(np.mean([run["upright_after_2s"] for run in valid])),
        "joint_speed_peak_max_rad_s": max(run["joint_speed_peak_rad_s"] for run in valid),
        "torque_peak_max_nm": max(run["torque_peak_nm"] for run in valid),
        "runs": runs,
    }
    (args.matrix_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    fieldnames = sorted({key for run in runs for key in run})
    with (args.matrix_dir / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(runs)

    print(json.dumps({key: value for key, value in summary.items() if key != "runs"}, indent=2))


if __name__ == "__main__":
    main()
