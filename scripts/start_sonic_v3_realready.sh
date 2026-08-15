#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/srv/sonic/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/sonic/ultimate-bots-G1}"
PYTHON="${PYTHON:-/srv/sonic/env_isaaclab/bin/python}"
CHECKPOINT="${CHECKPOINT:-${PROJECT_ROOT}/checkpoints/v3/s_batido_v3_recovery_step_000600.pt}"
MOTION_FILE="${MOTION_FILE:-${PROJECT_ROOT}/data/motion_lib/s_batido_v3_recovery.pkl}"
NUM_ENVS="${NUM_ENVS:-512}"
ITERATIONS="${ITERATIONS:-300}"
SAVE_INTERVAL="${SAVE_INTERVAL:-50}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-s_batido_v3_realready}"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/exports/v3/realready/train}"
LOG_FILE="${OUTPUT_DIR}/train.log"

source "${PROJECT_ROOT}/scripts/v3_robust_reward_overrides.sh"
mkdir -p "${OUTPUT_DIR}"
cd "${SONIC_ROOT}"

export ACCEPT_EULA=Y
export OMNI_KIT_ACCEPT_EULA=YES
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

# The Studio reference contains impossible ground penetration and an inflated
# pelvis jump.  Train against physical failure signals rather than terminating
# on those reference-coordinate errors.  The acrobatic phase allows large
# heading/tilt changes, but a pelvis/torso/head ground strike ends the episode;
# recovery must settle upright above a minimum pelvis height.
"${PYTHON}" gear_sonic/train_agent_trl.py \
  +exp=manager/universal_token/all_modes/sonic_release \
  +checkpoint="${CHECKPOINT}" \
  num_envs="${NUM_ENVS}" \
  headless=True \
  ++experiment_name="${EXPERIMENT_NAME}" \
  ++resume=false \
  ++algo.config.num_learning_iterations="${ITERATIONS}" \
  ++algo.config.save_interval="${SAVE_INTERVAL}" \
  ++algo.config.actor_learning_rate=1.0e-6 \
  ++algo.config.adaptive_lr_min=2.5e-7 \
  ++algo.config.adaptive_lr_max=4.0e-6 \
  ++algo.config.desired_kl=0.002 \
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
  ++manager_env.terminations.anchor_ori_full.params.recovery_world_tilt_rad=0.8 \
  ++manager_env.terminations.anchor_ori_full.params.recovery_min_height=0.5 \
  '++manager_env.terminations.anchor_ori_full.params.unsafe_contact_body_names=[pelvis,pelvis_contour_link,torso_link,head_link]' \
  ++manager_env.terminations.anchor_ori_full.params.unsafe_contact_force=100.0 \
  ++manager_env.events.physics_material.params.static_friction_range='[0.6,1.2]' \
  ++manager_env.events.physics_material.params.dynamic_friction_range='[0.5,1.0]' \
  ++manager_env.events.physics_material.params.restitution_range='[0.0,0.15]' \
  ++manager_env.events.add_joint_default_pos.params.pos_distribution_params='[-0.005,0.005]' \
  ++manager_env.events.base_com.params.com_range.x='[-0.015,0.015]' \
  ++manager_env.events.base_com.params.com_range.y='[-0.02,0.02]' \
  ++manager_env.events.base_com.params.com_range.z='[-0.025,0.025]' \
  ++manager_env.events.randomize_rigid_body_mass.params.mass_distribution_params='[0.9,1.15]' \
  ++manager_env.events.push_robot.interval_range_s='[2.0,2.8]' \
  ++manager_env.events.push_robot.params.velocity_range.x='[-0.15,0.15]' \
  ++manager_env.events.push_robot.params.velocity_range.y='[-0.15,0.15]' \
  ++manager_env.events.push_robot.params.velocity_range.z='[-0.05,0.05]' \
  ++manager_env.events.push_robot.params.velocity_range.roll='[-0.2,0.2]' \
  ++manager_env.events.push_robot.params.velocity_range.pitch='[-0.2,0.2]' \
  ++manager_env.events.push_robot.params.velocity_range.yaw='[-0.2,0.2]' \
  "${V3_ROBUST_REWARD_OVERRIDES[@]}" \
  use_wandb=false \
  2>&1 | tee "${LOG_FILE}"
