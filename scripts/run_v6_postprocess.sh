#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/srv/sonic/ultimate-bots-G1}"
SONIC_ROOT="${SONIC_ROOT:-/srv/sonic/GR00T-WholeBodyControl}"
RUN_DIR="${RUN_DIR:-${SONIC_ROOT}/logs_rl/TRL_G1_Track/s_batido_v6_buffered-20260815_090551}"
TRAIN_SESSION="${TRAIN_SESSION:-sonic_v6_train}"
MOTION_FILE="${PROJECT_ROOT}/data/motion_lib/s_batido_v6_buffered.pkl"
FINAL_DIR="${PROJECT_ROOT}/checkpoints/v6/final"
FINAL_CHECKPOINT="${FINAL_DIR}/s_batido_v6_buffered_step_000400.pt"
STATUS_DIR="${PROJECT_ROOT}/exports/v6/postprocess"

mkdir -p "${FINAL_DIR}" "${STATUS_DIR}"
stage() { printf '%s %s\n' "$(date -Is)" "$1" | tee -a "${STATUS_DIR}/stages.log"; }

stage "waiting_for_training"
while tmux has-session -t "${TRAIN_SESSION}" 2>/dev/null; do sleep 60; done
if ! grep -q 'EXIT:0' "${PROJECT_ROOT}/exports/v6/train/driver.log"; then
  stage "training_failed_or_incomplete"
  exit 2
fi

stage "preserving_final_checkpoint"
cp "${RUN_DIR}/last.pt" "${FINAL_CHECKPOINT}.tmp"
mv "${FINAL_CHECKPOINT}.tmp" "${FINAL_CHECKPOINT}"
cp "${RUN_DIR}/config.yaml" "${FINAL_DIR}/config.yaml"
(cd "${FINAL_DIR}" && sha256sum "$(basename "${FINAL_CHECKPOINT}")" > SHA256SUMS)

stage "isaac_matrix_started"
CHECKPOINT="${FINAL_CHECKPOINT}" \
MOTION_FILE="${MOTION_FILE}" \
RUN_ROOT="${PROJECT_ROOT}/exports/v6/final/isaac_matrix" \
bash "${PROJECT_ROOT}/scripts/run_v6_isaac_matrix.sh" \
  > "${STATUS_DIR}/isaac_matrix.log" 2>&1
stage "isaac_matrix_completed"

stage "isaac_full_render_started"
SONIC_ROOT="${SONIC_ROOT}" PROJECT_ROOT="${PROJECT_ROOT}" \
PYTHON="/srv/sonic/env_isaaclab/bin/python" \
CHECKPOINT="${FINAL_CHECKPOINT}" MOTION_FILE="${MOTION_FILE}" \
RUN_ID="v6_final_full" FULL_MOTION=true \
bash "${PROJECT_ROOT}/scripts/run_sonic_eval_debug.sh" \
  > "${STATUS_DIR}/isaac_render.log" 2>&1
stage "isaac_full_render_completed"

stage "onnx_export_started"
CHECKPOINT="${FINAL_CHECKPOINT}" \
MOTION_FILE="${MOTION_FILE}" \
OUTPUT_DIR="${PROJECT_ROOT}/exports/v6/final/onnx" \
bash "${PROJECT_ROOT}/scripts/export_v6_onnx.sh" \
  > "${STATUS_DIR}/onnx_export.log" 2>&1
stage "onnx_export_completed"

stage "mujoco_matrix_started"
RUNS=10 MODEL_STEP=000400 \
OUT="${PROJECT_ROOT}/exports/v6/final/mujoco_matrix" \
MODEL_DIR="${PROJECT_ROOT}/exports/v6/final/onnx" \
REFERENCE="reference/s_batido_v6_buffered" \
bash "${PROJECT_ROOT}/scripts/run_v6_sim2sim_matrix.sh" \
  > "${STATUS_DIR}/mujoco_matrix.log" 2>&1
stage "mujoco_matrix_completed"
stage "all_required_cross_validation_completed"
