#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/srv/sonic/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/sonic/ultimate-bots-G1}"
PYTHON="${PYTHON:-/srv/sonic/env_isaaclab/bin/python}"
CHECKPOINT="${CHECKPOINT:?Set CHECKPOINT to the selected V6 checkpoint}"
MOTION_FILE="${MOTION_FILE:-${PROJECT_ROOT}/data/motion_lib/s_batido_v6_buffered.pkl}"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/exports/v6/final/onnx}"

mkdir -p "${OUTPUT_DIR}"
cd "${SONIC_ROOT}"
export ACCEPT_EULA=Y
export OMNI_KIT_ACCEPT_EULA=YES
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
export SONIC_PARITY_REPORT="${OUTPUT_DIR}/parity.json"

"${PYTHON}" "${PROJECT_ROOT}/scripts/run_eval_export_with_parity.py" \
  +checkpoint="${CHECKPOINT}" +num_envs=1 +headless=true +export_onnx_only=true \
  ++manager_env.commands.motion.motion_lib_cfg.motion_file="${MOTION_FILE}" \
  ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy \
  2>&1 | tee "${OUTPUT_DIR}/export.log"

cp "$(dirname "${CHECKPOINT}")/exported/"*.onnx "${OUTPUT_DIR}/"
cp "${PROJECT_ROOT}/exports/v5/stability/stage2_final/onnx/observation_config.yaml" \
  "${OUTPUT_DIR}/observation_config.yaml"
