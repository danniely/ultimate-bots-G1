#!/usr/bin/env bash
set -u

PROJECT="${PROJECT:-/srv/sonic/ultimate-bots-G1}"
MOTION_FILE="${MOTION_FILE:-$PROJECT/data/motion_lib/s_batido_v6_buffered.pkl}"
ROOT="${ROOT:-$PROJECT/exports/v6/intermediate_screen}"
STEPS="${STEPS:-100 150 200 250 300 350}"

mkdir -p "$ROOT"
: >"$ROOT/progress.log"

for step in $STEPS; do
  padded="$(printf '%06d' "$step")"
  checkpoint="$PROJECT/checkpoints/v6/intermediate/s_batido_v6_buffered_step_${padded}.pt"
  step_root="$ROOT/step_${padded}"
  onnx_dir="$step_root/onnx"
  matrix_dir="$step_root/mujoco"
  mkdir -p "$step_root"

  printf '%s step_%s export_started\n' "$(date -Is)" "$padded" | tee -a "$ROOT/progress.log"
  if ! CHECKPOINT="$checkpoint" MOTION_FILE="$MOTION_FILE" OUTPUT_DIR="$onnx_dir" \
      bash "$PROJECT/scripts/export_v6_onnx.sh" >"$step_root/export.log" 2>&1; then
    printf '%s step_%s export_failed\n' "$(date -Is)" "$padded" | tee -a "$ROOT/progress.log"
    continue
  fi

  printf '%s step_%s mujoco_started\n' "$(date -Is)" "$padded" | tee -a "$ROOT/progress.log"
  OUT="$matrix_dir" RUNS=1 MODEL_STEP="$padded" MODEL_DIR="$onnx_dir" \
    bash "$PROJECT/scripts/run_v6_sim2sim_matrix.sh" >"$step_root/mujoco.log" 2>&1
  rc=$?
  printf '%s step_%s mujoco_finished rc=%s\n' "$(date -Is)" "$padded" "$rc" | tee -a "$ROOT/progress.log"
done

printf '%s screening_completed\n' "$(date -Is)" | tee -a "$ROOT/progress.log"
