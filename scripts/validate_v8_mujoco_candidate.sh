#!/usr/bin/env bash
set -euo pipefail

STEP="${STEP:?Set STEP, for example 000275}"
PROJECT="${PROJECT:-/srv/sonic/ultimate-bots-G1}"
RUNS="${RUNS:-10}"
LABEL="step${STEP#000}"
ROOT="${PROJECT}/exports/v8/candidates/${LABEL}"
CHECKPOINT="${PROJECT}/exports/v8/train/checkpoints/model_step_${STEP}.pt"

mkdir -p "${ROOT}/onnx" "${ROOT}/mujoco_matrix"
CHECKPOINT="${CHECKPOINT}" OUTPUT_DIR="${ROOT}/onnx" \
  bash "${PROJECT}/scripts/export_v8_onnx.sh" >"${ROOT}/onnx/driver.log" 2>&1
echo "ONNX_EXIT=0" >>"${ROOT}/onnx/driver.log"

: >"${ROOT}/mujoco_matrix/progress.log"
RUNS="${RUNS}" OUT="${ROOT}/mujoco_matrix" MODEL_DIR="${ROOT}/onnx" MODEL_STEP="${STEP}" \
  bash "${PROJECT}/scripts/run_v8_sim2sim_matrix.sh" >"${ROOT}/mujoco_matrix/driver.log" 2>&1
echo "MUJOCO_EXIT=0" >>"${ROOT}/mujoco_matrix/driver.log"
