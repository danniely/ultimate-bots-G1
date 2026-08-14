# MuJoCo Sim2Sim validation

## Purpose

The fine-tuned SONIC checkpoint (`checkpoints/v3/s_batido_v3_recovery_step_000600.pt`)
already completes the `s_batido` motion in Isaac Lab / PhysX (Success Rate
1.0, Progress Rate 1.0 -- see `exports/v3/final/final_full_eval.log`). This
only proves the policy works under PhysX's dynamics.

MuJoCo implements physics differently (contacts, friction, actuator
response). Running the exact same frozen policy through MuJoCo, unmodified,
is an independent check for overfitting to one simulator's dynamics before
ever touching real hardware.

**This is validation, not training.** No policy weights are exported,
fine-tuned, or otherwise modified as part of this workflow. If MuJoCo fails,
the fix is either an integration bug (wrong observation/joint/action
convention) or, if the integration is verified correct, an Isaac-side
training robustness improvement (domain randomization) followed by a new
Isaac + MuJoCo evaluation round -- never training directly against MuJoCo.

## Architecture

```text
checkpoints/v3/s_batido_v3_recovery_step_000600.pt   (frozen, Isaac-trained)
        |  scripts/export_onnx.sh  (needs Isaac Lab)
        v
deployment/model_step_000600_{encoder,decoder}.onnx
deployment/observation_config.yaml
deployment/motion/s_batido_v3_recovery/
        |  scripts/run_mujoco_eval.sh  (needs an NVIDIA GPU)
        v
gear_sonic_deploy (deploy.sh)  --  official SONIC deployment controller
        |  loopback ZMQ/DDS
        v
gear_sonic MuJoCo simulator (run_sim_loop.py)  --  G1 model, contacts, gravity
```

Both `eval_agent_trl.py`'s ONNX export and `gear_sonic_deploy`'s controller
are NVIDIA's own tooling from `NVlabs/GR00T-WholeBodyControl`. This repo does
not reimplement joint mapping, observation construction, PD control, or
action scaling.

## Hardware requirement: everything here needs an NVIDIA GPU

Unlike what a first read of `gear_sonic_deploy` suggests, **none of this
runs on a Mac or any GPU-less machine**:

- **ONNX export** (`gear_sonic/eval_agent_trl.py`) hard-requires Isaac Lab
  (`import isaaclab` at the top of the file exits immediately if missing).
  Isaac Lab needs an NVIDIA GPU.
- **The MuJoCo deployment controller** (`gear_sonic_deploy/deploy.sh`, which
  builds and runs the C++ binary `g1_deploy_onnx_ref`) links against
  TensorRT (`find_package(TensorRT REQUIRED)` in
  `gear_sonic_deploy/CMakeLists.txt`). TensorRT requires CUDA. This is true
  even in `sim` mode -- `deploy.sh sim` runs the exact same TensorRT-linked
  binary as `deploy.sh real`, just pointed at a loopback interface instead
  of the robot's network.

Only the MuJoCo simulator process itself (`gear_sonic/scripts/run_sim_loop.py`,
installed by `install_scripts/install_mujoco_sim.sh` into `.venv_sim`) is
pure Python/CPU. It still needs to run on the same GPU machine as the
controller, since the two talk to each other over local loopback.

**Everything in this doc is written to run on the Windows PC with the
NVIDIA GPU** (the same machine already running Isaac Sim/Lab). This repo's
scripts are developed and pushed from elsewhere (e.g. this Mac's `mujoco`
branch); nothing in this doc is expected to execute there.

## Setup (on the GPU machine)

```bash
git clone <this repo> -b mujoco
cd ultimate-bots-G1
git lfs install
git lfs pull        # materializes checkpoints/v3/*.pt (~428 MB, is a pointer otherwise)

./scripts/setup_mujoco.sh
# clones NVlabs/GR00T-WholeBodyControl to ~/GR00T-WholeBodyControl (override with SONIC_ROOT)
# and installs gear_sonic_deploy's .venv_sim
```

## Usage

