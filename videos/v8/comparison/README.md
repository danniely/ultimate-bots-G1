# Isaac Sim baseline for V8 comparison

`sonic_base_step2000_isaac_full.mp4` is the preserved Isaac Sim rollout for the
original SONIC checkpoint:

- checkpoint: `checkpoints/final/s_batido_sonic_step_002000.pt`
- motion: `data/motion_lib/s_batido_test.pkl`
- reference: 81 frames / 1.60 s
- encoded video: H.264 High, yuv420p, 1920x1088, 25 fps, 40 frames
- SHA-256: `4905e5c471a13cfe22339e329eb1e5ef91a7347239deffe6d473aeb73d5cb617`

The video includes the full original capoeira rollout. It is a baseline model
artifact, not a V8 rollout. V8 uses a longer buffered reference, so raw video
timestamps are not directly aligned. Compare the kick and landing phases rather
than matching timestamps from the start of each video.

V8 comparison video: `../v8_step025_isaac_full.mp4`.
