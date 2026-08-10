"""Isaac Lab recorder that saves frame-level SONIC tracking diagnostics.

The module lives in this project so the upstream GR00T checkout does not need
to be modified. Hydra loads it while evaluating on RunPod.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import torch
from isaaclab.managers import manager_term_cfg, recorder_manager
from isaaclab.utils import configclass
from loguru import logger

from gear_sonic.envs.manager_env.mdp.recorders import RecordersCfg

if TYPE_CHECKING:
    from isaaclab import envs


@configclass
class DebugRecordersCfg(RecordersCfg):
    """Standard SONIC recorders plus detailed frame diagnostics."""

    frame_diagnostics = None


class FrameDiagnosticsRecorderTerm(recorder_manager.RecorderTerm):
    """Save actual/reference state on every policy step as NPZ and CSV."""

    cfg: FrameDiagnosticsRecorderCfg

    def __init__(self, cfg: FrameDiagnosticsRecorderCfg, env: envs.ManagerBasedEnv):
        super().__init__(cfg, env)
        self.cfg = cfg
        self.env = env
        self.save_dir = Path(self.cfg.save_path)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.num_record_envs = min(int(self.cfg.max_envs), int(self.env.num_envs))
        self.frame_id = 0
        self._initialized = False
        self._closed = False
        self._buffers: dict[int, dict[str, list[np.ndarray]]] = {}
        self._csv_files: dict[int, Any] = {}
        self._csv_writers: dict[int, csv.DictWriter] = {}
        logger.info(f"=== Frame diagnostics: saving to {self.save_dir} ===")

    @staticmethod
    def _cpu(value: torch.Tensor | np.ndarray | Any) -> np.ndarray:
        if isinstance(value, torch.Tensor):
            return value.detach().cpu().numpy().copy()
        return np.asarray(value).copy()

    def _initialize(self) -> None:
        self.robot = self.env.scene["robot"]
        self.motion = self.env.command_manager.get_term("motion")
        self.joint_names = list(self.robot.joint_names)
        self.body_names = list(getattr(self.motion.cfg, "body_names", []))
        self.termination_names = list(self.env.termination_manager.active_terms)
        self.start_idx = getattr(getattr(self.env, "wrapper", None), "start_idx", 0)
        self.contact_sensor = None
        self.contact_body_names: list[str] = []
        try:
            self.contact_sensor = self.env.scene["contact_forces"]
            self.contact_body_names = list(self.contact_sensor.body_names)
        except Exception:  # noqa: BLE001
            logger.warning("contact_forces sensor unavailable; contact arrays will be empty")

        self.fields = [
            "frame_id", "sim_time_s", "motion_frame", "motion_time_s", "episode_step",
            "actual_joint_pos", "reference_joint_pos", "joint_pos_error",
            "actual_joint_vel", "reference_joint_vel", "joint_vel_error",
            "joint_pos_target", "applied_torque", "computed_torque", "raw_action",
            "actual_body_pos_w", "reference_body_pos_w", "body_pos_error_w",
            "actual_body_lin_vel_w", "reference_body_lin_vel_w",
            "actual_pelvis_pos_w", "reference_pelvis_pos_w",
            "actual_pelvis_lin_vel_w", "reference_pelvis_lin_vel_w",
            "contact_force_w", "termination_flags", "terminated", "time_out", "done",
        ]
        for env_idx in range(self.num_record_envs):
            self._buffers[env_idx] = {field: [] for field in self.fields}

        metadata = {
            "format_version": 1,
            "policy_dt_s": float(self.env.step_dt),
            "policy_fps": float(1.0 / self.env.step_dt),
            "joint_names": self.joint_names,
            "tracked_body_names": self.body_names,
            "contact_body_names": self.contact_body_names,
            "termination_names": self.termination_names,
            "coordinate_frame": "Isaac world frame; positions include environment origin",
            "quaternion_format": "wxyz",
            "units": {
                "time": "seconds",
                "joint_position": "radians",
                "joint_velocity": "radians/second",
                "position": "meters",
                "linear_velocity": "meters/second",
                "torque": "newton-meters",
                "contact_force": "newtons",
            },
            "npz_is_canonical": True,
        }
        (self.save_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        self._initialized = True

    def _safe_robot_array(self, name: str, env_idx: int, shape: tuple[int, ...]) -> np.ndarray:
        value = getattr(self.robot.data, name, None)
        if value is None:
            return np.full(shape, np.nan, dtype=np.float32)
        return self._cpu(value[env_idx])

    def _raw_action(self, env_idx: int) -> np.ndarray:
        value = getattr(self.env.action_manager, "action", None)
        if value is None:
            value = getattr(self.env.action_manager, "prev_action", None)
        if value is None:
            return np.full((len(self.joint_names),), np.nan, dtype=np.float32)
        return self._cpu(value[env_idx])

    def _contact_forces(self, env_idx: int) -> np.ndarray:
        if self.contact_sensor is None:
            return np.empty((0, 3), dtype=np.float32)
        value = getattr(self.contact_sensor.data, "net_forces_w", None)
        if value is None:
            return np.empty((0, 3), dtype=np.float32)
        return self._cpu(value[env_idx])

    def _termination_state(self, env_idx: int) -> tuple[np.ndarray, bool, bool]:
        manager = self.env.termination_manager
        flags = np.asarray(
            [bool(manager.get_term(name)[env_idx].item()) for name in self.termination_names],
            dtype=np.bool_,
        )
        terminated = bool(manager.terminated[env_idx].item())
        timed_out = bool(manager.time_outs[env_idx].item())
        return flags, terminated, timed_out

    @staticmethod
    def _flatten(prefix: str, value: np.ndarray, names: list[str] | None = None) -> dict[str, Any]:
        arr = np.asarray(value)
        result: dict[str, Any] = {}
        if arr.ndim == 0:
            result[prefix] = arr.item()
        elif arr.ndim == 1:
            labels = names if names and len(names) == len(arr) else [str(i) for i in range(len(arr))]
            result.update({f"{prefix}.{label}": arr[i].item() for i, label in enumerate(labels)})
        elif arr.ndim == 2 and arr.shape[1] == 3:
            labels = names if names and len(names) == len(arr) else [str(i) for i in range(len(arr))]
            for i, label in enumerate(labels):
                for axis, axis_name in enumerate("xyz"):
                    result[f"{prefix}.{label}.{axis_name}"] = arr[i, axis].item()
        else:
            for index in np.ndindex(arr.shape):
                suffix = ".".join(map(str, index))
                result[f"{prefix}.{suffix}"] = arr[index].item()
        return result

    def _csv_row(self, data: dict[str, np.ndarray]) -> dict[str, Any]:
        row: dict[str, Any] = {}
        joint_fields = {
            "actual_joint_pos", "reference_joint_pos", "joint_pos_error",
            "actual_joint_vel", "reference_joint_vel", "joint_vel_error",
            "joint_pos_target", "applied_torque", "computed_torque", "raw_action",
        }
        body_fields = {
            "actual_body_pos_w", "reference_body_pos_w", "body_pos_error_w",
            "actual_body_lin_vel_w", "reference_body_lin_vel_w",
        }
        for key, value in data.items():
            if key in joint_fields:
                row.update(self._flatten(key, value, self.joint_names))
            elif key in body_fields:
                row.update(self._flatten(key, value, self.body_names))
            elif key == "contact_force_w":
                row.update(self._flatten(key, value, self.contact_body_names))
            elif key == "termination_flags":
                row.update(self._flatten(key, value, self.termination_names))
            else:
                row.update(self._flatten(key, value))
        return row

    def _write_csv(self, env_idx: int, data: dict[str, np.ndarray]) -> None:
        row = self._csv_row(data)
        if env_idx not in self._csv_writers:
            file_idx = self.start_idx + env_idx
            handle = open(self.save_dir / f"env_{file_idx:06d}_frames.csv", "w", newline="")  # noqa: PTH123, SIM115
            writer = csv.DictWriter(handle, fieldnames=list(row))
            writer.writeheader()
            self._csv_files[env_idx] = handle
            self._csv_writers[env_idx] = writer
        self._csv_writers[env_idx].writerow(row)
        self._csv_files[env_idx].flush()

    def _capture(self, env_idx: int) -> dict[str, np.ndarray]:
        actual_joint_pos = self._cpu(self.motion.robot_joint_pos[env_idx])
        reference_joint_pos = self._cpu(self.motion.joint_pos[env_idx])
        actual_joint_vel = self._cpu(self.motion.robot_joint_vel[env_idx])
        reference_joint_vel = self._cpu(self.motion.joint_vel[env_idx])
        actual_body_pos = self._cpu(self.motion.robot_body_pos_w[env_idx])
        reference_body_pos = self._cpu(self.motion.body_pos_w[env_idx])
        actual_body_vel = self._cpu(self.motion.robot_body_lin_vel_w[env_idx])
        reference_body_vel = self._cpu(self.motion.body_lin_vel_w[env_idx])
        termination_flags, terminated, timed_out = self._termination_state(env_idx)
        motion_frame = int(
            (self.motion.motion_start_time_steps[env_idx] + self.motion.time_steps[env_idx]).item()
        )
        episode_step = int(self.env.episode_length_buf[env_idx].item())

        return {
            "frame_id": np.asarray(self.frame_id, dtype=np.int64),
            "sim_time_s": np.asarray(self.frame_id * self.env.step_dt, dtype=np.float64),
            "motion_frame": np.asarray(motion_frame, dtype=np.int64),
            "motion_time_s": np.asarray(motion_frame * self.env.step_dt, dtype=np.float64),
            "episode_step": np.asarray(episode_step, dtype=np.int64),
            "actual_joint_pos": actual_joint_pos,
            "reference_joint_pos": reference_joint_pos,
            "joint_pos_error": reference_joint_pos - actual_joint_pos,
            "actual_joint_vel": actual_joint_vel,
            "reference_joint_vel": reference_joint_vel,
            "joint_vel_error": reference_joint_vel - actual_joint_vel,
            "joint_pos_target": self._safe_robot_array("joint_pos_target", env_idx, (len(self.joint_names),)),
            "applied_torque": self._safe_robot_array("applied_torque", env_idx, (len(self.joint_names),)),
            "computed_torque": self._safe_robot_array("computed_torque", env_idx, (len(self.joint_names),)),
            "raw_action": self._raw_action(env_idx),
            "actual_body_pos_w": actual_body_pos,
            "reference_body_pos_w": reference_body_pos,
            "body_pos_error_w": reference_body_pos - actual_body_pos,
            "actual_body_lin_vel_w": actual_body_vel,
            "reference_body_lin_vel_w": reference_body_vel,
            "actual_pelvis_pos_w": actual_body_pos[0],
            "reference_pelvis_pos_w": reference_body_pos[0],
            "actual_pelvis_lin_vel_w": actual_body_vel[0],
            "reference_pelvis_lin_vel_w": reference_body_vel[0],
            "contact_force_w": self._contact_forces(env_idx),
            "termination_flags": termination_flags,
            "terminated": np.asarray(terminated, dtype=np.bool_),
            "time_out": np.asarray(timed_out, dtype=np.bool_),
            "done": np.asarray(terminated or timed_out, dtype=np.bool_),
        }

    def _write_npz(self, env_idx: int) -> None:
        data = self._buffers[env_idx]
        if not data["frame_id"]:
            return
        stacked = {key: np.stack(values) for key, values in data.items()}
        file_idx = self.start_idx + env_idx
        final_path = self.save_dir / f"env_{file_idx:06d}_frames.npz"
        temp_path = self.save_dir / f"env_{file_idx:06d}_frames.tmp.npz"
        np.savez_compressed(temp_path, **stacked)
        os.replace(temp_path, final_path)

    def record_post_step(self) -> tuple[str | None, torch.Tensor | dict | None]:
        if not self._initialized:
            self._initialize()
        for env_idx in range(self.num_record_envs):
            data = self._capture(env_idx)
            for field, value in data.items():
                self._buffers[env_idx][field].append(value)
            self._write_csv(env_idx, data)
        self.frame_id += 1
        if self.frame_id % max(1, int(self.cfg.flush_interval)) == 0:
            for env_idx in range(self.num_record_envs):
                self._write_npz(env_idx)
        return "frame_diagnostics", torch.ones(self.env.num_envs, 1, device=self.env.device)

    def close_writers(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._initialized:
            for env_idx in range(self.num_record_envs):
                self._write_npz(env_idx)
            for handle in self._csv_files.values():
                handle.close()
            logger.info(f"Saved frame diagnostics ({self.frame_id} frames) to {self.save_dir}")

    def __del__(self):
        self.close_writers()


@configclass
class FrameDiagnosticsRecorderCfg(manager_term_cfg.RecorderTermCfg):
    """Configuration for :class:`FrameDiagnosticsRecorderTerm`."""

    class_type: type = FrameDiagnosticsRecorderTerm
    save_path: str = None
    max_envs: int = 1
    flush_interval: int = 10