### 1. Export the fine-tuned policy to ONNX (needs Isaac Lab)

```bash
PYTHON=/path/to/isaaclab/python.sh ./scripts/export_onnx.sh
```

Converts the committed motion CSV bundle
(`data/source/sonic/s_batido_v3_recovery_sonic/`) to `motion_lib` pkl format,
then runs `eval_agent_trl.py +export_onnx_only=true` against
`checkpoints/v3/s_batido_v3_recovery_step_000600.pt`. Stages the results
under `deployment/`:

```text
deployment/
├── model_step_000600_encoder.onnx
├── model_step_000600_decoder.onnx     # (+ _g1/_smpl/_teleop variants if universal-token)
├── model_config.yaml                   # dumped env/algo config, for cross-checking obs dims
├── observation_config.yaml             # SEED from policy/release -- verify before trusting, see below
└── motion/s_batido_v3_recovery/        # CSV bundle, ready for --motion-data
```

### Observation config caveat

`gear_sonic_deploy`'s `observation_config.yaml` is a hand-authored C++-side
file (there is no Python code that emits it automatically), and it differs
per released checkpoint (compare `policy/release/observation_config.yaml`
vs `policy/sonic_v1_1/observation_config.yaml` -- different obs terms and
total dims). `export_onnx.sh` seeds `deployment/observation_config.yaml`
from the original release config because this fine-tune is a continuation
of that checkpoint's weights, not a new architecture -- but **verify this
before trusting a MuJoCo result**: compare the obs term names/order/dims in
`deployment/model_config.yaml` (`env_config.obs`) against
`deployment/observation_config.yaml`. A mismatch here produces a fast,
violent failure that looks like a dynamics problem but isn't (see
Interpretation below).

### 2. Known-good baseline (Milestone 2)

Before touching the fine-tuned policy, confirm NVIDIA's own release policy
works end to end in MuJoCo:

```bash
./scripts/run_mujoco_eval.sh --stock
```

Prints the two commands to run (Terminal A: simulator, Terminal B:
controller). If this doesn't work, the environment/build is broken --
fix that before testing the fine-tuned policy.

### 3. Reference motion kinematic check (Milestone 3)

```bash
cd ~/GR00T-WholeBodyControl/gear_sonic_deploy
python visualize_motion.py --motion_dir <project>/deployment/motion/s_batido_v3_recovery
```

Confirms orientation, root trajectory, left/right joints, foot contact, and
timing look correct in MuJoCo's coordinate system -- kinematic only, no
physics/policy involved yet.

### 4. Fine-tuned policy (Milestone 4/5)

```bash
./scripts/run_mujoco_eval.sh \
    --policy deployment/model_step_000600 \
    --motion deployment/motion/s_batido_v3_recovery
```

### Stopping

Ctrl+C both terminals. Terminal B (the controller) should be stopped first
if the robot is upright, to avoid an uncontrolled drop; in `sim` mode this
only affects the MuJoCo scene, not real hardware.

## Interpretation

| Isaac | MuJoCo | Reading |
|---|---|---|
| PASS | immediate violent joint movement | Integration bug (obs/joint/action ordering, scaling, config mismatch) -- not evidence about the policy |
| PASS | starts correctly, tracks, loses balance during the hard landing | Genuine dynamics/robustness gap -- interesting |
| PASS | PASS | Stronger evidence of a robust policy than Isaac alone; still not a real-robot guarantee |

Before concluding "the policy doesn't generalize," rule out: observation
ordering/normalization, joint ordering, action ordering/scaling, control
frequency, sim timestep, PD gains, motor parameters, default joint
positions, motion coordinate system, root orientation convention -- per the
observation-config caveat above, this is the most likely first failure mode
here specifically.

If a failure survives that check, the next step is improving Isaac-side
domain randomization and re-running fine-tuning, then re-evaluating both
Isaac and MuJoCo with the new checkpoint -- not tuning against MuJoCo
directly.

Run multiple trials (target: 10) before drawing conclusions; one pass/fail
is not enough to characterize robustness.
