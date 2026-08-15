#!/usr/bin/env bash
set -euo pipefail

PROJECT="${PROJECT:-/srv/sonic/ultimate-bots-G1}"
CHECKPOINT="$PROJECT/checkpoints/v6/intermediate/s_batido_v6_buffered_step_000300.pt"
MOTION_FILE="$PROJECT/data/motion_lib/s_batido_v6_buffered.pkl"
SELECTED="$PROJECT/checkpoints/v6/selected_step300"
OUT="$PROJECT/exports/v6/selected_step300"
ONNX_SOURCE="$PROJECT/exports/v6/intermediate_screen/step_000300/onnx"

mkdir -p "$SELECTED" "$OUT"
: >"$OUT/stages.log"
stage() { printf '%s %s\n' "$(date -Is)" "$1" | tee -a "$OUT/stages.log"; }

stage preserve_selected_checkpoint
cp "$CHECKPOINT" "$SELECTED/s_batido_v6_buffered_step_000300.pt.tmp"
mv "$SELECTED/s_batido_v6_buffered_step_000300.pt.tmp" "$SELECTED/s_batido_v6_buffered_step_000300.pt"
cp "$PROJECT/checkpoints/v6/intermediate/config.yaml" "$SELECTED/config.yaml"
(cd "$SELECTED" && sha256sum s_batido_v6_buffered_step_000300.pt > SHA256SUMS)

stage isaac_matrix_started
CHECKPOINT="$CHECKPOINT" MOTION_FILE="$MOTION_FILE" \
RUN_ROOT="$OUT/isaac_matrix" bash "$PROJECT/scripts/run_v6_isaac_matrix.sh" \
  >"$OUT/isaac_matrix.log" 2>&1
stage isaac_matrix_completed

stage isaac_full_render_started
SONIC_ROOT="/srv/sonic/GR00T-WholeBodyControl" PROJECT_ROOT="$PROJECT" \
PYTHON="/srv/sonic/env_isaaclab/bin/python" \
CHECKPOINT="$CHECKPOINT" MOTION_FILE="$MOTION_FILE" \
RUN_ID="v6_selected_step300_full" FULL_MOTION=true \
bash "$PROJECT/scripts/run_sonic_eval_debug.sh" >"$OUT/isaac_render.log" 2>&1
stage isaac_full_render_completed

stage preserve_onnx
mkdir -p "$OUT/onnx"
cp "$ONNX_SOURCE"/*.onnx "$OUT/onnx/"
cp "$ONNX_SOURCE"/observation_config.yaml "$OUT/onnx/"
cp "$ONNX_SOURCE"/parity.json "$OUT/onnx/"

stage mujoco_matrix_started
MATRIX_OUT="$OUT/mujoco_matrix"
MODEL_DIR="$OUT/onnx"
OUT="$MATRIX_OUT" RUNS=10 MODEL_STEP=000300 MODEL_DIR="$MODEL_DIR" \
bash "$PROJECT/scripts/run_v6_sim2sim_matrix.sh" >"$OUT/mujoco_matrix.log" 2>&1
stage mujoco_matrix_completed
stage validation_completed
