#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/srv/sonic/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/sonic/ultimate-bots-G1}"
PYTHON="${PYTHON:-/srv/sonic/env_isaaclab/bin/python}"
CHECKPOINT="${CHECKPOINT:-${PROJECT_ROOT}/checkpoints/v3/realready/s_batido_v3_realready_step_000100.pt}"
MOTION_FILE="${MOTION_FILE:-${PROJECT_ROOT}/data/motion_lib/s_batido_v3_recovery.pkl}"
NUM_ENVS="${NUM_ENVS:-512}"
ITERATIONS="${ITERATIONS:-250}"
SAVE_INTERVAL="${SAVE_INTERVAL:-25}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-s_batido_v5_stability}"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/exports/v5/stability/train}"
LOG_FILE="${OUTPUT_DIR}/train.log"

source "${PROJECT_ROOT}/scripts/v5_stability_reward_overrides.sh"
mkdir -p "${OUTPUT_DIR}"
cd "${SONIC_ROOT}"

export ACCEPT_EULA=Y
export OMNI_KIT_ACCEPT_EULA=YES
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

"${PYTHON}" gear_sonic/train_agent_trl.py \
  +exp=manager/universal_token/all_modes/sonic_release \
  +checkpoint="${CHECKPOINT}" \
  num_envs="${NUM_ENVS}" \
  headless=True \
  ++experiment_name="${EXPERIMENT_NAME}" \
  ++resume=false \
  ++algo.config.num_learning_iterations="${ITERATIONS}" \
  ++algo.config.save_interval="${SAVE_INTERVAL}" \
  ++algo.config.actor_learning_rate=7.5e-7 \
  ++algo.config.adaptive_lr_min=2.0e-7 \
  ++algo.config.adaptive_lr_max=2.5e-6 \
  ++algo.config.desired_kl=0.0015 \
  ++manager_env.commands.motion.motion_lib_cfg.motion_file="${MOTION_FILE}" \
  ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy \
  ++manager_env.commands.motion.motion_lib_cfg.adaptive_sampling.bin_size=25 \
  ++manager_env.commands.motion.motion_lib_cfg.adaptive_sampling.pre_failure_sample_window=100 \
  '~manager_env.terminations.anchor_pos' \
  '~manager_env.terminations.ee_body_pos' \
  '~manager_env.terminations.foot_pos_xyz' \
  ++manager_env.terminations.anchor_ori_full.func=sonic_debug.phase_rewards:phase_aware_base_safety \
  '~manager_env.terminations.anchor_ori_full.params.asset_cfg' \
  '~manager_env.terminations.anchor_ori_full.params.threshold' \
  ++manager_env.terminations.anchor_ori_full.params.command_name=motion \
  ++manager_env.terminations.anchor_ori_full.params.recovery_settle_frame=131 \
  ++manager_env.terminations.anchor_ori_full.params.pre_recovery_tilt_error_rad=3.0 \
  ++manager_env.terminations.anchor_ori_full.params.pre_recovery_min_height=0.2 \
  ++manager_env.terminations.anchor_ori_full.params.recovery_world_tilt_rad=0.7 \
  ++manager_env.terminations.anchor_ori_full.params.recovery_min_height=0.52 \
  '++manager_env.terminations.anchor_ori_full.params.unsafe_contact_body_names=[pelvis,pelvis_contour_link,torso_link,head_link]' \
  ++manager_env.terminations.anchor_ori_full.params.unsafe_contact_force=100.0 \
  ++manager_env.events.physics_material.params.static_friction_range='[0.55,1.25]' \
  ++manager_env.events.physics_material.params.dynamic_friction_range='[0.45,1.05]' \
  ++manager_env.events.physics_material.params.restitution_range='[0.0,0.18]' \
  ++manager_env.events.add_joint_default_pos.params.pos_distribution_params='[-0.0075,0.0075]' \
  ++manager_env.events.base_com.params.com_range.x='[-0.02,0.02]' \
  ++manager_env.events.base_com.params.com_range.y='[-0.025,0.025]' \
  ++manager_env.events.base_com.params.com_range.z='[-0.03,0.03]' \
  ++manager_env.events.randomize_rigid_body_mass.params.mass_distribution_params='[0.88,1.18]' \
  ++manager_env.events.push_robot.interval_range_s='[2.1,3.1]' \
  ++manager_env.events.push_robot.params.velocity_range.x='[-0.18,0.18]' \
  ++manager_env.events.push_robot.params.velocity_range.y='[-0.18,0.18]' \
  ++manager_env.events.push_robot.params.velocity_range.z='[-0.05,0.05]' \
  ++manager_env.events.push_robot.params.velocity_range.roll='[-0.22,0.22]' \
  ++manager_env.events.push_robot.params.velocity_range.pitch='[-0.22,0.22]' \
  ++manager_env.events.push_robot.params.velocity_range.yaw='[-0.22,0.22]' \
  manager_env.rewards.action_rate_l2.weight=-0.20 \
  "${V5_STABILITY_REWARD_OVERRIDES[@]}" \
  manager_env.rewards.recovery_upright.weight=2.5 \
  manager_env.rewards.recovery_low_base_velocity.weight=1.5 \
  manager_env.rewards.recovery_center_of_support.weight=2.0 \
  manager_env.rewards.support_contact.weight=1.5 \
  use_wandb=false \
  2>&1 | tee "${LOG_FILE}"
