"""Phase-specific reward terms for the s_batido v2 fine-tuning run."""

from __future__ import annotations

from typing import TYPE_CHECKING

from isaaclab.utils import configclass
from isaaclab.utils.math import quat_error_magnitude
import torch

from gear_sonic.envs.manager_env.mdp.commands import TrackingCommand, _get_body_indexes
from gear_sonic.envs.manager_env.mdp.rewards import RewardsCfg

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv


@configclass
class V2RewardsCfg(RewardsCfg):
    """Base SONIC rewards plus phase-specific s_batido bonuses."""

    support_contact = None
    takeoff_contact = None
    takeoff_pelvis_vertical_velocity = None
    airborne_right_leg_position = None
    airborne_right_leg_orientation = None
    airborne_right_leg_joint_pose = None
    airborne_pelvis_orientation = None
    landing_pelvis_tracking = None


def _phase_mask(
    command: TrackingCommand, start_frame: int, end_frame: int
) -> torch.Tensor:
    frame = command.motion_start_time_steps + command.time_steps
    return ((frame >= start_frame) & (frame <= end_frame)).to(dtype=torch.float32)


def phase_support_contact(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    wrist_body_names: list[str],
    ankle_body_names: list[str],
    min_force: float = 20.0,
) -> torch.Tensor:
    """Reward at least one wrist and one ankle maintaining useful ground contact.

    The force contribution saturates at ``min_force`` so the policy cannot gain
    extra reward by slamming the robot into the floor.
    """
    command: TrackingCommand = env.command_manager.get_term(command_name)
    sensor = env.scene["contact_forces"]
    wrist_ids = [sensor.body_names.index(name) for name in wrist_body_names]
    ankle_ids = [sensor.body_names.index(name) for name in ankle_body_names]
    forces = torch.linalg.norm(sensor.data.net_forces_w, dim=-1)
    wrist_contact = torch.clamp(forces[:, wrist_ids].max(dim=-1).values / min_force, 0.0, 1.0)
    ankle_contact = torch.clamp(forces[:, ankle_ids].max(dim=-1).values / min_force, 0.0, 1.0)
    return _phase_mask(command, start_frame, end_frame) * 0.5 * (
        wrist_contact + ankle_contact
    )


def phase_pelvis_vertical_velocity_tracking(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    std: float,
) -> torch.Tensor:
    """Track reference pelvis vertical velocity during the takeoff window."""
    command: TrackingCommand = env.command_manager.get_term(command_name)
    target_vz = command.body_lin_vel_w[:, 0, 2]
    actual_vz = command.robot_body_lin_vel_w[:, 0, 2]
    reward = torch.exp(-torch.square(target_vz - actual_vz) / (std * std))
    return _phase_mask(command, start_frame, end_frame) * reward


def phase_relative_body_position_tracking(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    std: float,
    body_names: list[str],
) -> torch.Tensor:
    """Track selected body positions relative to the pelvis in one phase."""
    command: TrackingCommand = env.command_manager.get_term(command_name)
    tracked = _get_body_indexes(command, body_names)
    diff = command.body_pos_relative_w[:, tracked] - command.robot_body_pos_w[:, tracked]
    error = torch.square(diff).sum(dim=-1).mean(dim=-1)
    return _phase_mask(command, start_frame, end_frame) * torch.exp(
        -error / (std * std)
    )


def phase_relative_body_orientation_tracking(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    std: float,
    body_names: list[str],
) -> torch.Tensor:
    """Track selected body orientations relative to the pelvis in one phase."""
    command: TrackingCommand = env.command_manager.get_term(command_name)
    tracked = _get_body_indexes(command, body_names)
    error = quat_error_magnitude(
        command.body_quat_relative_w[:, tracked],
        command.robot_body_quat_w[:, tracked],
    ).square().mean(dim=-1)
    return _phase_mask(command, start_frame, end_frame) * torch.exp(
        -error / (std * std)
    )


def phase_joint_position_tracking(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    std: float,
    joint_names: list[str],
) -> torch.Tensor:
    """Track selected joint angles directly during the highlight."""
    command: TrackingCommand = env.command_manager.get_term(command_name)
    joint_ids = [command.robot.joint_names.index(name) for name in joint_names]
    diff = command.joint_pos[:, joint_ids] - command.robot_joint_pos[:, joint_ids]
    error = torch.square(diff).mean(dim=-1)
    return _phase_mask(command, start_frame, end_frame) * torch.exp(
        -error / (std * std)
    )


def phase_anchor_orientation_tracking(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    std: float,
) -> torch.Tensor:
    """Track pelvis orientation during the airborne highlight."""
    command: TrackingCommand = env.command_manager.get_term(command_name)
    error = quat_error_magnitude(command.anchor_quat_w, command.robot_anchor_quat_w)
    return _phase_mask(command, start_frame, end_frame) * torch.exp(
        -error.square() / (std * std)
    )


def phase_anchor_position_tracking(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    std: float,
) -> torch.Tensor:
    """Track pelvis position in the landing/recovery window."""
    command: TrackingCommand = env.command_manager.get_term(command_name)
    diff = command.anchor_pos_w - command.robot_anchor_pos_w
    error = torch.square(diff).sum(dim=-1)
    return _phase_mask(command, start_frame, end_frame) * torch.exp(
        -error / (std * std)
    )
