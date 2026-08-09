#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/workspace/ultimate-bots-G1"
SONIC_ROOT="/workspace/GR00T-WholeBodyControl"
VENV_PATH="/workspace/env_isaaclab"

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  build-essential cmake git-lfs libgl1 libglib2.0-0 libx11-6 libxext6 \
  libxrender1 libsm6 libxrandr2 libxinerama1 libxcursor1

python -m pip install --upgrade uv
uv python install 3.11

if [[ ! -x "${VENV_PATH}/bin/python" ]]; then
  uv venv --python 3.11 "${VENV_PATH}"
fi

uv pip install --python "${VENV_PATH}/bin/python" \
  "isaaclab[isaacsim,all]==2.3.0" \
  --extra-index-url https://pypi.nvidia.com

uv pip install --python "${VENV_PATH}/bin/python" \
  torch==2.7.0 torchvision==0.22.0 \
  --index-url https://download.pytorch.org/whl/cu128

uv pip install --python "${VENV_PATH}/bin/python" \
  -e "${SONIC_ROOT}/gear_sonic[training]" \
  "huggingface_hub[cli]"

git -C "${PROJECT_ROOT}" lfs install

"${VENV_PATH}/bin/python" -c \
  "import torch; import isaaclab; print('torch', torch.__version__, 'cuda', torch.cuda.is_available()); print('isaaclab import OK')"

