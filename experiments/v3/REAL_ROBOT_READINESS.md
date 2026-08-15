# V3 Real-Robot Readiness Report

## Decision

The selected corrective checkpoint is `s_batido_v3_realready_step_000100.pt`.
It is a substantial improvement over the original V3 checkpoint in Isaac Lab,
but it is **not cleared for an untethered physical G1**. The official MuJoCo
deployment loop exposed recovery inconsistency and actuator saturation that the
Isaac-only evaluation did not reveal.

## What changed after V3

- Continued from the original V3 step 600 actor and critic with a fresh optimizer.
- Replaced source-motion absolute wrist, foot, pelvis, and full-orientation hard
  gates with phase-aware physical failure conditions.
- Added moderate friction, joint-offset, center-of-mass, and mass randomization.
- Added recovery-window pushes and penalties for dangerous body contact, hand and
  landing overload, excessive joint speed, and high actuator demand.
- Trained 300 additional iterations with 512 parallel environments and saved every
  50 iterations.

## Isaac Lab selection

All six corrective checkpoints completed 5/5 nominal and 5/5 moderate-randomized
screening runs. Step 100 was selected after the larger evaluation matrix:

| Profile | Step 50 | Step 100 |
|---|---:|---:|
| Strict nominal | 20/20 | 20/20 |
| Moderate randomization | 20/20 | 20/20 |
| Official randomization | 11/20 | 18/20 |
| Recovery push | 20/20 | 20/20 |

For step 100, nominal local MPJPE was about 49.5 mm and official-randomization
MPJPE was about 64.7 mm. The original V3 checkpoint failed all four 20-seed
physical matrices near 27.5% progress because it produced unsafe non-foot body
contact.

## Hardware-risk telemetry

Compared with original V3, step 100 removed the measured dangerous non-foot body
impact in the Isaac diagnostic run and lowered several peaks:

| Metric | Original V3 | Step 100 |
|---|---:|---:|
| Dangerous other-body contact peak | 2278.69 N | 0 N |
| Feet/ankles contact peak | 1788.99 N | 1016.47 N |
| Wrist/hand contact peak | 1988.86 N | 1632.82 N |
| Torque peak | 91.86 Nm | 88.99 Nm |
| Joint-speed peak | 21.98 rad/s | 22.21 rad/s |
| Joint-acceleration peak | 1051.61 rad/s² | 1127.63 rad/s² |

These are simulator measurements, not certified Unitree limits.

## Deployment artifacts

The official NVIDIA exporter produced G1, SMPL, teleop, encoder, and decoder
ONNX models. ONNX structural checks and finite deterministic inference passed for
all five. PyTorch and ONNX Runtime were also compared using the exact same export
inputs: the largest absolute difference across all five exports was
`3.81e-6` (encoder-only: exactly zero). The official C++ frequency test ran
1,000 random-input inferences:

| Model | Mean latency | Maximum measured rate |
|---|---:|---:|
| G1 combined | 0.384 ms | 2604 Hz |
| Encoder | 0.401 ms | 2492 Hz |
| Decoder | 0.259 ms | 3854 Hz |

This easily exceeds the 50 Hz control-loop requirement on the Nebius H100 host,
but it does not predict onboard Orin latency.

## Official MuJoCo sim2sim result

Ten independent runs used NVIDIA's C++ `g1_deploy_onnx_ref`, TensorRT 10.13, the
official MuJoCo G1 loop, the exported encoder/decoder pair, and a fully reconstructed
14-body deployment reference. The simulator and controller were restarted before
every run.

- Motion command completion: **10/10**
- Full 181-frame playback: **10/10**
- Upright recovery two seconds after landing (`world-up >= 0.8`): **6/10**
- Maximum observed joint speed: **39.46 rad/s**
- Maximum observed motor torque: **139 Nm in every run**

The policy can execute the full choreography in a second simulator, but recovery
is not repeatable enough and torque saturation is systematic. This is a real-robot
deployment blocker, not merely a presentation-quality issue.

## Physical-robot gate

Before an untethered attempt, require all of the following:

1. Confirm joint-specific G1 firmware torque and velocity limits with the event team.
2. Reach at least 19/20 successful official MuJoCo recoveries without the 139 Nm
   saturation pattern.
3. Run first on a gantry or overhead tether with an operator holding E-stop.
4. Test stand and low-amplitude recovery before enabling the kick phase.
5. Increase amplitude in stages while logging joint position, velocity, torque,
   IMU orientation, temperatures, and safety-stop reasons.

Until those gates pass, use step 100 for submission and simulation evidence, but
label it as a candidate requiring supervised hardware validation.

## Reproducibility artifacts

- Selected checkpoint: `checkpoints/v3/realready/s_batido_v3_realready_step_000100.pt`
- Full Isaac video: `videos/v3/s_batido_v3_realready_step100_full_isaac.mp4`
- ONNX/TRT exports and parity report: `exports/v3/realready/final/onnx/`
- Ten-run MuJoCo state logs: `exports/v3/realready/final/sim2sim_matrix/`
- The video is 50 FPS and preserves all 181 reference samples, including the
  terminal pose at 3.60 seconds.
