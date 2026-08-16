# SONIC V8 Landing-Recovery Results

## Decision

The final preserved V8 candidate is `step 25`. All 112 unique
checkpoint/profile/seed combinations completed the motion in Isaac Sim, but
post-landing final stabilization succeeded in only 3 of 10 official C++
closed-loop MuJoCo runs. The model is therefore **not real-robot ready and must
not be run on a physical G1**.

## Training

- Base model: V7 targeted final, fresh optimizer
- Environments / iterations: 384 environments, 300 iterations
- Final mean reward: 51.04432
- Final mean episode length: 337.77
- Time-out completion: 0.7466
- Mean adaptive failure rate: 0.0173
- Final checkpoint: `model_step_000300.pt`
- Selected checkpoint: `checkpoints/v8/s_batido_v8_landing_step_000025.pt`

## Isaac Sim Cross-Validation

- Twelve checkpoints at 25-step intervals were evaluated under
  nominal, moderate, official, and recovery-push profiles.
- Total unique evaluations: 112/112 full-motion completions, progress rate 1.0.
- Step 25 completed 20/20 runs: five seeds in each of the four profiles.
- Isaac completion alone cannot establish closed-loop post-landing stability,
  so MuJoCo results were used as the final safety criterion.

## Official C++ / MuJoCo Closed Loop

Every candidate passed the initial safety gate 10/10 without bypassing it and
executed all 467 motion frames 10/10. The difference appeared in final
post-landing standing stability.

| Checkpoint | Initial stability | Full motion | Final stability | Final stability rate |
| --- | ---: | ---: | ---: | ---: |
| Step 25 | 10/10 | 10/10 | 3/10 | 30% |
| Step 125 | 10/10 | 10/10 | 2/10 | 20% |
| Step 275 | 10/10 | 10/10 | 0/10 | 0% |
| Step 300 | 10/10 | 10/10 | 1/10 | 10% |

The main failure begins during recovery, approximately frames 307–344. Seeds
that fail to bring the capture point back inside the support polygon after
landing develop increasing joint speed and base angular velocity; some joints
reach the 139 Nm torque limit. Upright posture then collapses. Successful-seed
videos are preserved, but physical-robot deployment remains blocked.

## ONNX and Videos

- Encoder parity maximum absolute difference: 0.0
- Decoder parity maximum absolute difference: 1.6689300537109375e-6
- All parity outputs are finite.
- Isaac: `videos/v8/v8_step025_isaac_full.mp4` (H.264, 1920×1088, 50 fps,
  466 frames, 9.32 seconds)
- MuJoCo: `videos/v8/v8_step025_mujoco_closed_loop.mp4` (H.264, 960×720,
  30 fps, 617 frames, 20.57 seconds)

Raw evaluation logs and per-seed telemetry are preserved under `exports/v8`
and `exports/evaluations/v8_*`. GPU-specific TensorRT engines are excluded
because they are not reproducible ONNX artifacts.
