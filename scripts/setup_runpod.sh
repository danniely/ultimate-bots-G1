#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/workspace/ultimate-bots-G1"
SONIC_ROOT="/workspace/GR00T-WholeBodyControl"
VENV_PATH="/workspace/env_isaaclab"

apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  build-essential ca-certificates cmake curl git-lfs libgl1 libglib2.0-0 libx11-6 libxext6 \
  libxrender1 libsm6 libxrandr2 libxinerama1 libxcursor1

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
fi
uv python install 3.11

if [[ ! -x "${VENV_PATH}/bin/python" ]]; then
  uv venv --python 3.11 "${VENV_PATH}"
fi

uv pip install --python "${VENV_PATH}/bin/python" setuptools==80.9.0 wheel
uv pip install --python "${VENV_PATH}/bin/python" \
  flatdict==4.0.1 --no-build-isolation

uv pip install --python "${VENV_PATH}/bin/python" \
  "isaaclab[isaacsim,all]==2.3.0" \
  --extra-index-url https://pypi.nvidia.com

uv pip install --python "${VENV_PATH}/bin/python" \
  torch==2.7.0 torchvision==0.22.0 \
  --index-url https://download.pytorch.org/whl/cu128

uv pip install --python "${VENV_PATH}/bin/python" \
  -e "${SONIC_ROOT}/gear_sonic[training]" \
  "huggingface_hub[cli]" ipykernel

"${VENV_PATH}/bin/python" -m ipykernel install --user \
  --name sonic-python311 --display-name "SONIC (Python 3.11)"

git -C "${PROJECT_ROOT}" lfs install

"${VENV_PATH}/bin/python" -c \
  "import torch; import isaaclab; print('torch', torch.__version__, 'cuda', torch.cuda.is_available()); print('isaaclab import OK')"
