#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/srv/sonic/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/sonic/ultimate-bots-G1}"
PYTHON="${PYTHON:-/srv/sonic/env_isaaclab/bin/python}"
CHECKPOINT="${CHECKPOINT:-${SONIC_ROOT}/sonic_release/last.pt}"
SOURCE_MOTION="${SOURCE_MOTION:-${PROJECT_ROOT}/data/motion_lib/s_batido_test.pkl}"
FALLBACK_SOURCE_MOTION="${FALLBACK_SOURCE_MOTION:-${PROJECT_ROOT}/data/motion_lib/s_batido_v3_recovery.pkl}"
BUFFERED_MOTION="${BUFFERED_MOTION:-${PROJECT_ROOT}/exports/v0/motion/s_batido_v0_release_buffered.pkl}"
RUN_ROOT="${RUN_ROOT:-${PROJECT_ROOT}/exports/v0/isaac_release_buffered}"
VIDEO_DIR="${RUN_ROOT}/video"
FRAME_DIR="${RUN_ROOT}/frames"
CONTEXT_DIR="${RUN_ROOT}/checkpoint_context"

mkdir -p "${VIDEO_DIR}" "${FRAME_DIR}" "${CONTEXT_DIR}"

SOURCE_FRAME_ARGS=()
if [[ ! -f "${SOURCE_MOTION}" && -f "${FALLBACK_SOURCE_MOTION}" ]]; then
  echo "Original PKL is absent; reconstructing its first 81 frames from V3 recovery data"
  SOURCE_MOTION="${FALLBACK_SOURCE_MOTION}"
  SOURCE_FRAME_ARGS=(--source-frames 81)
fi

"${PYTHON}" "${PROJECT_ROOT}/scripts/build_v0_buffered_motion.py" \
  "${SOURCE_MOTION}" "${BUFFERED_MOTION}" --buffer-seconds 2.0 \
  "${SOURCE_FRAME_ARGS[@]}"

if [[ ! -f "${CHECKPOINT}" ]]; then
  echo "Missing pristine SONIC release checkpoint: ${CHECKPOINT}" >&2
  exit 1
fi
if [[ ! -f "$(dirname "${CHECKPOINT}")/config.yaml" ]]; then
  echo "Missing release config beside checkpoint" >&2
  exit 1
fi

ln -sfn "${CHECKPOINT}" "${CONTEXT_DIR}/last.pt"
"${PYTHON}" - "$(dirname "${CHECKPOINT}")/config.yaml" "${CONTEXT_DIR}/config.yaml" <<'PY'
import sys
import yaml

source, destination = sys.argv[1:]
with open(source, "r", encoding="utf-8") as stream:
    config = yaml.safe_load(stream)

# Preserve the motion timeout, but allow the simulator and camera to continue
# through tracking failure and the appended two-second diagnostic tail.
terminations = config["manager_env"]["terminations"]
config["manager_env"]["terminations"] = {
    key: value for key, value in terminations.items() if key in {"_target_", "time_out"}
}

with open(destination, "w", encoding="utf-8") as stream:
    yaml.safe_dump(config, stream, sort_keys=False)
PY

cd "${SONIC_ROOT}"
export ACCEPT_EULA=Y
export OMNI_KIT_ACCEPT_EULA=YES
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

exec "${PYTHON}" gear_sonic/eval_agent_trl.py \
  +checkpoint="${CONTEXT_DIR}/last.pt" \
  +headless=True \
  ++eval_callbacks=im_eval \
  ++run_eval_loop=False \
  ++num_envs=1 \
  ++manager_env.observations.policy.enable_corruption=False \
  ++manager_env.observations.tokenizer.enable_corruption=False \
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
  ++manager_env.commands.motion.motion_lib_cfg.motion_file="${BUFFERED_MOTION}" \
  ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy \
  2>&1 | tee "${RUN_ROOT}/eval.log"
