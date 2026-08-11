#!/usr/bin/env bash
set -euo pipefail

# Run inside RunPod. Video and frame-level telemetry share one run ID.
SONIC_ROOT="${SONIC_ROOT:-/workspace/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/workspace/ultimate-bots-G1}"
PYTHON="${PYTHON:-/opt/env_isaaclab/bin/python}"
CHECKPOINT="${CHECKPOINT:-${PROJECT_ROOT}/checkpoints/final/s_batido_sonic_step_002000.pt}"
MOTION_FILE="${MOTION_FILE:-${PROJECT_ROOT}/data/motion_lib/s_batido_test.pkl}"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)_step2000}"
FULL_MOTION="${FULL_MOTION:-false}"
RUN_ROOT="${PROJECT_ROOT}/exports/evaluations/${RUN_ID}"
VIDEO_DIR="${RUN_ROOT}/video"
FRAME_DIR="${RUN_ROOT}/frames"

mkdir -p "${VIDEO_DIR}" "${FRAME_DIR}"

# The released copy in checkpoints/final may not have config.yaml next to it,
# while eval_agent_trl.py expects the training config beside the checkpoint.
# Build a non-destructive per-run context in that case.
if [[ ! -f "$(dirname "${CHECKPOINT}")/config.yaml" && \
      ! -f "$(dirname "$(dirname "${CHECKPOINT}")")/config.yaml" ]]; then
  TRAINING_CONFIG="${PROJECT_ROOT}/exports/metrics/training_config.yaml"
  if [[ ! -f "${TRAINING_CONFIG}" ]]; then
    echo "Missing training config: ${TRAINING_CONFIG}" >&2
    exit 1
  fi
  CHECKPOINT_CONTEXT="${RUN_ROOT}/checkpoint_context"
  mkdir -p "${CHECKPOINT_CONTEXT}"
  ln -sf "${CHECKPOINT}" "${CHECKPOINT_CONTEXT}/$(basename "${CHECKPOINT}")"
  cp "${TRAINING_CONFIG}" "${CHECKPOINT_CONTEXT}/config.yaml"
  CHECKPOINT="${CHECKPOINT_CONTEXT}/$(basename "${CHECKPOINT}")"
fi

CHECKPOINT_CONFIG="$(dirname "${CHECKPOINT}")/config.yaml"
if [[ "${FULL_MOTION}" == "true" ]]; then
  # Keep the motion-library timeout so the rollout ends at the final reference
  # frame, but do not stop early when tracking thresholds are exceeded.  This
  # produces a diagnostic full-motion video; it does not count as a successful
  # rollout after the first would-be termination frame.
  FULL_MOTION_CONTEXT="${RUN_ROOT}/full_motion_checkpoint_context"
  mkdir -p "${FULL_MOTION_CONTEXT}"
  ln -sf "${CHECKPOINT}" "${FULL_MOTION_CONTEXT}/$(basename "${CHECKPOINT}")"
  "${PYTHON}" - "${CHECKPOINT_CONFIG}" "${FULL_MOTION_CONTEXT}/config.yaml" <<'PY'
import sys
import yaml

source, destination = sys.argv[1:]
with open(source, "r", encoding="utf-8") as stream:
    config = yaml.safe_load(stream)

terminations = config["manager_env"]["terminations"]
config["manager_env"]["terminations"] = {
    key: value
    for key, value in terminations.items()
    if key in {"_target_", "time_out"}
}

with open(destination, "w", encoding="utf-8") as stream:
    yaml.safe_dump(config, stream, sort_keys=False)
PY
  CHECKPOINT="${FULL_MOTION_CONTEXT}/$(basename "${CHECKPOINT}")"
fi

cd "${SONIC_ROOT}"

export ACCEPT_EULA=Y
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

exec "${PYTHON}" gear_sonic/eval_agent_trl.py \
  +checkpoint="${CHECKPOINT}" \
  +headless=True \
  ++eval_callbacks=im_eval \
  ++run_eval_loop=False \
  ++num_envs=1 \
  ++manager_env.config.render_results=True \
  ++manager_env.config.render_frame_skip=1 \
  ++manager_env.config.save_rendering_dir="${VIDEO_DIR}" \
  '~manager_env/recorders=empty' \
  +manager_env/recorders=render \
  ++manager_env.recorders._target_=sonic_debug.frame_recorder.DebugRecordersCfg \
  ++manager_env.recorders.frame_diagnostics._target_=sonic_debug.frame_recorder.FrameDiagnosticsRecorderCfg \
  ++manager_env.recorders.frame_diagnostics.save_path="${FRAME_DIR}" \
  ++manager_env.recorders.frame_diagnostics.max_envs=1 \
  ++manager_env.recorders.frame_diagnostics.flush_interval=10 \
  ++manager_env.commands.motion.motion_lib_cfg.motion_file="${MOTION_FILE}" \
  ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy \
  2>&1 | tee "${RUN_ROOT}/eval.log"
