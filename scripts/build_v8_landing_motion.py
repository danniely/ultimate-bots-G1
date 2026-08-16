#!/usr/bin/env python3
"""Build V8 by slowing touchdown and recovery while preserving every key pose."""

from __future__ import annotations

import argparse
from pathlib import Path

from build_v7_retimed_motion import (
    angular_velocity,
    finite_difference,
    read_csv,
    slerp,
    lerp,
    write_csv,
)


FPS = 50.0
LANDING_START = 167
LANDING_END = 210
RECOVERY_END = 258
LANDING_FACTOR = 3
RECOVERY_FACTOR = 2


def piecewise_retime(rows: list[list[float]], quaternion: bool = False) -> list[list[float]]:
    sampler = slerp if quaternion else lerp
    output: list[list[float]] = []
    for frame in range(len(rows) - 1):
        if LANDING_START <= frame < LANDING_END:
            factor = LANDING_FACTOR
        elif LANDING_END <= frame < RECOVERY_END:
            factor = RECOVERY_FACTOR
        else:
            factor = 1
        for substep in range(factor):
            output.append(sampler(rows[frame], rows[frame + 1], substep / factor))
    output.append(rows[-1].copy())
    return output


def build(source: Path, destination: Path) -> None:
    joint_header, joints_in = read_csv(source / "joint_pos.csv")
    pos_header, positions_in = read_csv(source / "body_pos.csv")
    quat_header, quaternions_in = read_csv(source / "body_quat.csv")
    if {len(joints_in), len(positions_in), len(quaternions_in)} != {333}:
        raise ValueError("V8 expects the 333-frame V7 targeted motion")

    joints = piecewise_retime(joints_in)
    positions = piecewise_retime(positions_in)
    quaternions = piecewise_retime(quaternions_in, quaternion=True)
    joint_velocities = finite_difference(joints)
    linear_velocities = finite_difference(positions)
    angular_velocities = [[0.0, 0.0, 0.0]] + [
        angular_velocity(previous, current)
        for previous, current in zip(quaternions, quaternions[1:])
    ]

    destination.mkdir(parents=True, exist_ok=True)
    write_csv(destination / "joint_pos.csv", joint_header, joints)
    write_csv(destination / "joint_vel.csv", [f"joint_{i}_vel" for i in range(29)], joint_velocities)
    write_csv(destination / "body_pos.csv", pos_header, positions)
    write_csv(destination / "body_quat.csv", quat_header, quaternions)
    write_csv(destination / "body_lin_vel.csv", ["body_0_vx", "body_0_vy", "body_0_vz"], linear_velocities)
    write_csv(destination / "body_ang_vel.csv", ["body_0_wx", "body_0_wy", "body_0_wz"], angular_velocities)

    destination.joinpath("info.txt").write_text(
        "Motion Information: s_batido_v8_landing\n"
        "========================================\n\n"
        "fps: 50\nsource_frames: 333\ntarget_frames: 467\n"
        "landing_source_frames: 167:210\nlanding_factor: 3\n"
        "recovery_source_frames: 210:258\nrecovery_factor: 2\n"
        "highlight_end_frame: 167\nlanding_end_frame: 296\n"
        "recovery_start_frame: 215\nfinal_hold_start_frame: 392\n",
        encoding="utf-8",
    )
    destination.joinpath("metadata.txt").write_text(
        "Metadata for: s_batido_v8_landing\n"
        "========================================\n\n"
        "Body part indexes:\n[ 0]\n\nTotal timesteps: 467\n",
        encoding="utf-8",
    )
    peak_joint = max(abs(value) for row in joint_velocities for value in row)
    peak_angular = max(sum(value * value for value in row) ** 0.5 for row in angular_velocities)
    print(f"frames={len(joints)} max_joint_speed={peak_joint:.6f} max_body_angular_speed={peak_angular:.6f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    build(args.source, args.destination)


if __name__ == "__main__":
    main()
