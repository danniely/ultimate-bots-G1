#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/srv/sonic/ultimate-bots-G1}"
ROOT="$PROJECT/exports/v6/selected_step300"
MATRIX_OUT="$ROOT/mujoco_matrix_retry1"
MODEL_DIR="$ROOT/onnx"
printf '%s mujoco_retry_started model_dir=%s\n' "$(date -Is)" "$MODEL_DIR" | tee -a "$ROOT/stages.log"
OUT="$MATRIX_OUT" RUNS=10 MODEL_STEP=000300 MODEL_DIR="$MODEL_DIR" \
bash "$PROJECT/scripts/run_v6_sim2sim_matrix.sh" >"$ROOT/mujoco_matrix_retry1.log" 2>&1
printf '%s mujoco_retry_completed\n' "$(date -Is)" | tee -a "$ROOT/stages.log"
