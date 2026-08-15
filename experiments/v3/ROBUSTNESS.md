# v3 real-robot readiness pass

The selected v3 step-600 checkpoint remains immutable.  This pass answers a
different question from the full-motion render: how likely is the controller
to finish on a physical Unitree G1 when model parameters and contacts differ
from Isaac Sim?

## Why the old video is not enough

The v3 full-motion video was intentionally rendered with only the motion
timeout termination.  It proves that the policy can produce all 181 reference
frames in Isaac Sim, but it does not prove that it remains inside the normal
SONIC tracking limits.  The v3 training config also removed material, joint
offset, COM, and mass randomization.  Its interval push starts after 4 seconds,
while the motion lasts only 3.62 seconds, so the push never occurs.

## New curriculum

`scripts/start_sonic_v3_robust.sh` starts from v3 step 600 with a fresh
optimizer.  It restores all stock SONIC terminations, uses a low learning rate,
and enables moderate randomization for friction, restitution, joint zero
offset, torso COM, and wrist/torso mass.  A small push is scheduled during the
landing-recovery window instead of after the motion is over.

The original v3 telemetry showed roughly 1.99 kN peak wrist/hand contact,
1.79 kN peak foot/ankle contact, and a 22 rad/s peak ankle speed in the
diagnostic rollout.  Soft hinge penalties therefore activate only above 400 N
at the supporting hand, 1200 N at landing, and 15 rad/s at any joint.  These
are training regularizers rather than certified G1 safety limits; the final
values still have to be checked against the exact competition robot and its
firmware limits.

This is deliberately a robustness pass, not a new choreography pass.  The v3
phase rewards remain unchanged so the airborne right-leg highlight and the
two-second landing recovery do not lose priority.

## Evaluation matrix

`scripts/run_v3_strict_matrix.sh` creates isolated checkpoint contexts without
modifying the selected `.pt` or its original config.  It runs four profiles:

1. `strict_nominal`: stock tracking terminations, no randomization.
2. `moderate_randomization`: the same ranges used for robust fine-tuning.
3. `official_randomization`: the full stock SONIC randomization ranges.
4. `recovery_push`: nominal physics plus a perturbation during recovery.

The stock `ee_body_pos` termination treats both wrists as hard height gates.
For this motion it cuts every checkpoint at frame 50, exactly at the intended
support-hand release, so it is preserved as a stock-compatibility result but
cannot rank real-robot readiness.  Four matching `hardware_*` profiles remove
the wrist and absolute foot-position hard gates.  The source itself contains
hand/foot ground penetration, so those reference coordinates cannot be treated
as physical truth.  Full quaternion error is also not a fall detector because
it includes the intentional spin around world Z.  The hardware profiles use a
phase-aware base gate instead: during the acrobatic phase it ignores heading,
allows the intended large tilt, but rejects a very low pelvis or impact on the
pelvis, torso, or head.  After the first second of recovery it requires
world-upright posture and minimum pelvis height.  Timeout remains a hard
completion gate;
wrist/foot tracking, ground contact, overload and slip are evaluated as
continuous telemetry instead of being ignored.

Five seeds screen every saved checkpoint.  The strongest checkpoints are then
rerun over twenty seeds.  Selection is lexicographic: completion and reaching
the highlight come before MPJPE or reward.  A policy that tracks beautifully
and then falls is not allowed to beat a less exact policy that completes.

## Deployment gate

An Isaac winner is only a candidate.  Before real hardware it must also pass:

- ONNX export and deterministic output comparison against PyTorch;
- the deployment binary frequency test;
- the official C++ SONIC controller connected to the MuJoCo simulation loop;
- repeated full-motion runs with state CSV logging;
- inspection of peak wrist/foot contact force, applied torque, joint velocity,
  acceleration, and action smoothness.

Real G1 execution should begin on an overhead gantry with an emergency-stop
operator, reduced action scale, and a staged speed ramp.  Simulation reduces
risk but cannot certify real-robot safety.
