#!/usr/bin/env python3
"""Render recorded SONIC telemetry with an official Unitree G1 MuJoCo model.

This supports two intentionally different checks:

* kinematic: place the MuJoCo model at every recorded Isaac state.
* torque: initialize from the first recorded state and replay recorded torques
  through MuJoCo physics without policy feedback.

Neither mode runs the SONIC policy inside MuJoCo. A true closed-loop cross-sim
evaluation additionally needs the SONIC observation adapter and policy export.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--telemetry", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("kinematic", "torque"), default="kinematic")
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--azimuth", type=float, default=135.0)
    parser.add_argument("--elevation", type=float, default=-14.0)
    parser.add_argument("--distance", type=float, default=2.8)
    parser.add_argument("--hold-seconds", type=float, default=0.5)
    return parser.parse_args()


def load_names(metadata_path: Path) -> tuple[list[str], list[str]]:
    import json

    metadata = json.loads(metadata_path.read_text())
    return metadata["joint_names"], metadata["tracked_body_names"]


def normalize_pelvis_positions(pelvis_positions: np.ndarray) -> np.ndarray:
    positions = pelvis_positions.astype(np.float64).copy()
    positions[:, :2] -= positions[0, :2]
    return positions


def matrix_to_quat_wxyz(matrix: np.ndarray) -> np.ndarray:
    quat = np.zeros(4, dtype=np.float64)
    mujoco.mju_mat2Quat(quat, matrix.reshape(-1))
    if quat[0] < 0:
        quat *= -1
    return quat


def reconstruct_pelvis_quaternions(
    body_positions: np.ndarray, body_names: list[str]
) -> np.ndarray:
    pelvis_i = body_names.index("pelvis")
    left_hip_i = body_names.index("left_hip_roll_link")
    right_hip_i = body_names.index("right_hip_roll_link")
    torso_i = body_names.index("torso_link")
    quaternions = []

    for bodies in body_positions:
        y_axis = bodies[left_hip_i] - bodies[right_hip_i]
        z_hint = bodies[torso_i] - bodies[pelvis_i]
        y_axis /= max(np.linalg.norm(y_axis), 1e-9)
        z_hint /= max(np.linalg.norm(z_hint), 1e-9)
        x_axis = np.cross(y_axis, z_hint)
        x_axis /= max(np.linalg.norm(x_axis), 1e-9)
        z_axis = np.cross(x_axis, y_axis)
        z_axis /= max(np.linalg.norm(z_axis), 1e-9)
        rotation = np.column_stack((x_axis, y_axis, z_axis))
        quaternions.append(matrix_to_quat_wxyz(rotation))

    quaternions = np.asarray(quaternions)
    for i in range(1, len(quaternions)):
        if np.dot(quaternions[i - 1], quaternions[i]) < 0:
            quaternions[i] *= -1
    return quaternions


def joint_qpos_addresses(model: mujoco.MjModel, joint_names: list[str]) -> list[int]:
    addresses = []
    missing = []
    for name in joint_names:
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if joint_id < 0:
            missing.append(name)
        else:
            addresses.append(int(model.jnt_qposadr[joint_id]))
    if missing:
        raise ValueError(f"Joints missing from MuJoCo model: {missing}")
    return addresses


def actuator_to_telemetry_indices(
    model: mujoco.MjModel, telemetry_joint_names: list[str]
) -> list[int | None]:
    index_by_name = {name: i for i, name in enumerate(telemetry_joint_names)}
    indices: list[int | None] = []
    for actuator_id in range(model.nu):
        joint_id = int(model.actuator_trnid[actuator_id, 0])
        joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
        indices.append(index_by_name.get(joint_name))
    return indices


def configure_camera(args: argparse.Namespace) -> mujoco.MjvCamera:
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:] = (0.0, 0.0, 0.75)
    camera.distance = args.distance
    camera.azimuth = args.azimuth
    camera.elevation = args.elevation
    return camera


def render_frame(
    renderer: mujoco.Renderer,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera,
) -> np.ndarray:
    camera.lookat[0] = 0.85 * camera.lookat[0] + 0.15 * data.qpos[0]
    camera.lookat[1] = 0.85 * camera.lookat[1] + 0.15 * data.qpos[1]
    camera.lookat[2] = 0.85 * camera.lookat[2] + 0.15 * max(0.55, data.qpos[2])
    renderer.update_scene(data, camera=camera)
    return renderer.render().copy()


def main() -> None:
    args = parse_args()
    joint_names, body_names = load_names(args.metadata)
    telemetry = np.load(args.telemetry, allow_pickle=False)
    model = mujoco.MjModel.from_xml_path(str(args.scene.resolve()))
    model.vis.global_.offwidth = max(model.vis.global_.offwidth, args.width)
    model.vis.global_.offheight = max(model.vis.global_.offheight, args.height)
    data = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=args.height, width=args.width)
    camera = configure_camera(args)

    joint_positions = telemetry["actual_joint_pos"].astype(np.float64)
    joint_velocities = telemetry["actual_joint_vel"].astype(np.float64)
    applied_torques = telemetry["applied_torque"].astype(np.float64)
    pelvis_positions = normalize_pelvis_positions(telemetry["actual_pelvis_pos_w"])
    pelvis_quaternions = reconstruct_pelvis_quaternions(
        telemetry["actual_body_pos_w"], body_names
    )
    times = telemetry["sim_time_s"].astype(np.float64)
    times -= times[0]

    qpos_addresses = joint_qpos_addresses(model, joint_names)
    actuator_indices = actuator_to_telemetry_indices(model, joint_names)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    frames: list[np.ndarray] = []
    data.qpos[:3] = pelvis_positions[0]
    data.qpos[3:7] = pelvis_quaternions[0]
    data.qpos[qpos_addresses] = joint_positions[0]
    mujoco.mj_forward(model, data)

    if args.mode == "kinematic":
        for frame_i in range(len(times)):
            data.qpos[:3] = pelvis_positions[frame_i]
            data.qpos[3:7] = pelvis_quaternions[frame_i]
            data.qpos[qpos_addresses] = joint_positions[frame_i]
            mujoco.mj_forward(model, data)
            frames.append(render_frame(renderer, data, camera))
    else:
        data.qvel[:3] = telemetry["actual_pelvis_lin_vel_w"][0]
        data.qvel[6 : 6 + len(joint_names)] = joint_velocities[0]
        model.opt.timestep = min(float(model.opt.timestep), 0.002)
        render_times = np.arange(0.0, times[-1] + 0.5 / args.fps, 1.0 / args.fps)
        render_i = 0
        while data.time <= times[-1] + 1e-9:
            sample_i = min(int(np.searchsorted(times, data.time, side="right") - 1), len(times) - 1)
            sample_i = max(sample_i, 0)
            for actuator_i, telemetry_i in enumerate(actuator_indices):
                data.ctrl[actuator_i] = (
                    0.0 if telemetry_i is None else applied_torques[sample_i, telemetry_i]
                )
            while render_i < len(render_times) and data.time >= render_times[render_i] - 1e-9:
                frames.append(render_frame(renderer, data, camera))
                render_i += 1
            mujoco.mj_step(model, data)

    hold_count = max(0, int(round(args.hold_seconds * args.fps)))
    if frames and hold_count:
        frames.extend([frames[-1].copy() for _ in range(hold_count)])

    imageio.mimwrite(
        args.output,
        frames,
        fps=args.fps,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=None,
    )
    renderer.close()
    print(f"Rendered {len(frames)} frames to {args.output}")


if __name__ == "__main__":
    main()
