#!/usr/bin/env bash
set -euo pipefail

# Export the fine-tuned SONIC checkpoint to ONNX using NVIDIA's official
# export path (gear_sonic/eval_agent_trl.py +export_onnx_only=true).
#
# This step needs Isaac Lab and therefore must run on a machine where Isaac
# Lab is already installed (it is NOT part of the MuJoCo/Sim2Sim validation
# environment set up by setup_mujoco.sh). No policy weights are modified;
# this only traces the frozen actor network to ONNX.
#
# Usage (run from the Isaac Lab machine, inside its Isaac Lab python env):
#   PYTHON=/path/to/isaaclab/python.sh ./scripts/export_onnx.sh
#
# Override any of CHECKPOINT / SONIC_ROOT / PROJECT_ROOT / PYTHON as needed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
SONIC_ROOT="${SONIC_ROOT:-${HOME}/GR00T-WholeBodyControl}"
PYTHON="${PYTHON:-python}"

CHECKPOINT="${CHECKPOINT:-${PROJECT_ROOT}/checkpoints/v3/s_batido_v3_recovery_step_000600.pt}"
MOTION_SOURCE_DIR="${MOTION_SOURCE_DIR:-${PROJECT_ROOT}/data/source/sonic/s_batido_v3_recovery_sonic}"
MOTION_PKL="${MOTION_PKL:-${PROJECT_ROOT}/data/motion_lib/s_batido_v3_recovery.pkl}"
DEPLOYMENT_DIR="${DEPLOYMENT_DIR:-${PROJECT_ROOT}/deployment}"

if [[ ! -d "${SONIC_ROOT}" ]]; then
  echo "SONIC_ROOT not found: ${SONIC_ROOT}" >&2
  echo "Clone https://github.com/NVlabs/GR00T-WholeBodyControl.git there," >&2
  echo "or set SONIC_ROOT to your existing Isaac Lab / GR00T-WholeBodyControl checkout." >&2
  exit 1
fi

if [[ ! -f "${CHECKPOINT}" ]]; then
  echo "Checkpoint not found: ${CHECKPOINT}" >&2
  echo "Run 'git lfs pull' in ${PROJECT_ROOT} to materialize the real weights" >&2
  echo "(a small pointer file means LFS content was not fetched)." >&2
  exit 1
fi
CHECKPOINT_BYTES="$(wc -c < "${CHECKPOINT}" | tr -d ' ')"
if [[ "${CHECKPOINT_BYTES}" -lt 1000000 ]]; then
  echo "Checkpoint looks like a Git LFS pointer, not real weights (${CHECKPOINT_BYTES} bytes)." >&2
  echo "Run 'git lfs pull' in ${PROJECT_ROOT} first." >&2
  exit 1
fi

if [[ ! -f "${MOTION_PKL}" ]]; then
  echo "[INFO] ${MOTION_PKL} not found - converting from committed CSV bundle ..."
  mkdir -p "$(dirname "${MOTION_PKL}")"
  "${PYTHON}" "${SONIC_ROOT}/gear_sonic/data_process/convert_soma_csv_to_motion_lib.py" \
    --input "${MOTION_SOURCE_DIR}" \
    --output "${MOTION_PKL}" \
    --fps 50
else
  echo "[OK] Found existing motion_lib pkl at ${MOTION_PKL}"
fi

cd "${SONIC_ROOT}"

export ACCEPT_EULA=Y
export OMNI_KIT_ACCEPT_EULA=YES
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

"${PYTHON}" gear_sonic/eval_agent_trl.py \
  +checkpoint="${CHECKPOINT}" \
  +headless=true \
  +num_envs=1 \
  +export_onnx_only=true \
  ++manager_env.commands.motion.motion_lib_cfg.motion_file="${MOTION_PKL}" \
  ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy

EXPORTED_DIR="$(dirname "${CHECKPOINT}")/exported"
MODEL_CONFIG="$(dirname "${CHECKPOINT}")/model_config.yaml"

mkdir -p "${DEPLOYMENT_DIR}"
cp -v "${EXPORTED_DIR}"/*.onnx "${DEPLOYMENT_DIR}/"
[[ -f "${MODEL_CONFIG}" ]] && cp -v "${MODEL_CONFIG}" "${DEPLOYMENT_DIR}/"

# gear_sonic_deploy/deploy.sh reads reference motion from a directory of the
# same CSV files we already build from (body_pos.csv, joint_pos.csv, ...), so
# the committed source bundle can be used directly as --motion-data.
MOTION_DEPLOY_DIR="${DEPLOYMENT_DIR}/motion/s_batido_v3_recovery"
mkdir -p "$(dirname "${MOTION_DEPLOY_DIR}")"
cp -rv "${MOTION_SOURCE_DIR}" "${MOTION_DEPLOY_DIR}"

# Seed an observation_config.yaml starting point. This fine-tune continues
# from the original released SONIC checkpoint's weights without changing the
# observation space, so policy/release/observation_config.yaml (436-dim) is
# the closest official match -- but this MUST be checked against
# deployment/model_config.yaml's obs_dims/obs_names before trusting results.
# See docs/mujoco_validation.md "Observation config caveat".
RELEASE_OBS_CONFIG="${SONIC_ROOT}/gear_sonic_deploy/policy/release/observation_config.yaml"
if [[ -f "${RELEASE_OBS_CONFIG}" ]]; then
  cp -v "${RELEASE_OBS_CONFIG}" "${DEPLOYMENT_DIR}/observation_config.yaml"
fi

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  Export complete. Deployment artifacts staged at:"
echo "    ${DEPLOYMENT_DIR}"
echo ""
echo "  Before running scripts/run_mujoco_eval.sh:"
echo "    1. Compare deployment/model_config.yaml's obs dims/names against"
echo "       deployment/observation_config.yaml (see docs/mujoco_validation.md)."
echo "    2. Commit these artifacts (they are meaningful outputs, not just"
echo "       cache) so they survive and stay versioned on the 'mujoco' branch:"
echo "         git add deployment/"
echo "         git commit -m 'Add exported v3 recovery policy ONNX'"
echo "══════════════════════════════════════════════════════════════"
