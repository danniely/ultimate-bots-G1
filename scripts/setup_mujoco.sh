#!/usr/bin/env bash
set -euo pipefail

# Bootstrap the lightweight MuJoCo deployment environment used for Sim2Sim
# validation of the fine-tuned SONIC policy. This does NOT require Isaac Lab,
# a GPU, or the training environment set up by setup_runpod.sh/setup_nebius.sh
# -- it only needs gear_sonic_deploy's own .venv_sim, which runs on CPU.
#
# Usage: ./scripts/setup_mujoco.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SONIC_ROOT="${SONIC_ROOT:-${HOME}/GR00T-WholeBodyControl}"

if [[ ! -d "${SONIC_ROOT}/.git" ]]; then
  echo "[INFO] Cloning NVlabs/GR00T-WholeBodyControl into ${SONIC_ROOT} ..."
  git clone https://github.com/NVlabs/GR00T-WholeBodyControl.git "${SONIC_ROOT}"
else
  echo "[OK] Found existing checkout at ${SONIC_ROOT}"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "[INFO] uv not found - installing ..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi
echo "[OK] uv $(uv --version)"

cd "${SONIC_ROOT}"
bash install_scripts/install_mujoco_sim.sh

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  MuJoCo deployment environment ready."
echo ""
echo "  SONIC_ROOT   = ${SONIC_ROOT}"
echo "  PROJECT_ROOT = ${PROJECT_ROOT}"
echo ""
echo "  Next steps (see docs/mujoco_validation.md):"
echo "    1. Get policy.onnx into ${PROJECT_ROOT}/deployment/"
echo "       (exported on the Isaac Lab machine via scripts/export_onnx.sh)"
echo "    2. ./scripts/run_mujoco_eval.sh --policy <POLICY_ONNX> --motion <REFERENCE_MOTION>"
echo "══════════════════════════════════════════════════════════════"
