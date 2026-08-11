#!/usr/bin/env python3
"""Append a reproducible two-second balance-recovery tail to SONIC CSV motion.

The original 81 frames remain byte-for-byte numerically unchanged. The first
half of the appended tail eases from the final landing pose toward the motion's
initial standing pose. The second half holds that stable pose. Horizontal root
position is kept at the landing location and the target pelvis is upright while
preserving its final yaw, avoiding a teleport back to the motion origin.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


FPS = 50.0
SIGNAL_FILES = (
    "body_pos.csv",
    "body_quat.csv",
    "body_lin_vel.csv",
    "body_ang_vel.csv",
    "joint_pos.csv",
    "joint_vel.csv",
)


def read_csv(path: Path) -> tuple[list[str], list[list[float]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    return rows[0], [[float(value) for value in row] for row in rows[1:]]


def write_csv(path: Path, header: list[str], rows: list[list[float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows([[f"{value:.6f}" for value in row] for row in rows])


def smoothstep5(value: float) -> float:
    return value**3 * (10.0 - 15.0 * value + 6.0 * value * value)


def normalize(quaternion: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in quaternion))
    return [value / norm for value in quaternion]


def slerp(left: list[float], right: list[float], amount: float) -> list[float]:
    left = normalize(left)
    right = normalize(right)
    dot = sum(a * b for a, b in zip(left, right))
    if dot < 0.0:
        right = [-value for value in right]
        dot = -dot
    if dot > 0.9995:
        return normalize([a + amount * (b - a) for a, b in zip(left, right)])
    theta = math.acos(max(-1.0, min(1.0, dot)))
    scale_left = math.sin((1.0 - amount) * theta) / math.sin(theta)
    scale_right = math.sin(amount * theta) / math.sin(theta)
    return [scale_left * a + scale_right * b for a, b in zip(left, right)]


def yaw_only(quaternion: list[float]) -> list[float]:
    w, x, y, z = normalize(quaternion)
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    return [math.cos(yaw / 2.0), 0.0, 0.0, math.sin(yaw / 2.0)]


def subtract(left: list[float], right: list[float]) -> list[float]:
    return [a - b for a, b in zip(left, right)]


def scale(values: list[float], factor: float) -> list[float]:
    return [value * factor for value in values]


def quaternion_conjugate(value: list[float]) -> list[float]:
    return [value[0], -value[1], -value[2], -value[3]]


def quaternion_multiply(left: list[float], right: list[float]) -> list[float]:
    lw, lx, ly, lz = left
    rw, rx, ry, rz = right
    return [
        lw * rw - lx * rx - ly * ry - lz * rz,
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
    ]


def angular_velocity(previous: list[float], current: list[float]) -> list[float]:
    delta = normalize(quaternion_multiply(current, quaternion_conjugate(previous)))
    if delta[0] < 0.0:
        delta = [-value for value in delta]
    vector_norm = math.sqrt(sum(value * value for value in delta[1:]))
    if vector_norm < 1.0e-9:
        return [0.0, 0.0, 0.0]
    angle = 2.0 * math.atan2(vector_norm, max(1.0e-9, delta[0]))
    return [value / vector_norm * angle * FPS for value in delta[1:]]


def build(source: Path, destination: Path, recovery_seconds: float) -> None:
    loaded = {name: read_csv(source / name) for name in SIGNAL_FILES}
    frame_counts = {len(rows) for _, rows in loaded.values()}
    if len(frame_counts) != 1:
        raise ValueError(f"Mismatched source frame counts: {sorted(frame_counts)}")

    source_frames = frame_counts.pop()
    recovery_frames = round(recovery_seconds * FPS)
    transition_frames = recovery_frames // 2
    hold_frames = recovery_frames - transition_frames

    joint_header, joint_rows = loaded["joint_pos.csv"]
    pos_header, pos_rows = loaded["body_pos.csv"]
    quat_header, quat_rows = loaded["body_quat.csv"]
    target_joint = joint_rows[0]
    target_pos = [pos_rows[-1][0], pos_rows[-1][1], pos_rows[0][2]]
    target_quat = yaw_only(quat_rows[-1])

    appended_joints: list[list[float]] = []
    appended_positions: list[list[float]] = []
    appended_quaternions: list[list[float]] = []
    for index in range(1, transition_frames + 1):
        amount = smoothstep5(index / transition_frames)
        appended_joints.append(
            [start + amount * (end - start) for start, end in zip(joint_rows[-1], target_joint)]
        )
        appended_positions.append(
            [start + amount * (end - start) for start, end in zip(pos_rows[-1], target_pos)]
        )
        appended_quaternions.append(slerp(quat_rows[-1], target_quat, amount))
    appended_joints.extend([target_joint.copy() for _ in range(hold_frames)])
    appended_positions.extend([target_pos.copy() for _ in range(hold_frames)])
    appended_quaternions.extend([target_quat.copy() for _ in range(hold_frames)])

    full_joints = joint_rows + appended_joints
    full_positions = pos_rows + appended_positions
    full_quaternions = quat_rows + appended_quaternions

    tail_joint_velocities = [
        scale(subtract(full_joints[index], full_joints[index - 1]), FPS)
        for index in range(source_frames, len(full_joints))
    ]
    tail_linear_velocities = [
        scale(subtract(full_positions[index], full_positions[index - 1]), FPS)
        for index in range(source_frames, len(full_positions))
    ]
    tail_angular_velocities = [
        angular_velocity(full_quaternions[index - 1], full_quaternions[index])
        for index in range(source_frames, len(full_quaternions))
    ]

    destination.mkdir(parents=True, exist_ok=True)
    write_csv(destination / "joint_pos.csv", joint_header, full_joints)
    write_csv(destination / "body_pos.csv", pos_header, full_positions)
    write_csv(destination / "body_quat.csv", quat_header, full_quaternions)
    write_csv(
        destination / "joint_vel.csv",
        loaded["joint_vel.csv"][0],
        loaded["joint_vel.csv"][1] + tail_joint_velocities,
    )
    write_csv(
        destination / "body_lin_vel.csv",
        loaded["body_lin_vel.csv"][0],
        loaded["body_lin_vel.csv"][1] + tail_linear_velocities,
    )
    write_csv(
        destination / "body_ang_vel.csv",
        loaded["body_ang_vel.csv"][0],
        loaded["body_ang_vel.csv"][1] + tail_angular_velocities,
    )
    (destination / "info.txt").write_text(
        "Motion Information: s_batido_v3_recovery\n"
        "==================================================\n\n"
        f"source_fps: {int(FPS)}\n"
        f"target_fps: {int(FPS)}\n"
        f"source_frames: {source_frames}\n"
        f"target_frames: {len(full_joints)}\n"
        f"recovery_frames: {recovery_frames}\n"
        f"recovery_seconds: {recovery_seconds:.2f}\n"
        f"transition_frames: {transition_frames}\n"
        f"hold_frames: {hold_frames}\n",
        encoding="utf-8",
    )
    (destination / "metadata.txt").write_text(
        "Metadata for: s_batido_v3_recovery\n"
        "========================================\n\n"
        "Body part indexes:\n[ 0]\n\n"
        f"Total timesteps: {len(full_joints)}\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--recovery-seconds", type=float, default=2.0)
    args = parser.parse_args()
    build(args.source, args.destination, args.recovery_seconds)


if __name__ == "__main__":
    main()
