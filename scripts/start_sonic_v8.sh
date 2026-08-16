#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/srv/sonic/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/sonic/ultimate-bots-G1}"
PYTHON="${PYTHON:-/srv/sonic/env_isaaclab/bin/python}"
CHECKPOINT="${CHECKPOINT:-${PROJECT_ROOT}/checkpoints/v7/s_batido_v7_targeted_final.pt}"
MOTION_FILE="${MOTION_FILE:-${PROJECT_ROOT}/data/motion_lib/s_batido_v8_landing.pkl}"
NUM_ENVS="${NUM_ENVS:-384}"
ITERATIONS="${ITERATIONS:-300}"
SAVE_INTERVAL="${SAVE_INTERVAL:-25}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-s_batido_v8_landing}"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/exports/v8/train}"

source "${PROJECT_ROOT}/scripts/v8_reward_overrides.sh"
mkdir -p "${OUTPUT_DIR}"
cd "${SONIC_ROOT}"
export ACCEPT_EULA=Y OMNI_KIT_ACCEPT_EULA=YES PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

"${PYTHON}" gear_sonic/train_agent_trl.py \
  +exp=manager/universal_token/all_modes/sonic_release \
  +checkpoint="${CHECKPOINT}" num_envs="${NUM_ENVS}" headless=True \
  ++experiment_name="${EXPERIMENT_NAME}" ++resume=false \
  ++algo.config.num_learning_iterations="${ITERATIONS}" \
  ++algo.config.save_interval="${SAVE_INTERVAL}" \
  ++callbacks.model_save.save_dir="${OUTPUT_DIR}/checkpoints" \
  ++callbacks.model_save.save_frequency="${SAVE_INTERVAL}" \
  ++callbacks.model_save.save_last_frequency="${SAVE_INTERVAL}" \
  ++algo.config.actor_learning_rate=3.0e-7 \
  ++algo.config.adaptive_lr_min=1.0e-7 ++algo.config.adaptive_lr_max=1.0e-6 \
  ++algo.config.desired_kl=0.0008 \
  ++manager_env.commands.motion.motion_lib_cfg.motion_file="${MOTION_FILE}" \
  ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy \
  ++manager_env.commands.motion.start_from_first_frame=true \
  ++manager_env.commands.motion.motion_lib_cfg.adaptive_sampling.bin_size=25 \
  ++manager_env.commands.motion.motion_lib_cfg.adaptive_sampling.pre_failure_sample_window=125 \
  '~manager_env.terminations.anchor_pos' '~manager_env.terminations.ee_body_pos' '~manager_env.terminations.foot_pos_xyz' \
  ++manager_env.terminations.anchor_ori_full.func=sonic_debug.phase_rewards:phase_aware_base_safety \
  '~manager_env.terminations.anchor_ori_full.params.asset_cfg' '~manager_env.terminations.anchor_ori_full.params.threshold' \
  ++manager_env.terminations.anchor_ori_full.params.command_name=motion \
  ++manager_env.terminations.anchor_ori_full.params.recovery_settle_frame=336 \
  ++manager_env.terminations.anchor_ori_full.params.pre_recovery_tilt_error_rad=3.0 \
  ++manager_env.terminations.anchor_ori_full.params.pre_recovery_min_height=0.2 \
  ++manager_env.terminations.anchor_ori_full.params.recovery_world_tilt_rad=0.45 \
  ++manager_env.terminations.anchor_ori_full.params.recovery_min_height=0.60 \
  '++manager_env.terminations.anchor_ori_full.params.unsafe_contact_body_names=[pelvis,pelvis_contour_link,torso_link,head_link]' \
  ++manager_env.terminations.anchor_ori_full.params.unsafe_contact_force=100.0 \
  ++manager_env.events.physics_material.params.static_friction_range='[0.5,1.3]' \
  ++manager_env.events.physics_material.params.dynamic_friction_range='[0.4,1.1]' \
  ++manager_env.events.physics_material.params.restitution_range='[0.0,0.2]' \
  ++manager_env.events.add_joint_default_pos.params.pos_distribution_params='[-0.01,0.01]' \
  ++manager_env.events.base_com.params.com_range.x='[-0.025,0.025]' \
  ++manager_env.events.base_com.params.com_range.y='[-0.03,0.03]' \
  ++manager_env.events.base_com.params.com_range.z='[-0.035,0.035]' \
  ++manager_env.events.randomize_rigid_body_mass.params.mass_distribution_params='[0.85,1.2]' \
  '++manager_env.events._target_=sonic_debug.phase_rewards.V8EventCfg' \
  '++manager_env.events.actuator_gains._target_=isaaclab.managers.EventTermCfg' \
  '++manager_env.events.actuator_gains.func=isaaclab.envs.mdp:randomize_actuator_gains' \
  '++manager_env.events.actuator_gains.mode=startup' \
  '++manager_env.events.actuator_gains.params.asset_cfg._target_=isaaclab.managers.SceneEntityCfg' \
  '++manager_env.events.actuator_gains.params.asset_cfg.name=robot' \
  '++manager_env.events.actuator_gains.params.asset_cfg.joint_names=[.*]' \
  '++manager_env.events.actuator_gains.params.stiffness_distribution_params=[0.9,1.1]' \
  '++manager_env.events.actuator_gains.params.damping_distribution_params=[0.8,1.2]' \
  '++manager_env.events.actuator_gains.params.operation=scale' \
  '++manager_env.events.actuator_gains.params.distribution=uniform' \
  manager_env.rewards.action_rate_l2.weight=-0.35 \
  "${V8_REWARD_OVERRIDES[@]}" \
  manager_env.rewards.landing_contact_overload.weight=-0.3 \
  manager_env.rewards.recovery_upright.weight=4.0 \
  manager_env.rewards.recovery_low_base_velocity.weight=5.0 \
  manager_env.rewards.recovery_center_of_support.weight=3.0 \
  manager_env.rewards.recovery_knee_torque_reserve.weight=-0.15 \
  manager_env.rewards.late_recovery_upright.weight=6.0 \
  manager_env.rewards.late_recovery_low_base_velocity.weight=5.0 \
  use_wandb=false 2>&1 | tee "${OUTPUT_DIR}/train.log"
