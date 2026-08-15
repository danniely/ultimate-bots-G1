#!/usr/bin/env bash
set -euo pipefail

TRAIN_SESSION="${TRAIN_SESSION:-sonic_v3_robust}"
RUN_DIR="${RUN_DIR:-/srv/sonic/GR00T-WholeBodyControl/logs_rl/TRL_G1_Track/s_batido_v3_robust-20260814_161203}"
TRAIN_LOG="${TRAIN_LOG:-/srv/sonic/ultimate-bots-G1/exports/v3/robust/train/train.log}"
OUTPUT_DIR="${OUTPUT_DIR:-/srv/sonic/ultimate-bots-G1/exports/v3/robust/train/checkpoints}"
SOURCE="${RUN_DIR}/last.pt"
STATE_FILE="${OUTPUT_DIR}/.last_mtime"
PYTHON="${PYTHON:-/srv/sonic/env_isaaclab/bin/python}"
CHECKPOINT_PREFIX="${CHECKPOINT_PREFIX:-s_batido_v3_robust}"

mkdir -p "${OUTPUT_DIR}"
last_mtime="$(cat "${STATE_FILE}" 2>/dev/null || true)"

while tmux has-session -t "${TRAIN_SESSION}" 2>/dev/null || [[ -f "${SOURCE}" ]]; do
  if [[ -f "${SOURCE}" ]]; then
    current_mtime="$(stat -c %Y "${SOURCE}")"
    if [[ "${current_mtime}" != "${last_mtime}" ]]; then
      # The trainer has just atomically refreshed last.pt.  Give buffers a
      # moment to settle, then label the snapshot from the matching log step.
      sleep 2
      iteration="$("${PYTHON}" - "${SOURCE}" <<'PY'
import sys
import torch

checkpoint = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
print(int(checkpoint["state"].global_step))
PY
)"
      if [[ -n "${iteration}" ]]; then
        printf -v label '%06d' "${iteration}"
        target="${OUTPUT_DIR}/${CHECKPOINT_PREFIX}_step_${label}.pt"
        cp --reflink=auto "${SOURCE}" "${target}"
        printf '%s\n' "${current_mtime}" > "${STATE_FILE}"
        last_mtime="${current_mtime}"
        echo "$(date -u +%FT%TZ) saved ${target}"
      fi
    fi
  fi

  tmux has-session -t "${TRAIN_SESSION}" 2>/dev/null || break
  sleep 10
done
