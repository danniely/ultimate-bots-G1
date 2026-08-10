# SONIC v2 training results

## Selected checkpoint

`stage1/s_batido_v2_stage1_step_001000.pt` is the selected competition/highlight candidate.

Stage 1 reached frame 69 of 81 (85.2%) in the recorded evaluation, including most of the airborne highlight. Stage 2 tracked positions more accurately while it remained active, but terminated at frame 50 of 81 (61.7%), before completing the highlight.

Both checkpoints are preserved because Stage 2 remains useful as a stricter-physics baseline.

## Final training snapshot

| Metric | Stage 1 | Stage 2 |
|---|---:|---:|
| Iterations | 1,000 | 1,000 |
| Mean reward | 6.7442 | 4.3304 |
| Mean episode length | 65.96 | 44.20 |
| Body position error | 0.1473 | 0.1081 |
| Joint position error | 0.2139 | 0.1604 |
| Takeoff pelvis vertical-velocity reward | 0.0552 | 0.0509 |
| Airborne right-leg position reward | 0.0926 | 0.0330 |
| Airborne right-leg joint-pose reward | 0.0458 | 0.0172 |
| Dominant termination | anchor orientation (93.86%) | end-effector body position (92.76%) |

## Recorded evaluation

| Metric | Stage 1 | Stage 2 |
|---|---:|---:|
| Success rate | 0% | 0% |
| Progress | 69/81 (85.2%) | 50/81 (61.7%) |
| Global MPJPE | 99.199 | 77.016 |
| Local MPJPE | 52.788 | 39.154 |
| PA MPJPE | 34.900 | 27.552 |
| Leg global MPJPE | 99.524 | 76.754 |
| Leg local MPJPE | 58.709 | 50.559 |
| Acceleration distance | 11.631 | 10.076 |
| Velocity distance | 19.722 | 16.900 |

Lower MPJPE and distance values are better. These are single recorded rollouts, and Stage 2 uses the restored strict termination and physics-randomization settings, so the values should be treated as diagnostic evidence rather than a statistically complete benchmark.

## Artifact map

- Stage 1 checkpoint: `../../checkpoints/v2/stage1/s_batido_v2_stage1_step_001000.pt`
- Stage 2 checkpoint: `../../checkpoints/v2/stage2/s_batido_v2_stage2_step_001000.pt`
- Stage 1 video and frame telemetry: `../evaluations/v2_stage1_final/`
- Stage 2 video and frame telemetry: `../evaluations/v2_stage2_final/`
- Training logs: `stage1/train.log` and `stage2/train.log`

## Checkpoint integrity

| Checkpoint | SHA-256 | Size |
|---|---|---:|
| Stage 1 | `459af783b334280d3d8986241248bc39ba69e8ce3fbf306da29f363a49b9bfd5` | 448,604,139 bytes |
| Stage 2 | `a1e03426b9f84ff44ef30a9362acd6d3aee3d169187e59d3fbeba6dcbb6972d1` | 448,604,139 bytes |
