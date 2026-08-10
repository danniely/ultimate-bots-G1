#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/workspace/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/workspace/ultimate-bots-G1}"
PYTHON="${PYTHON:-/opt/env_isaaclab/bin/python}"
CHECKPOINT="${CHECKPOINT:-${PROJECT_ROOT}/checkpoints/v1/s_batido_sonic_v1_step_002000.pt}"
MOTION_FILE="${MOTION_FILE:-${PROJECT_ROOT}/data/motion_lib/s_batido_test.pkl}"
NUM_ENVS="${NUM_ENVS:-512}"
ITERATIONS="${ITERATIONS:-1000}"
SAVE_INTERVAL="${SAVE_INTERVAL:-100}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-s_batido_v2_stage1}"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/exports/v2/stage1}"
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
  num_envs="${NUM_ENVS}" \
  headless=True \
  ++experiment_name="${EXPERIMENT_NAME}" \
  ++resume=false \
  ++algo.config.num_learning_iterations="${ITERATIONS}" \
  ++algo.config.save_interval="${SAVE_INTERVAL}" \
  ++algo.config.actor_learning_rate=5.0e-6 \
  ++algo.config.adaptive_lr_min=1.0e-6 \
  ++algo.config.adaptive_lr_max=2.0e-5 \
  ++algo.config.desired_kl=0.005 \
  ++manager_env.commands.motion.motion_lib_cfg.motion_file="${MOTION_FILE}" \
  ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy \
  '~manager_env.terminations.ee_body_pos' \
  '~manager_env.terminations.foot_pos_xyz' \
  '~manager_env.events.physics_material' \
  '~manager_env.events.add_joint_default_pos' \
  '~manager_env.events.base_com' \
  '~manager_env.events.randomize_rigid_body_mass' \
  "${V2_REWARD_OVERRIDES[@]}" \
  use_wandb=false \
  2>&1 | tee "${LOG_FILE}"
