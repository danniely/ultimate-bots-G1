#!/usr/bin/env bash
set -uo pipefail

RUNS="${RUNS:-10}"
INIT_TIMEOUT="${INIT_TIMEOUT:-180}"
PROJECT="${PROJECT:-/srv/sonic/ultimate-bots-G1}"
OFFICIAL="${OFFICIAL:-/srv/sonic/GR00T-WholeBodyControl}"
OUT="${OUT:-$PROJECT/exports/v3/realready/final/sim2sim_matrix_settled}"
MODEL_DIR="${MODEL_DIR:-$PROJECT/exports/v3/realready/final/onnx}"
MODEL_STEP="${MODEL_STEP:-000100}"
REFERENCE="${REFERENCE:-reference/s_batido_v3_realready}"
DEPLOY="$OFFICIAL/gear_sonic_deploy/target/release/g1_deploy_onnx_ref"
TRT_LIB="/srv/sonic/env_isaaclab/lib/python3.11/site-packages/tensorrt_libs"
ORT_LIB="/srv/sonic/deps/onnxruntime-linux-x64-1.22.0/lib"

mkdir -p "$OUT"

cleanup_children() {
  tmux kill-session -t g1_deploy 2>/dev/null || true
  tmux kill-session -t sim_loop 2>/dev/null || true
}
trap cleanup_children EXIT

for run in $(seq -w 1 "$RUNS"); do
  run_dir="$OUT/run_$run"
  mkdir -p "$run_dir/logs"
  : >"$run_dir/sim.log"
  : >"$run_dir/deploy.log"
  release_file="$run_dir/release_band"
  rm -f "$release_file"
  cleanup_children

  tmux new-session -d -s sim_loop \
    "bash -lc 'cd $OFFICIAL; source .venv_sim/bin/activate; PYTHONPATH=\$PWD python $PROJECT/scripts/run_mujoco_headless_release.py --release-after 60 --release-file $release_file 2>&1 | tee $run_dir/sim.log'"
  sleep 6

  tmux new-session -d -s g1_deploy \
    "bash -lc 'export LD_LIBRARY_PATH=$TRT_LIB:$ORT_LIB:\$LD_LIBRARY_PATH; cd $OFFICIAL/gear_sonic_deploy; $DEPLOY lo $MODEL_DIR/model_step_${MODEL_STEP}_decoder.onnx $REFERENCE --obs-config $MODEL_DIR/observation_config.yaml --encoder-file $MODEL_DIR/model_step_${MODEL_STEP}_encoder.onnx --input-type keyboard --output-type zmq --disable-crc-check --enable-csv-logs --logs-dir $run_dir/logs 2>&1 | tee $run_dir/deploy.log'"

  ready=0
  for _ in $(seq 1 "$INIT_TIMEOUT"); do
    if grep -q "Init Done" "$run_dir/deploy.log"; then ready=1; break; fi
    tmux has-session -t g1_deploy 2>/dev/null || break
    sleep 1
  done
  if [[ "$ready" != 1 ]]; then
    echo "run_$run init_failed" | tee -a "$OUT/progress.log"
    cleanup_children
    continue
  fi

  tmux send-keys -t g1_deploy "]"
  if ! python3 "$PROJECT/scripts/wait_for_sim2sim_settle.py" "$run_dir/logs" \
      --timeout 25 --consecutive 25 --min-upright 0.95 \
      --max-joint-speed 2.5 --max-base-angular-speed 0.6 \
      --output "$run_dir/settle.json"; then
    echo "run_$run initial_settle_failed" | tee -a "$OUT/progress.log"
    cleanup_children
    continue
  fi
  tmux send-keys -t g1_deploy "T"
  touch "$release_file"
  for _ in $(seq 1 10); do
    grep -q "AUTO_RELEASE" "$run_dir/sim.log" && break
    sleep 0.1
  done

  completed=0
  for _ in $(seq 1 15); do
    if grep -q "completed\." "$run_dir/deploy.log"; then completed=1; break; fi
    tmux has-session -t g1_deploy 2>/dev/null || break
    sleep 1
  done
  sleep 2
  tmux send-keys -t g1_deploy "O" 2>/dev/null || true
  sleep 2
  echo "run_$run completed=$completed" | tee -a "$OUT/progress.log"
done

cleanup_children
