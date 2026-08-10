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
└── ultimate-bots-G1/        # this repository
/opt/
└── env_isaaclab/            # regenerable Python 3.11 environment
```

## Setup

```bash
bash /workspace/ultimate-bots-G1/scripts/setup_runpod.sh
```

Large final artifacts are tracked with Git LFS. Intermediate checkpoints stay
on the RunPod volume and are not committed.

The Python environment lives on the faster container disk because Isaac Sim
contains many small files. Re-run the setup script after recreating a Pod.

## Frame-level evaluation diagnostics

Use `scripts/run_sonic_eval_debug.sh` for evaluation runs that need debugging.
It saves the rendered video and synchronized 50 Hz telemetry under one run ID
in `exports/evaluations/<RUN_ID>/`.

The canonical `frames/*.npz` contains actual/reference joint positions and
velocities, errors, controller targets, actions, applied/computed torques,
tracked-body and pelvis state, contact forces, and every termination flag. A
flattened `frames/*.csv` is written simultaneously for quick inspection.
`frames/metadata.json` records joint/body ordering and units.

```bash
RUN_ID=after_reward_v2 \
CHECKPOINT=/workspace/ultimate-bots-G1/checkpoints/final/s_batido_sonic_step_002000.pt \
bash /workspace/ultimate-bots-G1/scripts/run_sonic_eval_debug.sh
```
