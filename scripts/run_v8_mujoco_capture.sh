#!/usr/bin/env bash
set -uo pipefail

ATTEMPTS="${ATTEMPTS:-5}"
PROJECT="${PROJECT:-/srv/sonic/ultimate-bots-G1}"
OFFICIAL="${OFFICIAL:-/srv/sonic/GR00T-WholeBodyControl}"
OUT="${OUT:-$PROJECT/exports/v8/final/mujoco_capture}"
MODEL_DIR="${MODEL_DIR:-$PROJECT/exports/v8/candidates/step025/onnx}"
MODEL_STEP="${MODEL_STEP:-000025}"
REFERENCE="${REFERENCE:-reference/s_batido_v8_landing}"
DEPLOY="$OFFICIAL/gear_sonic_deploy/target/release/g1_deploy_onnx_ref"
TRT_LIB="/srv/sonic/env_isaaclab/lib/python3.11/site-packages/tensorrt_libs"
ORT_LIB="/srv/sonic/deps/onnxruntime-linux-x64-1.22.0/lib"
PYTHON="${PYTHON:-$OFFICIAL/.venv_sim/bin/python}"

mkdir -p "$OUT" "$PROJECT/videos/v8"
cleanup_children() {
  tmux send-keys -t g1_deploy C-c 2>/dev/null || true
  tmux send-keys -t sim_capture C-c 2>/dev/null || true
  sleep 1
  tmux kill-session -t g1_deploy 2>/dev/null || true
  tmux kill-session -t sim_capture 2>/dev/null || true
  pkill -f '[g]1_deploy_onnx_ref.*s_batido_v8_landing' 2>/dev/null || true
  pkill -f '[r]un_mujoco_headless_capture.py' 2>/dev/null || true
}
trap cleanup_children EXIT

for attempt in $(seq -w 1 "$ATTEMPTS"); do
  run_dir="$OUT/run_$attempt"
  mkdir -p "$run_dir/logs"
  : >"$run_dir/deploy.log"
  : >"$run_dir/sim.log"
  release_file="$run_dir/release_band"
  stop_file="$run_dir/stop_capture"
  rm -f "$release_file" "$stop_file"
  cleanup_children

  tmux new-session -d -s sim_capture \
    "bash -lc 'export MUJOCO_GL=egl; cd $OFFICIAL; source .venv_sim/bin/activate; export PYTHONPATH=\$PWD; exec python $PROJECT/scripts/run_mujoco_headless_capture.py --output $run_dir/mujoco.mp4 --release-after 60 --release-file $release_file --stop-file $stop_file --max-seconds 30 > $run_dir/sim.log 2>&1'"
  sleep 8
  tmux has-session -t sim_capture 2>/dev/null || { echo "run_$attempt capture_init_failed"; continue; }
  tmux new-session -d -s g1_deploy \
    "bash -lc 'export LD_LIBRARY_PATH=$TRT_LIB:$ORT_LIB:\$LD_LIBRARY_PATH; cd $OFFICIAL/gear_sonic_deploy; exec $DEPLOY lo $MODEL_DIR/model_step_${MODEL_STEP}_decoder.onnx $REFERENCE --obs-config $MODEL_DIR/observation_config.yaml --encoder-file $MODEL_DIR/model_step_${MODEL_STEP}_encoder.onnx --input-type keyboard --output-type zmq --disable-crc-check --enable-csv-logs --logs-dir $run_dir/logs > $run_dir/deploy.log 2>&1'"
  ready=0
  for _ in $(seq 1 180); do
    grep -q "Init Done" "$run_dir/deploy.log" && { ready=1; break; }
    tmux has-session -t g1_deploy 2>/dev/null || break
    sleep 1
  done
  [[ "$ready" == 1 ]] || { echo "run_$attempt init_failed"; touch "$stop_file"; continue; }
  tmux send-keys -t g1_deploy "]"
  touch "$release_file"
  if ! "$PYTHON" "$PROJECT/scripts/wait_for_sim2sim_settle.py" "$run_dir/logs" \
      --timeout 25 --consecutive 25 --min-upright 0.95 \
      --max-joint-speed 2.5 --max-base-angular-speed 0.6 \
      --output "$run_dir/initial_settle.json"; then
    echo "run_$attempt initial_settle_failed"
    touch "$stop_file"
    continue
  fi
  tmux send-keys -t g1_deploy "T"
  for _ in $(seq 1 30); do
    grep -q "completed\." "$run_dir/deploy.log" && break
    sleep 1
  done
  sleep 2
  touch "$stop_file"
  for _ in $(seq 1 20); do
    tmux has-session -t sim_capture 2>/dev/null || break
    sleep 0.5
  done
  cleanup_children
  "$PYTHON" "$PROJECT/scripts/summarize_v8_sim2sim_matrix.py" "$OUT" >/dev/null 2>&1 || true
  stable=$("$PYTHON" - "$OUT/summary.json" "$attempt" <<'PY'
import json, sys
d=json.load(open(sys.argv[1]))
name="run_"+sys.argv[2]
print(int(any(r.get("run")==name and r.get("final_stable") for r in d["runs"])))
PY
)
  if [[ "$stable" == 1 ]]; then
    cp "$run_dir/mujoco.mp4" "$PROJECT/videos/v8/v8_step025_mujoco_closed_loop.mp4"
    echo "CAPTURE_SUCCESS run_$attempt"
    exit 0
  fi
done

echo "CAPTURE_NO_STABLE_RUN" >&2
exit 1
