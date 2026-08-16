"""Phase-specific reward terms for the s_batido fine-tuning runs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from isaaclab.utils import configclass
from isaaclab.utils.math import quat_apply, quat_error_magnitude
import torch

from gear_sonic.envs.manager_env.mdp.commands import TrackingCommand, _get_body_indexes
from gear_sonic.envs.manager_env.mdp.events import EventCfg
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


@configclass
class V3RobustRewardsCfg(V3RewardsCfg):
    """v3 rewards plus soft hardware-load constraints for sim-to-real."""

    support_contact_overload = None
    landing_contact_overload = None
    joint_velocity_overload = None
    dangerous_body_contact = None


@configclass
class V5StabilityRewardsCfg(V3RobustRewardsCfg):
    """Real-robot stability terms added after the V4 sim2sim audit."""

    initial_upright = None
    initial_low_base_velocity = None
    initial_joint_velocity_overload = None
    knee_torque_reserve = None
    recovery_knee_torque_reserve = None
    late_recovery_upright = None
    late_recovery_low_base_velocity = None


@configclass
class V8LandingRewardsCfg(V5StabilityRewardsCfg):
    """Landing-energy and capture-point terms for cross-simulator recovery."""

    landing_joint_velocity_overload = None
    recovery_joint_velocity_overload = None
    recovery_capture_point = None


@configclass
class V8EventCfg(EventCfg):
    """Base SONIC randomization plus actuator gain uncertainty."""

    actuator_gains = None


def _phase_mask(
    command: TrackingCommand, start_frame: int, end_frame: int
) -> torch.Tensor:
    frame = command.motion_start_time_steps + command.time_steps
    return ((frame >= start_frame) & (frame <= end_frame)).to(dtype=torch.float32)


def phase_aware_base_safety(
    env: ManagerBasedRLEnv,
    command_name: str,
    recovery_settle_frame: int = 131,
    pre_recovery_tilt_error_rad: float = 1.2,
    pre_recovery_min_height: float = 0.3,
    recovery_world_tilt_rad: float = 0.8,
    recovery_min_height: float = 0.5,
    unsafe_contact_body_names: list[str] | None = None,
    unsafe_contact_force: float = 100.0,
) -> torch.Tensor:
    """Terminate on a physical fall without treating yaw error as a fall.

    Before recovery, the capoeira reference intentionally tilts the pelvis and
    spins around world Z.  Compare only the reference and robot *up vectors*,
    so a heading mismatch does not trigger an emergency stop.  During recovery
    the robot must instead be upright in the world frame and keep its pelvis
    above a conservative minimum height.
    """
    command: TrackingCommand = env.command_manager.get_term(command_name)
    local_up = torch.zeros_like(command.robot_anchor_pos_w)
    local_up[:, 2] = 1.0
    reference_up = quat_apply(command.anchor_quat_w, local_up)
    robot_up = quat_apply(command.robot_anchor_quat_w, local_up)

    relative_cos = torch.sum(reference_up * robot_up, dim=-1).clamp(-1.0, 1.0)
    relative_tilt = torch.acos(relative_cos)
    world_cos = robot_up[:, 2].clamp(-1.0, 1.0)
    world_tilt = torch.acos(world_cos)

    frame = command.motion_start_time_steps + command.time_steps
    before_recovery = frame < recovery_settle_frame
    unsafe_motion = (relative_tilt > pre_recovery_tilt_error_rad) | (
        command.robot_anchor_pos_w[:, 2] < pre_recovery_min_height
    )
    unsafe_recovery = (world_tilt > recovery_world_tilt_rad) | (
        command.robot_anchor_pos_w[:, 2] < recovery_min_height
    )
    unsafe = torch.where(before_recovery, unsafe_motion, unsafe_recovery)

    if unsafe_contact_body_names:
        sensor = env.scene["contact_forces"]
        body_ids = [
            sensor.body_names.index(name) for name in unsafe_contact_body_names
        ]
        force = torch.linalg.norm(
            sensor.data.net_forces_w[:, body_ids], dim=-1
        ).max(dim=-1).values
        unsafe = unsafe | (force > unsafe_contact_force)
    return unsafe


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


def phase_capture_point_over_feet(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    ankle_body_names: list[str],
    horizon_s: float = 0.22,
    std: float = 0.24,
) -> torch.Tensor:
    """Reward projected pelvis motion ending inside the two-foot support area.

    A static center-of-support term can be high while the pelvis still carries
    enough horizontal momentum to fall after touchdown.  This short-horizon
    capture-point approximation makes that residual velocity visible to PPO.
    """
    command: TrackingCommand = env.command_manager.get_term(command_name)
    ankle_ids = _get_body_indexes(command, ankle_body_names)
    feet_midpoint_xy = command.robot_body_pos_w[:, ankle_ids, :2].mean(dim=1)
    pelvis_xy = command.robot_anchor_pos_w[:, :2]
    pelvis_velocity_xy = command.robot_body_lin_vel_w[:, 0, :2]
    capture_xy = pelvis_xy + horizon_s * pelvis_velocity_xy
    error = torch.square(capture_xy - feet_midpoint_xy).sum(dim=-1)
    return _phase_mask(command, start_frame, end_frame) * torch.exp(
        -error / (std * std)
    )


def phase_contact_force_overload(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    body_names: list[str],
    soft_limit: float,
    max_penalty: float = 9.0,
) -> torch.Tensor:
    """Penalize force above a soft limit without discouraging useful contact.

    The hinge is zero below ``soft_limit``.  Squaring the normalized excess
    makes sharp impacts more expensive than sustained, gently shared support.
    The cap prevents an isolated PhysX spike from dominating an entire PPO
    batch.
    """
    command: TrackingCommand = env.command_manager.get_term(command_name)
    sensor = env.scene["contact_forces"]
    body_ids = [sensor.body_names.index(name) for name in body_names]
    forces = torch.linalg.norm(sensor.data.net_forces_w[:, body_ids], dim=-1)
    peak_force = forces.max(dim=-1).values
    overload = torch.relu(peak_force / soft_limit - 1.0).square()
    return _phase_mask(command, start_frame, end_frame) * torch.clamp(
        overload, max=max_penalty
    )


def phase_joint_velocity_overload(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    soft_limit: float,
    max_penalty: float = 4.0,
) -> torch.Tensor:
    """Penalize only unusually fast joints, preserving normal movement speed."""
    command: TrackingCommand = env.command_manager.get_term(command_name)
    peak_speed = env.scene["robot"].data.joint_vel.abs().max(dim=-1).values
    overload = torch.relu(peak_speed / soft_limit - 1.0).square()
    return _phase_mask(command, start_frame, end_frame) * torch.clamp(
        overload, max=max_penalty
    )


def phase_joint_torque_overload(
    env: ManagerBasedRLEnv,
    command_name: str,
    start_frame: int,
    end_frame: int,
    joint_names: list[str],
    soft_limit: float,
    max_penalty: float = 4.0,
) -> torch.Tensor:
    """Keep commanded torque below a soft reserve before actuator clipping.

    ``computed_torque`` is the PD/controller request before the simulator clips
    it to the actuator effort limit.  Penalizing only the excess preserves the
    torque needed for takeoff while teaching the policy not to depend on the
    139 Nm knee saturation observed in the official MuJoCo deployment loop.
    """
    command: TrackingCommand = env.command_manager.get_term(command_name)
    robot = env.scene["robot"]
    joint_ids = robot.find_joints(joint_names)[0]
    peak_torque = robot.data.computed_torque[:, joint_ids].abs().max(dim=-1).values
    overload = torch.relu(peak_torque / soft_limit - 1.0).square()
    return _phase_mask(command, start_frame, end_frame) * torch.clamp(
        overload, max=max_penalty
    )
