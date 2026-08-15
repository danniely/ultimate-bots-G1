#!/usr/bin/env bash

source "${PROJECT_ROOT}/scripts/v3_robust_reward_overrides.sh"

V5_STABILITY_REWARD_OVERRIDES=(
  '++manager_env.rewards._target_=sonic_debug.phase_rewards.V5StabilityRewardsCfg'
  "${V3_ROBUST_REWARD_OVERRIDES[@]:1}"

  '++manager_env.rewards.initial_upright._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.initial_upright.func=sonic_debug.phase_rewards:phase_upright_anchor'
  '++manager_env.rewards.initial_upright.weight=3.0'
  '++manager_env.rewards.initial_upright.params.command_name=motion'
  '++manager_env.rewards.initial_upright.params.start_frame=0'
  '++manager_env.rewards.initial_upright.params.end_frame=35'
  '++manager_env.rewards.initial_upright.params.std=0.20'

  '++manager_env.rewards.initial_low_base_velocity._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.initial_low_base_velocity.func=sonic_debug.phase_rewards:phase_low_base_velocity'
  '++manager_env.rewards.initial_low_base_velocity.weight=8.0'
  '++manager_env.rewards.initial_low_base_velocity.params.command_name=motion'
  '++manager_env.rewards.initial_low_base_velocity.params.start_frame=0'
  '++manager_env.rewards.initial_low_base_velocity.params.end_frame=35'
  '++manager_env.rewards.initial_low_base_velocity.params.linear_std=0.20'
  '++manager_env.rewards.initial_low_base_velocity.params.angular_std=0.40'

  '++manager_env.rewards.initial_joint_velocity_overload._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.initial_joint_velocity_overload.func=sonic_debug.phase_rewards:phase_joint_velocity_overload'
  '++manager_env.rewards.initial_joint_velocity_overload.weight=-0.25'
  '++manager_env.rewards.initial_joint_velocity_overload.params.command_name=motion'
  '++manager_env.rewards.initial_joint_velocity_overload.params.start_frame=0'
  '++manager_env.rewards.initial_joint_velocity_overload.params.end_frame=35'
  '++manager_env.rewards.initial_joint_velocity_overload.params.soft_limit=2.5'
  '++manager_env.rewards.initial_joint_velocity_overload.params.max_penalty=4.0'

  '++manager_env.rewards.knee_torque_reserve._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.knee_torque_reserve.func=sonic_debug.phase_rewards:phase_joint_torque_overload'
  '++manager_env.rewards.knee_torque_reserve.weight=-0.03'
  '++manager_env.rewards.knee_torque_reserve.params.command_name=motion'
  '++manager_env.rewards.knee_torque_reserve.params.start_frame=0'
  '++manager_env.rewards.knee_torque_reserve.params.end_frame=180'
  '++manager_env.rewards.knee_torque_reserve.params.joint_names=[left_knee_joint,right_knee_joint]'
  '++manager_env.rewards.knee_torque_reserve.params.soft_limit=115.0'
  '++manager_env.rewards.knee_torque_reserve.params.max_penalty=4.0'

  '++manager_env.rewards.recovery_knee_torque_reserve._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.recovery_knee_torque_reserve.func=sonic_debug.phase_rewards:phase_joint_torque_overload'
  '++manager_env.rewards.recovery_knee_torque_reserve.weight=-0.08'
  '++manager_env.rewards.recovery_knee_torque_reserve.params.command_name=motion'
  '++manager_env.rewards.recovery_knee_torque_reserve.params.start_frame=65'
  '++manager_env.rewards.recovery_knee_torque_reserve.params.end_frame=180'
  '++manager_env.rewards.recovery_knee_torque_reserve.params.joint_names=[left_knee_joint,right_knee_joint]'
  '++manager_env.rewards.recovery_knee_torque_reserve.params.soft_limit=105.0'
  '++manager_env.rewards.recovery_knee_torque_reserve.params.max_penalty=4.0'

  '++manager_env.rewards.late_recovery_upright._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.late_recovery_upright.func=sonic_debug.phase_rewards:phase_upright_anchor'
  '++manager_env.rewards.late_recovery_upright.weight=3.0'
  '++manager_env.rewards.late_recovery_upright.params.command_name=motion'
  '++manager_env.rewards.late_recovery_upright.params.start_frame=131'
  '++manager_env.rewards.late_recovery_upright.params.end_frame=180'
  '++manager_env.rewards.late_recovery_upright.params.std=0.20'

  '++manager_env.rewards.late_recovery_low_base_velocity._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.late_recovery_low_base_velocity.func=sonic_debug.phase_rewards:phase_low_base_velocity'
  '++manager_env.rewards.late_recovery_low_base_velocity.weight=2.0'
  '++manager_env.rewards.late_recovery_low_base_velocity.params.command_name=motion'
  '++manager_env.rewards.late_recovery_low_base_velocity.params.start_frame=131'
  '++manager_env.rewards.late_recovery_low_base_velocity.params.end_frame=180'
  '++manager_env.rewards.late_recovery_low_base_velocity.params.linear_std=0.20'
  '++manager_env.rewards.late_recovery_low_base_velocity.params.angular_std=0.40'
)
