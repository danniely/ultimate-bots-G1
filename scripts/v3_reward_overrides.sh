#!/usr/bin/env bash

# v3 keeps the v2 highlight objectives and adds a 2-second recovery phase.
source "${PROJECT_ROOT}/scripts/v2_reward_overrides.sh"

V3_REWARD_OVERRIDES=(
  '++manager_env.rewards._target_=sonic_debug.phase_rewards.V3RewardsCfg'
  "${V2_REWARD_OVERRIDES[@]:1}"

  '++manager_env.rewards.recovery_double_foot_contact._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.recovery_double_foot_contact.func=sonic_debug.phase_rewards:phase_double_foot_contact'
  '++manager_env.rewards.recovery_double_foot_contact.weight=1.5'
  '++manager_env.rewards.recovery_double_foot_contact.params.command_name=motion'
  '++manager_env.rewards.recovery_double_foot_contact.params.start_frame=70'
  '++manager_env.rewards.recovery_double_foot_contact.params.end_frame=180'
  '++manager_env.rewards.recovery_double_foot_contact.params.ankle_body_names=[left_ankle_roll_link,right_ankle_roll_link]'
  '++manager_env.rewards.recovery_double_foot_contact.params.min_force=40.0'

  '++manager_env.rewards.recovery_upright._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.recovery_upright.func=sonic_debug.phase_rewards:phase_upright_anchor'
  '++manager_env.rewards.recovery_upright.weight=2.0'
  '++manager_env.rewards.recovery_upright.params.command_name=motion'
  '++manager_env.rewards.recovery_upright.params.start_frame=70'
  '++manager_env.rewards.recovery_upright.params.end_frame=180'
  '++manager_env.rewards.recovery_upright.params.std=0.35'

  '++manager_env.rewards.recovery_low_base_velocity._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.recovery_low_base_velocity.func=sonic_debug.phase_rewards:phase_low_base_velocity'
  '++manager_env.rewards.recovery_low_base_velocity.weight=1.0'
  '++manager_env.rewards.recovery_low_base_velocity.params.command_name=motion'
  '++manager_env.rewards.recovery_low_base_velocity.params.start_frame=81'
  '++manager_env.rewards.recovery_low_base_velocity.params.end_frame=180'
  '++manager_env.rewards.recovery_low_base_velocity.params.linear_std=0.35'
  '++manager_env.rewards.recovery_low_base_velocity.params.angular_std=0.7'

  '++manager_env.rewards.recovery_center_of_support._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.recovery_center_of_support.func=sonic_debug.phase_rewards:phase_center_over_feet'
  '++manager_env.rewards.recovery_center_of_support.weight=1.5'
  '++manager_env.rewards.recovery_center_of_support.params.command_name=motion'
  '++manager_env.rewards.recovery_center_of_support.params.start_frame=81'
  '++manager_env.rewards.recovery_center_of_support.params.end_frame=180'
  '++manager_env.rewards.recovery_center_of_support.params.ankle_body_names=[left_ankle_roll_link,right_ankle_roll_link]'
  '++manager_env.rewards.recovery_center_of_support.params.std=0.2'
)
