#!/usr/bin/env python3
"""Build a deployment-friendly buffered SONIC motion for V6.

Timeline at 50 Hz:

* hold the exact G1 deployment standing pose;
* ease from that pose to the source motion's first pose;
* time-warp the first source frames so motion velocity ramps up from zero;
* preserve the remainder of the original 81-frame capoeira motion;
* ease back to the exact deployment standing pose at the landing location/yaw;
* hold the final standing pose.

All velocities are recomputed from the generated positions and quaternions so
the policy never receives a dynamic frame paired with a zero-velocity body (or
the reverse) at a splice boundary.
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
    "joint_pos.csv",
)

# G1 deployment standing angles in MuJoCo/hardware order.
DEFAULT_ANGLES_MUJOCO = [
    -0.312, 0.0, 0.0, 0.669, -0.363, 0.0,
    -0.312, 0.0, 0.0, 0.669, -0.363, 0.0,
    0.0, 0.0, 0.0,
    0.2, 0.2, 0.0, 0.6, 0.0, 0.0, 0.0,
    0.2, -0.2, 0.0, 0.6, 0.0, 0.0, 0.0,
]

# Hardware index -> IsaacLab index, from the official deployment mapping.
MUJOCO_TO_ISAACLAB = [
    0, 6, 12, 1, 7, 13, 2, 8, 14, 3, 9, 15, 22, 4, 10,
    16, 23, 5, 11, 17, 24, 18, 25, 19, 26, 20, 27, 21, 28,
]


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


def yaw_quaternion(quaternion: list[float]) -> list[float]:
    w, x, y, z = normalize(quaternion)
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    return [math.cos(yaw / 2.0), 0.0, 0.0, math.sin(yaw / 2.0)]


def lerp(left: list[float], right: list[float], amount: float) -> list[float]:
    return [a + amount * (b - a) for a, b in zip(left, right)]


def sample_linear(rows: list[list[float]], phase: float) -> list[float]:
    lower = min(int(math.floor(phase)), len(rows) - 1)
    upper = min(lower + 1, len(rows) - 1)
    return lerp(rows[lower], rows[upper], phase - lower)


def sample_quaternion(rows: list[list[float]], phase: float) -> list[float]:
    lower = min(int(math.floor(phase)), len(rows) - 1)
    upper = min(lower + 1, len(rows) - 1)
    return slerp(rows[lower], rows[upper], phase - lower)


def deployment_joint_pose_isaaclab() -> list[float]:
    result = [0.0] * len(DEFAULT_ANGLES_MUJOCO)
    for mujoco_index, isaac_index in enumerate(MUJOCO_TO_ISAACLAB):
        result[isaac_index] = DEFAULT_ANGLES_MUJOCO[mujoco_index]
    return result


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


def quaternion_power(value: list[float], amount: float) -> list[float]:
    value = normalize(value)
    if value[0] < 0.0:
        value = [-component for component in value]
    vector_norm = math.sqrt(sum(component * component for component in value[1:]))
    if vector_norm < 1.0e-10:
        return [1.0, 0.0, 0.0, 0.0]
    half_angle = math.atan2(vector_norm, value[0]) * amount
    scale = math.sin(half_angle) / vector_norm
    return normalize([math.cos(half_angle)] + [component * scale for component in value[1:]])


def angular_velocity(previous: list[float], current: list[float]) -> list[float]:
    delta = normalize(quaternion_multiply(current, quaternion_conjugate(previous)))
    if delta[0] < 0.0:
        delta = [-value for value in delta]
    vector_norm = math.sqrt(sum(value * value for value in delta[1:]))
    if vector_norm < 1.0e-10:
        return [0.0, 0.0, 0.0]
    angle = 2.0 * math.atan2(vector_norm, max(1.0e-10, delta[0]))
    return [value / vector_norm * angle * FPS for value in delta[1:]]


def finite_difference(rows: list[list[float]]) -> list[list[float]]:
    velocities = [[0.0] * len(rows[0])]
    for previous, current in zip(rows, rows[1:]):
        velocities.append([(b - a) * FPS for a, b in zip(previous, current)])
    return velocities


def build(
    source: Path,
    destination: Path,
    hold_frames: int,
    approach_frames: int,
    launch_frames: int,
    launch_source_end: int,
    recovery_frames: int,
    recovery_coast_frames: int,
    final_hold_frames: int,
) -> None:
    loaded = {name: read_csv(source / name) for name in SIGNAL_FILES}
    frame_counts = {len(rows) for _, rows in loaded.values()}
    if len(frame_counts) != 1:
        raise ValueError(f"Mismatched source frame counts: {sorted(frame_counts)}")
    source_frames = frame_counts.pop()
    if launch_source_end <= 0 or launch_source_end >= source_frames - 1:
        raise ValueError("launch_source_end must be inside the source motion")

    joint_header, source_joints = loaded["joint_pos.csv"]
    pos_header, source_positions = loaded["body_pos.csv"]
    quat_header, source_quaternions = loaded["body_quat.csv"]

    standing_joint = deployment_joint_pose_isaaclab()
    standing_position = [0.0, 0.0, 0.76]
    standing_quaternion = [1.0, 0.0, 0.0, 0.0]

    joints = [standing_joint.copy() for _ in range(hold_frames)]
    positions = [standing_position.copy() for _ in range(hold_frames)]
    quaternions = [standing_quaternion.copy() for _ in range(hold_frames)]

    for index in range(1, approach_frames + 1):
        amount = smoothstep5(index / approach_frames)
        joints.append(lerp(standing_joint, source_joints[0], amount))
        positions.append(lerp(standing_position, source_positions[0], amount))
        quaternions.append(slerp(standing_quaternion, source_quaternions[0], amount))

    # Cubic Hermite phase ramp: source phase and velocity are both continuous.
    # It starts with zero source-frame velocity and ends at one source frame per
    # generated frame, matching normal playback before the splice.
    duration = float(launch_frames - 1)
    end_phase = float(launch_source_end)
    for index in range(launch_frames):
        t = index / duration
        h01 = -2.0 * t**3 + 3.0 * t**2
        h11 = t**3 - t**2
        phase = h01 * end_phase + h11 * duration
        joints.append(sample_linear(source_joints, phase))
        positions.append(sample_linear(source_positions, phase))
        quaternions.append(sample_quaternion(source_quaternions, phase))

    joints.extend(row.copy() for row in source_joints[launch_source_end + 1 :])
    positions.extend(row.copy() for row in source_positions[launch_source_end + 1 :])
    quaternions.extend(row.copy() for row in source_quaternions[launch_source_end + 1 :])
    core_end_frame = len(joints) - 1

    if recovery_coast_frames < 0 or recovery_coast_frames >= recovery_frames:
        raise ValueError("recovery_coast_frames must be in [0, recovery_frames)")

    # First dissipate the final source-frame velocity instead of dropping it to
    # zero at the recovery splice. This removes the large target-velocity jerk
    # that was present in V3/V5 while keeping the coast bounded.
    last_joint_step = [b - a for a, b in zip(joints[-2], joints[-1])]
    last_position_step = [b - a for a, b in zip(positions[-2], positions[-1])]
    last_quaternion_step = normalize(
        quaternion_multiply(quaternions[-1], quaternion_conjugate(quaternions[-2]))
    )
    for index in range(1, recovery_coast_frames + 1):
        velocity_scale = 1.0 - index / (recovery_coast_frames + 1.0)
        joints.append(
            [value + velocity_scale * step for value, step in zip(joints[-1], last_joint_step)]
        )
        positions.append(
            [value + velocity_scale * step for value, step in zip(positions[-1], last_position_step)]
        )
        quaternions.append(
            normalize(
                quaternion_multiply(
                    quaternion_power(last_quaternion_step, velocity_scale), quaternions[-1]
                )
            )
        )

    transition_start_joint = joints[-1].copy()
    transition_start_position = positions[-1].copy()
    transition_start_quaternion = quaternions[-1].copy()
    final_position = [transition_start_position[0], transition_start_position[1], 0.76]
    final_quaternion = yaw_quaternion(transition_start_quaternion)
    transition_frames = recovery_frames - recovery_coast_frames
    for index in range(1, transition_frames + 1):
        amount = smoothstep5(index / transition_frames)
        joints.append(lerp(transition_start_joint, standing_joint, amount))
        positions.append(lerp(transition_start_position, final_position, amount))
        quaternions.append(slerp(transition_start_quaternion, final_quaternion, amount))

    joints.extend(standing_joint.copy() for _ in range(final_hold_frames))
    positions.extend(final_position.copy() for _ in range(final_hold_frames))
    quaternions.extend(final_quaternion.copy() for _ in range(final_hold_frames))

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

    approach_start = hold_frames
    launch_start = approach_start + approach_frames
    source_remainder_start = launch_start + launch_frames
    recovery_start = core_end_frame + 1
    final_hold_start = recovery_start + recovery_frames
    (destination / "info.txt").write_text(
        "Motion Information: s_batido_v6_buffered\n"
        "==================================================\n\n"
        f"fps: {int(FPS)}\n"
        f"source_frames: {source_frames}\n"
        f"target_frames: {len(joints)}\n"
        f"hold_frames: {hold_frames}\n"
        f"approach_frames: {approach_frames}\n"
        f"launch_frames: {launch_frames}\n"
        f"launch_source_end: {launch_source_end}\n"
        f"source_remainder_start_frame: {source_remainder_start}\n"
        f"core_end_frame: {core_end_frame}\n"
        f"recovery_start_frame: {recovery_start}\n"
        f"recovery_coast_frames: {recovery_coast_frames}\n"
        f"final_hold_start_frame: {final_hold_start}\n"
        f"final_hold_frames: {final_hold_frames}\n",
        encoding="utf-8",
    )
    (destination / "metadata.txt").write_text(
        "Metadata for: s_batido_v6_buffered\n"
        "========================================\n\n"
        "Body part indexes:\n[ 0]\n\n"
        f"Total timesteps: {len(joints)}\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--hold-frames", type=int, default=50)
    parser.add_argument("--approach-frames", type=int, default=35)
    parser.add_argument("--launch-frames", type=int, default=25)
    parser.add_argument("--launch-source-end", type=int, default=12)
    parser.add_argument("--recovery-frames", type=int, default=75)
    parser.add_argument("--recovery-coast-frames", type=int, default=15)
    parser.add_argument("--final-hold-frames", type=int, default=75)
    args = parser.parse_args()
    build(
        args.source,
        args.destination,
        args.hold_frames,
        args.approach_frames,
        args.launch_frames,
        args.launch_source_end,
        args.recovery_frames,
        args.recovery_coast_frames,
        args.final_hold_frames,
    )


if __name__ == "__main__":
    main()
