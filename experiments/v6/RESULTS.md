# V6 buffered capoeira results

V6 adds an explicit stationary start and end around the capoeira motion:

- frames 0–49: deployment standing pose
- frames 50–84: smooth approach
- frames 85–109: eased launch
- frames 110–177: capoeira highlight
- frames 178–252: landing and recovery
- frames 253–327: final standing hold

The policy was fine-tuned for 400 iterations from the V5 stage-2 checkpoint.
Checkpoints were preserved every 50 iterations. The last checkpoint was not
selected automatically: MuJoCo screening showed a strong regression after
step 300, so step 300 is preserved as the best V6 candidate.

## Selected candidate

- checkpoint: `checkpoints/v6/selected_step300/s_batido_v6_buffered_step_000300.pt`
- Isaac full video: `videos/v6/s_batido_v6_buffered_step300_full_isaac.mp4`
- ONNX parity maximum absolute error: `1.85e-6` or lower

## Isaac Sim cross-validation

Step 300 completed all 20 evaluation runs:

| Profile | Runs completed | Mean progress | Mean local MPJPE |
|---|---:|---:|---:|
| hardware nominal | 5/5 | 1.000 | 99.3 mm |
| hardware moderate | 5/5 | 1.000 | 102.5 mm |
| hardware official | 5/5 | 1.000 | 102.4 mm |
| recovery push | 5/5 | 1.000 | 102.5 mm |

The full diagnostic render contains 327 encoded frames at 50 fps and lasts
6.54 seconds. The reference has 328 samples; the recorder emits one fewer
encoded frame because the final sample closes the rollout.

## Official C++ / MuJoCo cross-validation

The one-run checkpoint screen initially made step 300 look promising: it
passed the start gate, completed 328 motion frames, and ended with upright
0.991, joint-speed peak 0.404 rad/s, and base-angular-speed peak 0.263 rad/s.

The clean 10-run confirmation did **not** reproduce that result:

- initial safety gate: 1/10
- command completion: 1/10
- full 328-frame motion: 1/10
- final stability gate: 0/10
- successful run final upright minimum: 0.311 (required >= 0.95)
- successful run final joint-speed peak: 14.10 rad/s (required <= 2.5)
- successful run final base-angular-speed peak: 5.46 rad/s (required <= 0.6)
- motion torque peak: 139 Nm

## Conclusion

V6 validates the buffered motion and is robust inside Isaac Sim, but it is
**not ready for a physical G1**. The official MuJoCo result exposes a simulator
transfer gap at both policy engagement and post-landing recovery. A future
stage should train against the measured MuJoCo failure distribution instead
of weakening the safety gate.
