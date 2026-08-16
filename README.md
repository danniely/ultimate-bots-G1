# Unitree G1 Capoeira Kick — SONIC Capoeira V8

This repository contains the reproducible experiment files for fine-tuning
NVIDIA SONIC to perform a short, high-impact capoeira kick on Unitree G1.

The NVIDIA source checkout is kept separately at
`/workspace/GR00T-WholeBodyControl`. This repository stores only our motion
data, configuration, scripts, metrics, selected checkpoints, ONNX exports, and
before/after videos.

## Project overview

I taught Unitree G1 a capoeira kick using a real human motion reference. I
initially explored AI-generated video, but it often ignored physical constraints
and did not provide the motion quality needed for training.

Having separate training and validation environments made cross-validation
especially challenging. The policy was trained in NVIDIA Isaac Sim, while
differences in physics, contacts, friction, and actuator response made the same
motion less reliable in MuJoCo. I improved the result by dividing the motion
into launch, kick, landing, and recovery phases and applying phase-specific
rewards and penalties. Repeated training and Isaac Sim–MuJoCo validation
gradually produced a more accurate and stable motion.

### Submission links

- **Before and after simulation:** [G1 Robot.mp4](videos/G1%20Robot.mp4)
- **ONNX policy:** [SONIC Capoeira V8 on Hugging Face](https://huggingface.co/hyunho7979/sonic-capoeira-v8)
- **Motion dataset:** [SONIC Capoeira V8 dataset on Hugging Face](https://huggingface.co/datasets/hyunho7979/sonic-capoeira-v8)
- **Code and training configuration:** this repository

### Validation snapshot

- Isaac Sim evaluation: **112/112 completed rollouts** across the recorded V8
  screening matrix.
- ONNX parity: encoder max absolute difference `0`; decoder max absolute
  difference `1.67e-6`.
- MuJoCo cross-validation: **10/10 full-motion rollouts**, with **3/10** meeting
  the stricter final-stabilization gate.

> **Safety note:** This is a simulation research result. The policy has not
> been approved for deployment on a physical robot.

## Version-by-version improvements

Each version responds to a failure observed in the previous one; the numbers do
not simply represent longer training. Reward structure, termination rules,
motion timing, deployment handoff, and validation gates all changed over time.

| Version | Primary improvement | Outcome / next limitation |
|---|---|---|
| V0 | Recorded the untouched NVIDIA SONIC release as the baseline. | Lost the reference before the kick and reached the floor within the first half-second. |
| V1 | Fine-tuned all 81 reference frames with the standard full-body tracking objective. | Learned the broad motion, but the airborne kick and landing were weak. |
| V2 | Split the move into support, launch, airborne highlight, and landing phases with phase-specific rewards. | Stage 1 produced the clearest kick; restoring strict gates in Stage 2 caused early termination. |
| V3 | Added a 100-frame landing-recovery tail, two-foot support, upright, low-velocity, and support-center rewards. | Completed 181/181 frames in Isaac Sim, but hardware-oriented validation was still missing. |
| V4 | Added strict physical failure conditions, domain randomization, recovery pushes, contact-overload penalties, and actuator-risk metrics. | Improved Isaac robustness; MuJoCo exposed inconsistent recovery and repeated 139 Nm saturation. |
| V5 | Added a settled-start gate, knee torque reserve, joint-speed limits, action smoothing, and stronger launch/recovery stability rewards. | Reduced Isaac contact and acceleration peaks, but the official MuJoCo controller could not establish a repeatable safe start. |
| V6 | Added an explicit standing buffer, smooth policy handoff, eased launch, landing coast, and final standing hold. | Completed all Isaac profiles; the ten-run MuJoCo confirmation exposed startup and final-recovery transfer failures. |
| V7 | Corrected the startup diagnostic order and locally retimed only the sharp reference discontinuities. | Reached 10/10 MuJoCo starts and 10/10 full motions, but only 2/10 strict final stabilizations. |
| V8 | Slowed touchdown by 3× and recovery by 2×; optimized capture point, landing load, recovery joint speed, knee reserve, and actuator randomization. | Completed 112/112 Isaac evaluations and 10/10 MuJoCo motions; the selected checkpoint passed strict final stabilization in 3/10 runs. |

The detailed engineering journal, including the reason for each revision,
training changes, measured results, and lessons learned, is available in
[docs/VERSION_HISTORY.md](docs/VERSION_HISTORY.md).

> A fresh optimizer means that policy and critic weights were restored from the
> previous checkpoint while optimizer momentum and learning-rate state were
> restarted. It does not mean training began from random weights.

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
