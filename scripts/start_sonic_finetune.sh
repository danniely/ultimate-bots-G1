#!/usr/bin/env bash
set -euo pipefail

# Run this script inside the RunPod container. The log and checkpoints live on
# /workspace so they survive a Pod stop/restart.
SONIC_ROOT="/workspace/GR00T-WholeBodyControl"
PROJECT_ROOT="/workspace/ultimate-bots-G1"
PYTHON="/opt/env_isaaclab/bin/python"
MOTION_FILE="${PROJECT_ROOT}/data/motion_lib/s_batido_test.pkl"
LOG_FILE="${PROJECT_ROOT}/train.log"

cd "${SONIC_ROOT}"
export ACCEPT_EULA=Y
export PYTHONUNBUFFERED=1

exec "${PYTHON}" gear_sonic/train_agent_trl.py \
  +exp=manager/universal_token/all_modes/sonic_release \
  +checkpoint=sonic_release/last.pt \
  num_envs=512 \
  headless=True \
  ++algo.config.num_learning_iterations=2000 \
  ++algo.config.save_interval=100 \
  ++manager_env.commands.motion.motion_lib_cfg.motion_file="${MOTION_FILE}" \
  ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy \
  use_wandb=false \
  2>&1 | tee "${LOG_FILE}"
