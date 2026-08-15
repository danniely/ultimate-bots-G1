# V5 stability results

## Decision

V5 Stage 2 is **not cleared for physical G1 deployment**. It preserved the
181-frame capoeira motion in Isaac Lab and completed all 20 hardware-profile
evaluations, but the official MuJoCo deployment loop failed the pre-motion
settled-start safety gate in all 10 runs. The motion command was intentionally
not released after those failures.

## Isaac Lab

Stage 2 completed 150 refinement iterations from the V5 Stage 1 checkpoint
using a fresh optimizer. It then completed 5/5 runs in each profile:

| Profile | Success | Mean local MPJPE |
|---|---:|---:|
| Hardware nominal | 5/5 | 60.1 mm |
| Moderate randomization | 5/5 | 58.8 mm |
| Official randomization | 5/5 | 67.7 mm |
| Recovery push | 5/5 | 58.8 mm |

The full Isaac render contains 180 encoded frames at 50 FPS (3.60 seconds); the
telemetry contains all 181 reference samples including the terminal sample.

Compared with V4 telemetry, V5 reduced the feet/ankles contact-force peak from
1016 N to 519 N and the joint-acceleration peak from 1128 rad/s^2 to 733
rad/s^2. The joint-speed peak fell from 22.21 rad/s to 21.26 rad/s. However,
the single-run Isaac torque peak increased from 88.99 Nm to 116.22 Nm and
nominal tracking error increased from about 49.5 mm to 60.1 mm.

## Official MuJoCo settled-start gate

Each run required 0.5 continuous seconds with world-up at least 0.95, peak
joint speed no greater than 2.5 rad/s, and base angular speed no greater than
0.6 rad/s before sending the motion command.

| Result | Value |
|---|---:|
| Settled starts | 0/10 |
| Mean minimum world-up | 0.925 |
| Mean peak joint speed | 22.87 rad/s |
| Mean peak base angular speed | 2.45 rad/s |

The failure is a launch-controller/sim2sim stability blocker. Lower impact and
acceleration during Isaac motion playback do not compensate for the inability
to hold a safe pre-motion stance in the official deployment loop.

## Preserved artifacts

- Stage 1 checkpoint: `checkpoints/v5/stability/`
- Stage 2 checkpoint: `checkpoints/v5/stability_stage2/`
- Isaac video: `videos/v5/s_batido_v5_stage2_full_isaac.mp4`
- Hardware-risk telemetry: `exports/v5/stability/stage2_final/metrics/`
- MuJoCo gate summary: `exports/v5/stability/stage2_final/sim2sim_matrix/`

The next revision should separate a verified standing controller from the
motion policy and use a gated, smooth handoff instead of asking the motion
policy itself to settle the initial stance.
