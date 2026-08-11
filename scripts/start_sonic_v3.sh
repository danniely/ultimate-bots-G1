#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/srv/sonic/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/sonic/ultimate-bots-G1}"
PYTHON="${PYTHON:-/srv/sonic/env_isaaclab/bin/python}"
CHECKPOINT="${CHECKPOINT:-${PROJECT_ROOT}/checkpoints/v2/stage1/s_batido_v2_stage1_step_001000.pt}"
MOTION_FILE="${MOTION_FILE:-${PROJECT_ROOT}/data/motion_lib/s_batido_v3_recovery.pkl}"
NUM_ENVS="${NUM_ENVS:-512}"
ITERATIONS="${ITERATIONS:-750}"
SAVE_INTERVAL="${SAVE_INTERVAL:-50}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-s_batido_v3_recovery}"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/exports/v3/train}"
LOG_FILE="${OUTPUT_DIR}/train.log"

source "${PROJECT_ROOT}/scripts/v3_reward_overrides.sh"
mkdir -p "${OUTPUT_DIR}"
cd "${SONIC_ROOT}"

export ACCEPT_EULA=Y
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
  ++algo.config.actor_learning_rate=2.0e-6 \
  ++algo.config.adaptive_lr_min=5.0e-7 \
  ++algo.config.adaptive_lr_max=8.0e-6 \
  ++algo.config.desired_kl=0.003 \
  ++manager_env.commands.motion.motion_lib_cfg.motion_file="${MOTION_FILE}" \
  ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy \
  ++manager_env.commands.motion.motion_lib_cfg.adaptive_sampling.bin_size=25 \
  ++manager_env.commands.motion.motion_lib_cfg.adaptive_sampling.pre_failure_sample_window=100 \
  ++manager_env.terminations.anchor_ori_full.params.threshold=0.45 \
  ++manager_env.terminations.anchor_pos.params.threshold=0.25 \
  '~manager_env.terminations.ee_body_pos' \
  '~manager_env.terminations.foot_pos_xyz' \
  '~manager_env.events.physics_material' \
  '~manager_env.events.add_joint_default_pos' \
  '~manager_env.events.base_com' \
  '~manager_env.events.randomize_rigid_body_mass' \
  "${V3_REWARD_OVERRIDES[@]}" \
  use_wandb=false \
  2>&1 | tee "${LOG_FILE}"
