# V5 stability pass

V4 preserved the capoeira highlight and improved Isaac robustness, but its first
official MuJoCo matrix recovered upright in only 6/10 runs.  The audit found two
separate causes that must not be mixed together:

1. The old harness launched the motion after a fixed two-second delay.  One run
   began with world-up `-0.047`, and most began below `0.91`, so the baseline was
   partly measuring a bad launch sequence rather than the learned motion.
2. Both knee motors repeatedly reached the exact 139 Nm deployment limit.

The V5 workflow first requires 0.5 seconds of continuous upright, low-velocity
state before sending the motion command.  If the corrected V4 baseline remains
below 19/20, fine-tuning continues from V4 with:

- a soft pre-clipping knee torque reserve (115 Nm overall, 105 Nm in recovery);
- explicit upright and low-velocity rewards over the first 20 motion frames, so
  the deployed controller can hold a settled launch pose before playback;
- a second stability refinement stage after the first MuJoCo gate exposed
  persistent ankle/knee oscillation despite an upright torso; this stage extends
  the launch window to 35 frames and directly penalizes joint speed above
  2.5 rad/s while strengthening two-foot support and action smoothing;
- stronger late-recovery upright and low-base-velocity rewards;
- slightly stronger action-rate smoothing;
- wider but still moderate friction, joint-zero, COM, mass, and recovery-push
  randomization;
- a stricter late-recovery fall gate.

Checkpoint selection remains lexicographic: full motion and highlight retention,
then settled MuJoCo recovery rate, then knee saturation count, torque p99, joint
speed, and tracking error.  The target is at least 19/20 settled-start MuJoCo
recoveries with fewer knee-saturation frames than V4.
