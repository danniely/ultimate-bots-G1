#!/usr/bin/env bash
set -uo pipefail

RUNS="${RUNS:-10}"
INIT_TIMEOUT="${INIT_TIMEOUT:-30}"
PROJECT="${PROJECT:-/srv/sonic/ultimate-bots-G1}"
OFFICIAL="${OFFICIAL:-/srv/sonic/GR00T-WholeBodyControl}"
OUT="${OUT:-$PROJECT/exports/v7/stand_diagnostic}"
MODEL_DIR="${MODEL_DIR:-$PROJECT/exports/v6/selected_step300/onnx}"
MODEL_STEP="${MODEL_STEP:-000300}"
REFERENCE="${REFERENCE:-reference/s_batido_v6_buffered}"
DEPLOY="$OFFICIAL/gear_sonic_deploy/target/release/g1_deploy_onnx_ref"
TRT_LIB="/srv/sonic/env_isaaclab/lib/python3.11/site-packages/tensorrt_libs"
ORT_LIB="/srv/sonic/deps/onnxruntime-linux-x64-1.22.0/lib"
PYTHON="${PYTHON:-$OFFICIAL/.venv_sim/bin/python}"

mkdir -p "$OUT"
: >"$OUT/progress.log"

cleanup_children() {
  tmux send-keys -t v7_stand_deploy C-c 2>/dev/null || true
  tmux send-keys -t v7_stand_sim C-c 2>/dev/null || true
  sleep 1
  tmux kill-session -t v7_stand_deploy 2>/dev/null || true
  tmux kill-session -t v7_stand_sim 2>/dev/null || true
  pkill -f '[g]1_deploy_onnx_ref.*s_batido_v6_buffered' 2>/dev/null || true
  pkill -f '[r]un_mujoco_headless_release.py' 2>/dev/null || true
  sleep 2
}
trap cleanup_children EXIT

for run in $(seq -w 1 "$RUNS"); do
  run_dir="$OUT/run_$run"
  mkdir -p "$run_dir/logs"
  : >"$run_dir/sim.log"
  : >"$run_dir/deploy.log"
  cleanup_children

  # The elastic safety band remains enabled for this entire diagnostic. This
  # isolates controller engagement and standing oscillation from the kick.
  tmux new-session -d -s v7_stand_sim \
    "bash -lc 'cd $OFFICIAL; source .venv_sim/bin/activate; export PYTHONPATH=\$PWD; exec python $PROJECT/scripts/run_mujoco_headless_release.py --release-after 120 > $run_dir/sim.log 2>&1'"
  sleep 6
  if ! tmux has-session -t v7_stand_sim 2>/dev/null; then
    echo "run_$run sim_init_failed" | tee -a "$OUT/progress.log"
    cleanup_children
    continue
  fi

  tmux new-session -d -s v7_stand_deploy \
    "bash -lc 'export LD_LIBRARY_PATH=$TRT_LIB:$ORT_LIB:\$LD_LIBRARY_PATH; cd $OFFICIAL/gear_sonic_deploy; exec $DEPLOY lo $MODEL_DIR/model_step_${MODEL_STEP}_decoder.onnx $REFERENCE --obs-config $MODEL_DIR/observation_config.yaml --encoder-file $MODEL_DIR/model_step_${MODEL_STEP}_encoder.onnx --input-type keyboard --output-type zmq --disable-crc-check --enable-csv-logs --logs-dir $run_dir/logs > $run_dir/deploy.log 2>&1'"

  ready=0
  for _ in $(seq 1 180); do
    if grep -q "Init Done" "$run_dir/deploy.log"; then ready=1; break; fi
    tmux has-session -t v7_stand_deploy 2>/dev/null || break
    sleep 1
  done
  if [[ "$ready" != 1 ]]; then
    echo "run_$run deploy_init_failed" | tee -a "$OUT/progress.log"
    cleanup_children
    continue
  fi

  # Engage the official standing controller, but never send the motion command.
  tmux send-keys -t v7_stand_deploy "]"
  if "$PYTHON" "$PROJECT/scripts/wait_for_sim2sim_settle.py" "$run_dir/logs" \
      --timeout "$INIT_TIMEOUT" --consecutive 25 --min-upright 0.95 \
      --max-joint-speed 2.5 --max-base-angular-speed 0.6 \
      --output "$run_dir/initial_settle.json" >"$run_dir/settle.log" 2>&1; then
    echo "run_$run settled" | tee -a "$OUT/progress.log"
  else
    echo "run_$run settle_failed" | tee -a "$OUT/progress.log"
  fi
  cleanup_children
done

cleanup_children
"$PYTHON" "$PROJECT/scripts/summarize_v7_stand_diagnostic.py" "$OUT"
