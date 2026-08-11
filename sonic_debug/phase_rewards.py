"""Phase-specific reward terms for the s_batido fine-tuning runs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from isaaclab.utils import configclass
from isaaclab.utils.math import quat_apply, quat_error_magnitude
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


@configclass
class V3RewardsCfg(V2RewardsCfg):
    """v2 highlight rewards plus landing and balance-recovery objectives."""

    recovery_double_foot_contact = None
    recovery_upright = None
    recovery_low_base_velocity = None
    recovery_center_of_support = None


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


def phase_double_foot_contact(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    ankle_body_names: list[str],
    min_force: float = 40.0,
) -> torch.Tensor:
    """Reward simultaneous, non-impactful contact at both ankles."""
    command: TrackingCommand = env.command_manager.get_term(command_name)
    sensor = env.scene["contact_forces"]
    ankle_ids = [sensor.body_names.index(name) for name in ankle_body_names]
    forces = torch.linalg.norm(sensor.data.net_forces_w[:, ankle_ids], dim=-1)
    contact = torch.clamp(forces / min_force, 0.0, 1.0)
    return _phase_mask(command, start_frame, end_frame) * contact.min(dim=-1).values


def phase_upright_anchor(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    std: float = 0.35,
) -> torch.Tensor:
    """Reward the pelvis local up axis aligning with world up."""
    command: TrackingCommand = env.command_manager.get_term(command_name)
    local_up = torch.zeros_like(command.robot_anchor_pos_w)
    local_up[:, 2] = 1.0
    world_up = quat_apply(command.robot_anchor_quat_w, local_up)
    tilt_error = torch.square(world_up[:, :2]).sum(dim=-1)
    return _phase_mask(command, start_frame, end_frame) * torch.exp(
        -tilt_error / (std * std)
    )


def phase_low_base_velocity(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    linear_std: float = 0.35,
    angular_std: float = 0.7,
) -> torch.Tensor:
    """Reward settling instead of continuing to slide or rotate after landing."""
    command: TrackingCommand = env.command_manager.get_term(command_name)
    linear_speed_sq = torch.square(command.robot_body_lin_vel_w[:, 0]).sum(dim=-1)
    angular_speed_sq = torch.square(command.robot_body_ang_vel_w[:, 0]).sum(dim=-1)
    linear_score = torch.exp(-linear_speed_sq / (linear_std * linear_std))
    angular_score = torch.exp(-angular_speed_sq / (angular_std * angular_std))
    return _phase_mask(command, start_frame, end_frame) * 0.5 * (
        linear_score + angular_score
    )


def phase_center_over_feet(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    ankle_body_names: list[str],
    std: float = 0.2,
) -> torch.Tensor:
    """Reward the pelvis projection staying near the midpoint of both feet."""
    command: TrackingCommand = env.command_manager.get_term(command_name)
    ankle_ids = _get_body_indexes(command, ankle_body_names)
    feet_midpoint_xy = command.robot_body_pos_w[:, ankle_ids, :2].mean(dim=1)
    pelvis_xy = command.robot_anchor_pos_w[:, :2]
    error = torch.square(pelvis_xy - feet_midpoint_xy).sum(dim=-1)
    return _phase_mask(command, start_frame, end_frame) * torch.exp(
        -error / (std * std)
    )
