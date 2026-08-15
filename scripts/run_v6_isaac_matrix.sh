#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/srv/sonic/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/sonic/ultimate-bots-G1}"
PYTHON="${PYTHON:-/srv/sonic/env_isaaclab/bin/python}"
CHECKPOINT="${CHECKPOINT:?Set CHECKPOINT to a V6 checkpoint with config.yaml beside it}"
MOTION_FILE="${MOTION_FILE:-${PROJECT_ROOT}/data/motion_lib/s_batido_v6_buffered.pkl}"
SEEDS="${SEEDS:-0 1 2 3 4}"
PROFILES="${PROFILES:-hardware_nominal hardware_moderate hardware_official hardware_recovery_push}"
RUN_ROOT="${RUN_ROOT:-${PROJECT_ROOT}/exports/v6/isaac_matrix}"
CONTEXT_ROOT="${RUN_ROOT}/contexts"

mkdir -p "${RUN_ROOT}"
"${PYTHON}" "${PROJECT_ROOT}/scripts/prepare_v6_eval_context.py" \
  --checkpoint "${CHECKPOINT}" --output-root "${CONTEXT_ROOT}"

cd "${SONIC_ROOT}"
export ACCEPT_EULA=Y
export OMNI_KIT_ACCEPT_EULA=YES
export PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

for profile in ${PROFILES}; do
  mkdir -p "${RUN_ROOT}/${profile}"
  for seed in ${SEEDS}; do
    log="${RUN_ROOT}/${profile}/seed_${seed}.log"
    echo "profile=${profile} seed=${seed}" | tee "${log}"
    "${PYTHON}" gear_sonic/eval_agent_trl.py \
      +checkpoint="${CONTEXT_ROOT}/${profile}/$(basename "${CHECKPOINT}")" \
      +headless=True ++seed="${seed}" ++eval_callbacks=im_eval \
      ++run_eval_loop=False ++num_envs=1 \
      ++manager_env.config.render_results=False \
      ++manager_env.commands.motion.motion_lib_cfg.motion_file="${MOTION_FILE}" \
      ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy \
      2>&1 | tee -a "${log}"
  done
done

"${PYTHON}" "${PROJECT_ROOT}/scripts/summarize_v3_strict_matrix.py" --run-root "${RUN_ROOT}"
