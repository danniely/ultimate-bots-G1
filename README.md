# Ultimate Bots G1 — SuperSONIC fine-tuning

This repository contains the reproducible experiment files for fine-tuning
NVIDIA SONIC on a custom Unitree G1 martial-arts motion.

The NVIDIA source checkout is kept separately at
`/workspace/GR00T-WholeBodyControl`. This repository stores only our motion
data, configuration, scripts, metrics, selected checkpoints, ONNX exports, and
before/after videos.

## RunPod layout

```text
/workspace/
├── GR00T-WholeBodyControl/  # NVIDIA upstream source
├── ultimate-bots-G1/        # this repository
└── env_isaaclab/            # Python 3.11 environment
```

## Setup

```bash
bash /workspace/ultimate-bots-G1/scripts/setup_runpod.sh
```

Large final artifacts are tracked with Git LFS. Intermediate checkpoints stay
on the RunPod volume and are not committed.

