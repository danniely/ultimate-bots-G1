#!/usr/bin/env bash

source "${PROJECT_ROOT}/scripts/v3_reward_overrides.sh"

V3_ROBUST_REWARD_OVERRIDES=(
  '++manager_env.rewards._target_=sonic_debug.phase_rewards.V3RobustRewardsCfg'
  "${V3_REWARD_OVERRIDES[@]:1}"

  '++manager_env.rewards.support_contact_overload._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.support_contact_overload.func=sonic_debug.phase_rewards:phase_contact_force_overload'
  '++manager_env.rewards.support_contact_overload.weight=-0.2'
  '++manager_env.rewards.support_contact_overload.params.command_name=motion'
  '++manager_env.rewards.support_contact_overload.params.start_frame=0'
  '++manager_env.rewards.support_contact_overload.params.end_frame=40'
  '++manager_env.rewards.support_contact_overload.params.body_names=[left_wrist_roll_link,left_wrist_pitch_link,left_wrist_yaw_link,left_hand_palm_link,right_wrist_roll_link,right_wrist_pitch_link,right_wrist_yaw_link,right_hand_palm_link]'
  '++manager_env.rewards.support_contact_overload.params.soft_limit=400.0'
  '++manager_env.rewards.support_contact_overload.params.max_penalty=9.0'

  '++manager_env.rewards.landing_contact_overload._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.landing_contact_overload.func=sonic_debug.phase_rewards:phase_contact_force_overload'
  '++manager_env.rewards.landing_contact_overload.weight=-0.1'
  '++manager_env.rewards.landing_contact_overload.params.command_name=motion'
  '++manager_env.rewards.landing_contact_overload.params.start_frame=65'
  '++manager_env.rewards.landing_contact_overload.params.end_frame=105'
  '++manager_env.rewards.landing_contact_overload.params.body_names=[left_ankle_pitch_link,left_ankle_roll_link,LL_FOOT,right_ankle_pitch_link,right_ankle_roll_link,LR_FOOT]'
  '++manager_env.rewards.landing_contact_overload.params.soft_limit=1200.0'
  '++manager_env.rewards.landing_contact_overload.params.max_penalty=4.0'

  '++manager_env.rewards.joint_velocity_overload._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.joint_velocity_overload.func=sonic_debug.phase_rewards:phase_joint_velocity_overload'
  '++manager_env.rewards.joint_velocity_overload.weight=-0.05'
  '++manager_env.rewards.joint_velocity_overload.params.command_name=motion'
  '++manager_env.rewards.joint_velocity_overload.params.start_frame=0'
  '++manager_env.rewards.joint_velocity_overload.params.end_frame=180'
  '++manager_env.rewards.joint_velocity_overload.params.soft_limit=15.0'
  '++manager_env.rewards.joint_velocity_overload.params.max_penalty=4.0'

  '++manager_env.rewards.dangerous_body_contact._target_=isaaclab.managers.RewardTermCfg'
  '++manager_env.rewards.dangerous_body_contact.func=sonic_debug.phase_rewards:phase_contact_force_overload'
  '++manager_env.rewards.dangerous_body_contact.weight=-1.0'
  '++manager_env.rewards.dangerous_body_contact.params.command_name=motion'
  '++manager_env.rewards.dangerous_body_contact.params.start_frame=35'
  '++manager_env.rewards.dangerous_body_contact.params.end_frame=130'
  '++manager_env.rewards.dangerous_body_contact.params.body_names=[pelvis,pelvis_contour_link,torso_link,head_link]'
  '++manager_env.rewards.dangerous_body_contact.params.soft_limit=50.0'
  '++manager_env.rewards.dangerous_body_contact.params.max_penalty=16.0'
)
