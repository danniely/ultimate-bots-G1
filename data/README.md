# Motion dataset

`source/lafan/s_batido_test.csv` is the original 49-frame, 30 FPS retargeted
motion exported from Ultimate Bots Studio.

`source/sonic/s_batido_test_sonic/` is the Studio-produced SONIC CSV bundle:

- 81 frames at 50 FPS
- `joint_pos.csv`: 29 G1 joint positions
- `body_pos.csv`: pelvis world position
- `body_quat.csv`: pelvis world orientation
- velocity files and metadata retained for reproducibility

The official NVIDIA converter turns this directory into
`data/motion_lib/s_batido_test.pkl`. Generated PKLs are reproducible outputs and
are not committed by default.

`source/sonic/s_batido_v3_recovery_sonic/` preserves those 81 frames and adds
100 frames (2 seconds at 50 FPS) for landing recovery. The first second eases
to the motion's initial stable stance at the landing location; the second
second holds it. Rebuild it reproducibly with:

```bash
python3 scripts/build_v3_recovery_motion.py \
  data/source/sonic/s_batido_test_sonic \
  data/source/sonic/s_batido_v3_recovery_sonic
```
