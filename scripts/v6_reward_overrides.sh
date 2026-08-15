#!/usr/bin/env bash

source "${PROJECT_ROOT}/scripts/v5_stability_reward_overrides.sh"

# V6 frame map (328 frames, indices 0..327):
#   0..49    exact deployment standing hold
#   50..84   smooth approach to original frame 0
#   85..109  eased launch mapping original frames 0..12
#   110..177 original frames 13..80
#   178..252 smooth recovery to deployment standing pose
#   253..327 final standing hold
V6_REWARD_OVERRIDES=(
  '++manager_env.rewards._target_=sonic_debug.phase_rewards.V5StabilityRewardsCfg'
  "${V5_STABILITY_REWARD_OVERRIDES[@]:1}"

  'manager_env.rewards.support_contact.params.start_frame=85'
  'manager_env.rewards.support_contact.params.end_frame=121'
  'manager_env.rewards.takeoff_contact.params.start_frame=122'
  'manager_env.rewards.takeoff_contact.params.end_frame=137'
  'manager_env.rewards.takeoff_pelvis_vertical_velocity.params.start_frame=122'
  'manager_env.rewards.takeoff_pelvis_vertical_velocity.params.end_frame=137'
  'manager_env.rewards.airborne_right_leg_position.params.start_frame=138'
  'manager_env.rewards.airborne_right_leg_position.params.end_frame=166'
  'manager_env.rewards.airborne_right_leg_orientation.params.start_frame=138'
  'manager_env.rewards.airborne_right_leg_orientation.params.end_frame=166'
  'manager_env.rewards.airborne_right_leg_joint_pose.params.start_frame=138'
  'manager_env.rewards.airborne_right_leg_joint_pose.params.end_frame=166'
  'manager_env.rewards.airborne_pelvis_orientation.params.start_frame=138'
  'manager_env.rewards.airborne_pelvis_orientation.params.end_frame=166'
  'manager_env.rewards.landing_pelvis_tracking.params.start_frame=167'
  'manager_env.rewards.landing_pelvis_tracking.params.end_frame=177'

  'manager_env.rewards.recovery_double_foot_contact.params.start_frame=178'
  'manager_env.rewards.recovery_double_foot_contact.params.end_frame=327'
  'manager_env.rewards.recovery_upright.params.start_frame=178'
  'manager_env.rewards.recovery_upright.params.end_frame=327'
  'manager_env.rewards.recovery_low_base_velocity.params.start_frame=253'
  'manager_env.rewards.recovery_low_base_velocity.params.end_frame=327'
  'manager_env.rewards.recovery_center_of_support.params.start_frame=253'
  'manager_env.rewards.recovery_center_of_support.params.end_frame=327'

  'manager_env.rewards.support_contact_overload.params.start_frame=85'
  'manager_env.rewards.support_contact_overload.params.end_frame=137'
  'manager_env.rewards.landing_contact_overload.params.start_frame=167'
  'manager_env.rewards.landing_contact_overload.params.end_frame=215'
  'manager_env.rewards.joint_velocity_overload.params.start_frame=0'
  'manager_env.rewards.joint_velocity_overload.params.end_frame=327'
  'manager_env.rewards.dangerous_body_contact.params.start_frame=110'
  'manager_env.rewards.dangerous_body_contact.params.end_frame=252'

  'manager_env.rewards.initial_upright.params.start_frame=0'
  'manager_env.rewards.initial_upright.params.end_frame=49'
  'manager_env.rewards.initial_low_base_velocity.params.start_frame=0'
  'manager_env.rewards.initial_low_base_velocity.params.end_frame=49'
  'manager_env.rewards.initial_joint_velocity_overload.params.start_frame=0'
  'manager_env.rewards.initial_joint_velocity_overload.params.end_frame=49'
  'manager_env.rewards.knee_torque_reserve.params.start_frame=0'
  'manager_env.rewards.knee_torque_reserve.params.end_frame=327'
  'manager_env.rewards.recovery_knee_torque_reserve.params.start_frame=167'
  'manager_env.rewards.recovery_knee_torque_reserve.params.end_frame=327'
  'manager_env.rewards.late_recovery_upright.params.start_frame=253'
  'manager_env.rewards.late_recovery_upright.params.end_frame=327'
  'manager_env.rewards.late_recovery_low_base_velocity.params.start_frame=253'
  'manager_env.rewards.late_recovery_low_base_velocity.params.end_frame=327'
)
