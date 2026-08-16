#!/usr/bin/env bash

source "${PROJECT_ROOT}/scripts/v7_reward_overrides.sh"

# V8 frame map (467 frames): highlight 0..167, slowed landing 168..296,
# controlled recovery 297..391, and exact deployment stand 392..466.
V8_REWARD_OVERRIDES=(
  '++manager_env.rewards._target_=sonic_debug.phase_rewards.V8LandingRewardsCfg'
  "${V7_REWARD_OVERRIDES[@]:1}"
  'manager_env.rewards.landing_pelvis_tracking.params.start_frame=168'
  'manager_env.rewards.landing_pelvis_tracking.params.end_frame=212'
  'manager_env.rewards.recovery_double_foot_contact.params.start_frame=215'
  'manager_env.rewards.recovery_double_foot_contact.params.end_frame=466'
  'manager_env.rewards.recovery_upright.params.start_frame=215'
  'manager_env.rewards.recovery_upright.params.end_frame=466'
  'manager_env.rewards.recovery_low_base_velocity.params.start_frame=296'
  'manager_env.rewards.recovery_low_base_velocity.params.end_frame=466'
  'manager_env.rewards.recovery_center_of_support.params.start_frame=296'
  'manager_env.rewards.recovery_center_of_support.params.end_frame=466'
  'manager_env.rewards.landing_contact_overload.params.start_frame=168'
  'manager_env.rewards.landing_contact_overload.params.end_frame=316'
  'manager_env.rewards.landing_contact_overload.params.soft_limit=850.0'
  'manager_env.rewards.joint_velocity_overload.params.end_frame=466'
  'manager_env.rewards.dangerous_body_contact.params.start_frame=110'
  'manager_env.rewards.dangerous_body_contact.params.end_frame=391'
  'manager_env.rewards.knee_torque_reserve.params.end_frame=466'
  'manager_env.rewards.recovery_knee_torque_reserve.params.start_frame=168'
  'manager_env.rewards.recovery_knee_torque_reserve.params.end_frame=466'
  'manager_env.rewards.late_recovery_upright.params.start_frame=336'
  'manager_env.rewards.late_recovery_upright.params.end_frame=466'
  'manager_env.rewards.late_recovery_low_base_velocity.params.start_frame=336'
  'manager_env.rewards.late_recovery_low_base_velocity.params.end_frame=466'

  '++manager_env.rewards.landing_joint_velocity_overload._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.landing_joint_velocity_overload.func=sonic_debug.phase_rewards:phase_joint_velocity_overload'
  '++manager_env.rewards.landing_joint_velocity_overload.weight=-0.45'
  '++manager_env.rewards.landing_joint_velocity_overload.params.command_name=motion'
  '++manager_env.rewards.landing_joint_velocity_overload.params.start_frame=168'
  '++manager_env.rewards.landing_joint_velocity_overload.params.end_frame=295'
  '++manager_env.rewards.landing_joint_velocity_overload.params.soft_limit=7.5'
  '++manager_env.rewards.landing_joint_velocity_overload.params.max_penalty=6.0'

  '++manager_env.rewards.recovery_joint_velocity_overload._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.recovery_joint_velocity_overload.func=sonic_debug.phase_rewards:phase_joint_velocity_overload'
  '++manager_env.rewards.recovery_joint_velocity_overload.weight=-1.2'
  '++manager_env.rewards.recovery_joint_velocity_overload.params.command_name=motion'
  '++manager_env.rewards.recovery_joint_velocity_overload.params.start_frame=296'
  '++manager_env.rewards.recovery_joint_velocity_overload.params.end_frame=466'
  '++manager_env.rewards.recovery_joint_velocity_overload.params.soft_limit=2.5'
  '++manager_env.rewards.recovery_joint_velocity_overload.params.max_penalty=8.0'

  '++manager_env.rewards.recovery_capture_point._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.recovery_capture_point.func=sonic_debug.phase_rewards:phase_capture_point_over_feet'
  '++manager_env.rewards.recovery_capture_point.weight=3.5'
  '++manager_env.rewards.recovery_capture_point.params.command_name=motion'
  '++manager_env.rewards.recovery_capture_point.params.start_frame=296'
  '++manager_env.rewards.recovery_capture_point.params.end_frame=466'
  '++manager_env.rewards.recovery_capture_point.params.ankle_body_names=[left_ankle_roll_link,right_ankle_roll_link]'
  '++manager_env.rewards.recovery_capture_point.params.horizon_s=0.22'
  '++manager_env.rewards.recovery_capture_point.params.std=0.24'
)
