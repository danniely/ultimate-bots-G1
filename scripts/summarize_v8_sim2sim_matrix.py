#!/usr/bin/env python3
"""Summarize V8 official C++/MuJoCo closed-loop cross-validation."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


EXPECTED_FRAMES = 467
FINAL_HOLD_FRAMES = 75


def rows(path: Path) -> list[list[str]]:
    try:
        with path.open(newline="") as handle:
            return list(csv.reader(handle))[1:]
    except (FileNotFoundError, OSError):
        return []


def signal(path: Path) -> np.ndarray:
    data = rows(path)
    return np.asarray([[float(value) for value in row[5:]] for row in data]) if data else np.empty((0, 0))


def up_values(path: Path) -> np.ndarray:
    data = rows(path)
    return np.asarray([1.0 - 2.0 * (float(row[6]) ** 2 + float(row[7]) ** 2) for row in data])


def summarize_run(run_dir: Path) -> dict:
    logs = run_dir / "logs"
    playing = rows(logs / "motion_playing.csv")
    active = [index for index, row in enumerate(playing) if float(row[5]) > 0.5]
    completed = "completed." in (run_dir / "deploy.log").read_text(errors="replace")
    initial_path = run_dir / "initial_settle.json"
    initial = json.loads(initial_path.read_text()) if initial_path.exists() else {"settled": False}
    if not active:
        return {
            "run": run_dir.name,
            "initial_settled": bool(initial.get("settled")),
            "command_completed": completed,
            "has_motion": False,
        }

    first, last = min(active), max(active)
    up = up_values(logs / "base_quat.csv")
    joint_speed = np.abs(signal(logs / "dq.csv"))
    base_ang = signal(logs / "base_ang_vel.csv")
    torque = np.abs(signal(logs / "motor_torque.csv"))
    motion_count = last - first + 1
    final_first = max(first, last - FINAL_HOLD_FRAMES + 1)
    final_slice = slice(final_first, last + 1)
    motion_slice = slice(first, last + 1)
    final_base_ang_peak = float(np.linalg.norm(base_ang[final_slice, :3], axis=1).max())
    final_joint_peak = float(joint_speed[final_slice].max())
    final_upright_min = float(up[final_slice].min())
    final_stable = (
        final_upright_min >= 0.95
        and final_joint_peak <= 2.5
        and final_base_ang_peak <= 0.6
    )
    return {
        "run": run_dir.name,
        "initial_settled": bool(initial.get("settled")),
        "command_completed": completed,
        "has_motion": True,
        "motion_frames": motion_count,
        "full_motion": motion_count >= EXPECTED_FRAMES - 1,
        "final_stable": final_stable,
        "final_upright_min": final_upright_min,
        "final_joint_speed_peak_rad_s": final_joint_peak,
        "final_base_angular_speed_peak_rad_s": final_base_ang_peak,
        "motion_joint_speed_peak_rad_s": float(joint_speed[motion_slice].max()),
        "motion_torque_peak_nm": float(torque[motion_slice].max()),
        "motion_torque_p99_nm": float(np.quantile(torque[motion_slice], 0.99)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix_dir", type=Path)
    args = parser.parse_args()
    runs = [summarize_run(path) for path in sorted(args.matrix_dir.glob("run_*"))]
    valid = [run for run in runs if run.get("has_motion")]
    summary = {
        "runs_requested": len(runs),
        "initial_settled": sum(bool(run.get("initial_settled")) for run in runs),
        "commands_completed": sum(bool(run.get("command_completed")) for run in runs),
        "full_motions": sum(bool(run.get("full_motion")) for run in valid),
        "final_stable": sum(bool(run.get("final_stable")) for run in valid),
        "final_upright_min_mean": float(np.mean([run["final_upright_min"] for run in valid])) if valid else None,
        "final_joint_speed_peak_max_rad_s": max((run["final_joint_speed_peak_rad_s"] for run in valid), default=None),
        "final_base_angular_speed_peak_max_rad_s": max((run["final_base_angular_speed_peak_rad_s"] for run in valid), default=None),
        "motion_joint_speed_peak_max_rad_s": max((run["motion_joint_speed_peak_rad_s"] for run in valid), default=None),
        "motion_torque_peak_max_nm": max((run["motion_torque_peak_nm"] for run in valid), default=None),
        "runs": runs,
    }
    args.matrix_dir.mkdir(parents=True, exist_ok=True)
    (args.matrix_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "runs"}, indent=2))


if __name__ == "__main__":
    main()
