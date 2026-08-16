# SONIC V0 — pristine release baseline

This is the unmodified NVIDIA `sonic_release/last.pt` policy evaluated in Isaac
Sim against the original 81-frame `s_batido` capoeira reference. Because the
standalone original PKL was absent on the evaluation VM, those 81 frames were
reconstructed exactly from the unchanged prefix of
`s_batido_v3_recovery.pkl`.

For diagnostic recording only, the final reference pose is repeated for 100
frames (2.0 seconds at 50 Hz) and early tracking terminations are disabled.
The policy, weights, observations, and actions are not changed. Therefore the
reported evaluator success is not a task-success result; it only means the
recording reached its 181-frame timeout.

## Result

- Canonical video: `../../videos/v0/sonic_release_v0_isaac_buffered.mp4`
- Codec / dimensions: H.264, 1920x1088
- Rate / length: 50 fps, 180 encoded frames, 3.60 seconds
- Reference motion: 81 original frames followed by a 100-frame diagnostic tail
- Pelvis below 0.50 m: frame 16, 0.32 seconds
- Pelvis below 0.40 m: frame 21, 0.42 seconds
- At diagnostic-tail start: frame 81, 1.62 seconds, pelvis height 0.260 m
- Peak absolute joint speed: 15.883 rad/s at frame 74 (1.48 seconds)

The pristine release policy does not execute the capoeira sequence. It loses
the reference almost immediately, reaches the floor before the kick portion,
and remains down during the requested two-second post-failure buffer.

`frames/env_000000_frames.npz` is the canonical telemetry. The CSV is included
for inspection. The release checkpoint itself is not duplicated here.
