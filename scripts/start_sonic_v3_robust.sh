#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/srv/sonic/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/sonic/ultimate-bots-G1}"
PYTHON="${PYTHON:-/srv/sonic/env_isaaclab/bin/python}"
CHECKPOINT="${CHECKPOINT:-${PROJECT_ROOT}/checkpoints/v3/s_batido_v3_recovery_step_000600.pt}"
MOTION_FILE="${MOTION_FILE:-${PROJECT_ROOT}/data/motion_lib/s_batido_v3_recovery.pkl}"
NUM_ENVS="${NUM_ENVS:-512}"
ITERATIONS="${ITERATIONS:-400}"
SAVE_INTERVAL="${SAVE_INTERVAL:-50}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-s_batido_v3_robust}"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/exports/v3/robust/train}"
LOG_FILE="${OUTPUT_DIR}/train.log"

source "${PROJECT_ROOT}/scripts/v3_robust_reward_overrides.sh"
mkdir -p "${OUTPUT_DIR}"
cd "${SONIC_ROOT}"

export ACCEPT_EULA=Y
export OMNI_KIT_ACCEPT_EULA=YES
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

# Unlike start_sonic_v3.sh, this pass keeps every stock termination and startup
# randomization.  The ranges are narrowed from the very aggressive SONIC
# defaults so the policy learns robustness without immediately forgetting the
# airborne highlight.  The interval push is moved into the recovery window.
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
