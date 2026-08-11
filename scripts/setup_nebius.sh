#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a Nebius Ubuntu GPU VM for SONIC/Isaac Lab. The VM user created in
# the Nebius console is expected to have passwordless sudo via cloud-init.
NEBIUS_WORKSPACE="${NEBIUS_WORKSPACE:-/srv/sonic}"
PROJECT_ROOT="${PROJECT_ROOT:-${NEBIUS_WORKSPACE}/ultimate-bots-G1}"
SONIC_ROOT="${SONIC_ROOT:-${NEBIUS_WORKSPACE}/GR00T-WholeBodyControl}"
VENV_PATH="${VENV_PATH:-${NEBIUS_WORKSPACE}/env_isaaclab}"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This installer must run on the Nebius Linux VM." >&2
  exit 1
fi

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=()
else
  SUDO=(sudo)
fi

"${SUDO[@]}" apt-get update -qq
"${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  build-essential ca-certificates cmake curl ffmpeg git git-lfs jq rsync tmux \
  libgl1 libglib2.0-0 libx11-6 libxext6 libxrender1 libsm6 libxrandr2 \
  libxinerama1 libxcursor1 libxt6 libglu1-mesa libvulkan1 vulkan-tools \
  libegl-dev libglvnd0 libglx0

"${SUDO[@]}" install -d -o "$(id -u)" -g "$(id -g)" "${NEBIUS_WORKSPACE}"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "NVIDIA driver is missing. Create the VM from a Nebius NVIDIA GPU image." >&2
  exit 1
fi
nvidia-smi

# Nebius CUDA images may contain only the compute portion of the NVIDIA driver.
# Isaac Sim headless rendering also needs the matching Vulkan/OpenGL ICD. The
# CUDA repository is pinned below normal priority, so request exact versions.
if ! vulkaninfo --summary 2>/dev/null | grep -q 'deviceName.*NVIDIA'; then
  NVIDIA_COMPUTE_PACKAGE="$(dpkg-query -W -f='${binary:Package}\n' 'libnvidia-compute-*' 2>/dev/null | head -n 1)"
  NVIDIA_BRANCH="${NVIDIA_COMPUTE_PACKAGE##*-}"
  NVIDIA_BRANCH="${NVIDIA_BRANCH%%:*}"
  NVIDIA_DRIVER_VERSION="$(dpkg-query -W -f='${Version}' "${NVIDIA_COMPUTE_PACKAGE}")"
  latest_version() {
    apt-cache madison "$1" | awk 'NR == 1 { print $3 }'
  }
  "${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    "libnvidia-egl-gbm1=$(latest_version libnvidia-egl-gbm1)" \
    "libnvidia-egl-wayland1=$(latest_version libnvidia-egl-wayland1)" \
    "libnvidia-egl-xcb1=$(latest_version libnvidia-egl-xcb1)" \
    "libnvidia-egl-xlib1=$(latest_version libnvidia-egl-xlib1)" \
    "libnvidia-gl-${NVIDIA_BRANCH}=${NVIDIA_DRIVER_VERSION}"
fi

vulkaninfo --summary 2>/dev/null | grep -A8 -E 'GPU[0-9]+:' | head -n 20

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | \
    "${SUDO[@]}" env UV_INSTALL_DIR=/usr/local/bin sh
fi

if [[ ! -d "${SONIC_ROOT}/.git" ]]; then
  git clone https://github.com/NVlabs/GR00T-WholeBodyControl.git "${SONIC_ROOT}"
fi

if [[ ! -d "${PROJECT_ROOT}/.git" ]]; then
  echo "Clone danniely/ultimate-bots-G1 into ${PROJECT_ROOT} before running this script." >&2
  exit 1
fi

git -C "${PROJECT_ROOT}" lfs install
git -C "${PROJECT_ROOT}" lfs pull

uv python install 3.11
if [[ ! -x "${VENV_PATH}/bin/python" ]]; then
  uv venv --python 3.11 "${VENV_PATH}"
fi

uv pip install --python "${VENV_PATH}/bin/python" setuptools==80.9.0 wheel
uv pip install --python "${VENV_PATH}/bin/python" flatdict==4.0.1 --no-build-isolation

export ACCEPT_EULA=Y
export OMNI_KIT_ACCEPT_EULA=YES

uv pip install --python "${VENV_PATH}/bin/python" \
  "isaaclab[isaacsim,all]==2.3.0" \
  --extra-index-url https://pypi.nvidia.com

uv pip install --python "${VENV_PATH}/bin/python" \
  torch==2.7.0 torchvision==0.22.0 \
  --index-url https://download.pytorch.org/whl/cu128

uv pip install --python "${VENV_PATH}/bin/python" \
  -e "${SONIC_ROOT}/gear_sonic[training]" \
  "huggingface_hub[cli]" ipykernel open3d vector-quantize-pytorch

"${VENV_PATH}/bin/python" -m ipykernel install --user \
  --name sonic-nebius-python311 --display-name "SONIC Nebius (Python 3.11)"

"${VENV_PATH}/bin/python" -c \
  "import torch; import isaaclab; print('torch', torch.__version__, 'cuda', torch.cuda.is_available()); print('isaaclab import OK')"

echo "Nebius SONIC environment is ready at ${VENV_PATH}."
