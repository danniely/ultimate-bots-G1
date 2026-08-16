#!/usr/bin/env bash
set -euo pipefail

SONIC_ROOT="${SONIC_ROOT:-/srv/sonic/GR00T-WholeBodyControl}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/sonic/ultimate-bots-G1}"
PYTHON="${PYTHON:-/srv/sonic/env_isaaclab/bin/python}"
CHECKPOINT_DIR="${CHECKPOINT_DIR:-${PROJECT_ROOT}/exports/v8/train/checkpoints}"
MOTION_FILE="${MOTION_FILE:-${PROJECT_ROOT}/data/motion_lib/s_batido_v8_landing.pkl}"
SEEDS="${SEEDS:-0 1 2 3 4}"
PROFILES="${PROFILES:-hardware_nominal hardware_moderate hardware_official hardware_recovery_push}"
RUN_ROOT="${RUN_ROOT:-${PROJECT_ROOT}/exports/v8/isaac_screen}"
MAX_JOBS="${MAX_JOBS:-4}"
STEPS="${STEPS:-025 050 075 100 125 150 175 200 225 250 275 300}"

mkdir -p "${RUN_ROOT}"
cd "${SONIC_ROOT}"
export ACCEPT_EULA=Y OMNI_KIT_ACCEPT_EULA=YES PYTHONUNBUFFERED=1
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

run_one() {
  local checkpoint="$1" step="$2" profile="$3" seed="$4" context_root="$5"
  local out="${RUN_ROOT}/step_${step}/${profile}"
  local log="${out}/seed_${seed}.log"
  mkdir -p "${out}"
  if grep -q "Success Rate:" "${log}" 2>/dev/null; then
    echo "skip step=${step} profile=${profile} seed=${seed}" >>"${RUN_ROOT}/progress.log"
    return 0
  fi
  echo "start step=${step} profile=${profile} seed=${seed}" >>"${RUN_ROOT}/progress.log"
  if "${PYTHON}" gear_sonic/eval_agent_trl.py \
    +checkpoint="${context_root}/${profile}/$(basename "${checkpoint}")" \
    +headless=True ++seed="${seed}" ++eval_callbacks=im_eval \
    ++run_eval_loop=False ++num_envs=1 \
    ++experiment_name="v8_eval_${step}_${profile}_${seed}" \
    ++manager_env.config.render_results=False \
    ++manager_env.commands.motion.motion_lib_cfg.motion_file="${MOTION_FILE}" \
    ++manager_env.commands.motion.motion_lib_cfg.smpl_motion_file=dummy \
    >"${log}" 2>&1; then
    echo "done step=${step} profile=${profile} seed=${seed}" >>"${RUN_ROOT}/progress.log"
  else
    local rc=$?
    echo "failed step=${step} profile=${profile} seed=${seed} rc=${rc}" >>"${RUN_ROOT}/progress.log"
  fi
}

for step in ${STEPS}; do
  checkpoint="${CHECKPOINT_DIR}/model_step_000${step}.pt"
  [[ -f "${checkpoint}" ]] || { echo "missing ${checkpoint}" >&2; exit 2; }
  checkpoint_root="${RUN_ROOT}/step_${step}"
  context_root="${checkpoint_root}/contexts"
  "${PYTHON}" "${PROJECT_ROOT}/scripts/prepare_v8_eval_context.py" \
    --checkpoint "${checkpoint}" --output-root "${context_root}"
  for profile in ${PROFILES}; do
    for seed in ${SEEDS}; do
      run_one "${checkpoint}" "${step}" "${profile}" "${seed}" "${context_root}" &
      while (( $(jobs -pr | wc -l) >= MAX_JOBS )); do wait -n; done
    done
  done
done
wait

for step in ${STEPS}; do
  "${PYTHON}" "${PROJECT_ROOT}/scripts/summarize_v3_strict_matrix.py" \
    --run-root "${RUN_ROOT}/step_${step}"
done
echo "ISAAC_SCREEN_EXIT=0" | tee "${RUN_ROOT}/driver.log"
