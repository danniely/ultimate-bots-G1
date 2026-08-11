# SONIC v3 final selection

- Selected checkpoint: `s_batido_v3_recovery_step_000600.pt`
- Source checkpoint: v2 Stage 1 step 1000 with a fresh optimizer
- Training: 512 environments, 750 iterations, checkpoints every 50 iterations
- Reference motion: 181 samples at 50 FPS (81 original + 100 landing-recovery samples)
- Normal physics evaluation: 100% progress, 100% success
- Rendered full video: 181 frames, 50 FPS, 3.62 seconds, 1920x1088

## Why step 600

All checkpoints from step 250 through step 750 completed the 181-sample physics evaluation. Step 600 was selected as the strongest balance between preserving the original highlight and stabilizing the two-second recovery:

- Mean recovery pelvis speed: 0.0630 m/s
- Mean pelvis-to-feet-center horizontal distance: 0.0153 m
- Double-foot contact rate during recovery: 98%
- Recovery joint RMSE: 0.2004 rad
- Full-motion local MPJPE: 46.360 mm
- Full-motion acceleration distance: 4.903
- Full-motion velocity distance: 9.505

Step 200 stopped after 70 frames. Steps 250-750 completed the sequence, but later checkpoints traded some highlight tracking accuracy for additional recovery-pose tracking. Step 600 provided the best overall compromise.
