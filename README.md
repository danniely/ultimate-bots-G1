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

### Nebius GPU VM

On a Nebius Ubuntu VM created from an NVIDIA GPU image, clone this repository
to `/srv/sonic/ultimate-bots-G1`, then run:

```bash
bash /srv/sonic/ultimate-bots-G1/scripts/setup_nebius.sh
```

The Nebius installer keeps the repository, NVIDIA checkout, and Python
environment together on the VM boot disk under `/srv/sonic`. Stopping the VM
stops compute charges while the disk remains billable and persistent.

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

## s_batido v2 curriculum

The original 2,000-iteration result is frozen under `checkpoints/v1/`. Version
2 starts from those policy and critic weights with a fresh optimizer and lower
learning rate; it does not restart from the released SONIC checkpoint.

The v2 reward plan is recorded in `experiments/v2/reward_plan.yaml`. Stage 1
temporarily removes endpoint terminations and startup physics randomization so
the policy can experience the takeoff and airborne highlight. Stage 2 restores
the normal termination and randomization rules for robustness.

```bash
bash /workspace/ultimate-bots-G1/scripts/start_sonic_v2_stage1.sh

CHECKPOINT=/path/to/stage1/model_step_001000.pt \
bash /workspace/ultimate-bots-G1/scripts/start_sonic_v2_stage2.sh
```

## v3 landing recovery

v3 starts from the selected v2 Stage 1 highlight checkpoint. It keeps the
original 81-frame move and appends a 100-frame recovery target: one second to
return to a stable upright stance and one second to hold it. Recovery-specific
rewards cover two-foot contact, upright pelvis, low base velocity, and keeping
the pelvis projection centered over the feet.

On Nebius, after converting the generated CSV bundle to
`data/motion_lib/s_batido_v3_recovery.pkl`, run a smoke test first:

```bash
NUM_ENVS=32 ITERATIONS=2 SAVE_INTERVAL=1 \
EXPERIMENT_NAME=s_batido_v3_smoke \
OUTPUT_DIR=/srv/sonic/ultimate-bots-G1/exports/v3/smoke \
bash /srv/sonic/ultimate-bots-G1/scripts/start_sonic_v3.sh
```

The full run defaults to 512 environments and 750 iterations with a lower
learning rate than v2 to reduce catastrophic forgetting of the airborne
highlight.
