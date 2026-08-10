#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/workspace/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/workspace/ultimate-bots-G1}"
PYTHON="${PYTHON:-/opt/env_isaaclab/bin/python}"
: "${CHECKPOINT:?Set CHECKPOINT to the selected v2 stage1 checkpoint}"
MOTION_FILE="${MOTION_FILE:-${PROJECT_ROOT}/data/motion_lib/s_batido_test.pkl}"
OUTPUT_DIR="${PROJECT_ROOT}/exports/v2/stage2"
LOG_FILE="${OUTPUT_DIR}/train.log"

source "${PROJECT_ROOT}/scripts/v2_reward_overrides.sh"
mkdir -p "${OUTPUT_DIR}"
cd "${SONIC_ROOT}"

export ACCEPT_EULA=Y
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

"${PYTHON}" gear_sonic/train_agent_trl.py \
  +exp=manager/universal_token/all_modes/sonic_release \
  +checkpoint="${CHECKPOINT}" \
  num_envs=512 \
  headless=True \
  ++experiment_name=s_batido_v2_stage2 \
  ++resume=false \
  ++algo.config.num_learning_iterations=1000 \
  ++algo.config.save_interval=100 \
  ++algo.config.actor_learning_rate=5.0e-6 \
  ++algo.config.adaptive_lr_min=1.0e-6 \
  ++algo.config.adaptive_lr_max=2.0e-5 \
  ++algo.config.desired_kl=0.005 \
  ++manager_env.commands.motion.motion_lib_cfg.motion_file="${MOTION_FILE}" \
  ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy \
  "${V2_REWARD_OVERRIDES[@]}" \
  use_wandb=false \
  2>&1 | tee "${LOG_FILE}"
