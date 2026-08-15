#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${RUN_DIR:-/srv/sonic/GR00T-WholeBodyControl/logs_rl/TRL_G1_Track/s_batido_v6_buffered-20260815_090551}"
PROJECT_ROOT="${PROJECT_ROOT:-/srv/sonic/ultimate-bots-G1}"
PYTHON="${PYTHON:-/srv/sonic/env_isaaclab/bin/python}"
DEST="${DEST:-${PROJECT_ROOT}/checkpoints/v6/intermediate}"
TRAIN_SESSION="${TRAIN_SESSION:-sonic_v6_train}"

mkdir -p "${DEST}"
last_preserved=""
while tmux has-session -t "${TRAIN_SESSION}" 2>/dev/null || [[ -f "${RUN_DIR}/last.pt" ]]; do
  if [[ -f "${RUN_DIR}/last.pt" ]]; then
    step="$(${PYTHON} - "${RUN_DIR}/last.pt" <<'PY' 2>/dev/null
import sys
import torch

checkpoint = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
print(int(checkpoint["state"].global_step))
PY
)"
    if [[ -n "${step}" && "${step}" != "${last_preserved}" ]]; then
      destination="${DEST}/s_batido_v6_buffered_step_$(printf '%06d' "${step}").pt"
      if [[ ! -f "${destination}" ]]; then
        cp "${RUN_DIR}/last.pt" "${destination}.tmp"
        mv "${destination}.tmp" "${destination}"
      fi
      cp "${RUN_DIR}/config.yaml" "${DEST}/config.yaml"
      (cd "${DEST}" && sha256sum s_batido_v6_buffered_step_*.pt > SHA256SUMS)
      echo "preserved step=${step} path=${destination}" | tee -a "${DEST}/watch.log"
      last_preserved="${step}"
    fi
  fi
  if ! tmux has-session -t "${TRAIN_SESSION}" 2>/dev/null; then
    break
  fi
  sleep 30
done
