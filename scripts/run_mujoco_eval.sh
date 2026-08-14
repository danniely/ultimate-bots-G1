#!/usr/bin/env bash
set -euo pipefail

# Print the two commands needed to run a MuJoCo Sim2Sim validation trial:
# the MuJoCo simulator (Terminal A) and the SONIC deployment controller
# (Terminal B). These are two long-lived processes that must stay running
# and talking to each other over loopback ZMQ/DDS, so this script does not
# background-manage them -- it tells you exactly what to run and where, per
# NVIDIA's own gear_sonic_deploy workflow (see docs/mujoco_validation.md).
#
# The controller (deploy.sh) links against TensorRT and requires an NVIDIA
# GPU. It cannot run on a machine without one.
#
# Usage:
#   ./scripts/run_mujoco_eval.sh --stock                         # Milestone 2 baseline
#   ./scripts/run_mujoco_eval.sh --policy deployment/model_step_000600 \
#       --motion deployment/motion/s_batido_v3_recovery           # Milestone 4/5

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
SONIC_ROOT="${SONIC_ROOT:-${HOME}/GR00T-WholeBodyControl}"
DEPLOY_DIR="${SONIC_ROOT}/gear_sonic_deploy"

STOCK=false
POLICY=""
MOTION=""
OBS_CONFIG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stock)
      STOCK=true
      shift
      ;;
    --policy)
      POLICY="$2"
      shift 2
      ;;
    --motion)
      MOTION="$2"
      shift 2
      ;;
    --obs-config)
      OBS_CONFIG="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "${STOCK}" == false && -z "${POLICY}" ]]; then
  echo "Pass --stock for the known-good NVIDIA baseline, or --policy <path> for the fine-tuned policy." >&2
  echo "See: ./scripts/run_mujoco_eval.sh --stock" >&2
  echo "     ./scripts/run_mujoco_eval.sh --policy deployment/model_step_000600 --motion deployment/motion/s_batido_v3_recovery" >&2
  exit 1
fi

if [[ ! -d "${DEPLOY_DIR}" ]]; then
  echo "gear_sonic_deploy not found at ${DEPLOY_DIR}. Run ./scripts/setup_mujoco.sh first." >&2
  exit 1
fi

DEPLOY_ARGS=()
if [[ "${STOCK}" == false ]]; then
  POLICY_ABS="${PROJECT_ROOT}/${POLICY#"${PROJECT_ROOT}"/}"
  DEPLOY_ARGS+=(--cp "${POLICY_ABS}")
  if [[ -n "${MOTION}" ]]; then
    MOTION_ABS="${PROJECT_ROOT}/${MOTION#"${PROJECT_ROOT}"/}"
    DEPLOY_ARGS+=(--motion-data "${MOTION_ABS}")
  fi
  if [[ -n "${OBS_CONFIG}" ]]; then
    OBS_CONFIG_ABS="${PROJECT_ROOT}/${OBS_CONFIG#"${PROJECT_ROOT}"/}"
  else
    OBS_CONFIG_ABS="${PROJECT_ROOT}/deployment/observation_config.yaml"
  fi
  DEPLOY_ARGS+=(--obs-config "${OBS_CONFIG_ABS}")
fi
DEPLOY_ARGS+=(sim)

echo "══════════════════════════════════════════════════════════════"
echo "  Run these in two separate terminals."
echo "══════════════════════════════════════════════════════════════"
echo ""
echo "  Terminal A - MuJoCo simulator:"
echo ""
echo "    cd ${SONIC_ROOT}"
echo "    source .venv_sim/bin/activate"
echo "    python gear_sonic/scripts/run_sim_loop.py"
echo ""
echo "  Terminal B - SONIC deployment controller"
if [[ "${STOCK}" == true ]]; then
echo "               (NVIDIA release policy, known-good baseline):"
else
echo "               (fine-tuned v3 recovery policy):"
fi
echo ""
echo "    cd ${DEPLOY_DIR}"
printf "    ./deploy.sh"
for arg in "${DEPLOY_ARGS[@]}"; do printf " %q" "${arg}"; done
printf "\n\n"
echo "  First run of deploy.sh installs 'just'/build deps and compiles"
echo "  g1_deploy_onnx_ref (needs TensorRT_ROOT set - see deploy.sh output)."
echo "  Start Terminal A first, then Terminal B. Ctrl+C both to stop."
echo "══════════════════════════════════════════════════════════════"
