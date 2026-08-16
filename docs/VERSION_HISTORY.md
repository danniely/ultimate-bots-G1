# SONIC Capoeira Engineering Journal: V0–V8

This journal records why each version was created, what changed, how it was
validated, and what remained unresolved. A version number represents a new
engineering hypothesis rather than simply more training iterations.

## Validation approach

Training and primary evaluation ran in NVIDIA Isaac Sim. Deployment-oriented
cross-validation used the official C++ controller and MuJoCo loop. This split
made validation difficult: a policy could look stable in Isaac Sim yet fail in
MuJoCo because contact resolution, friction, actuator response, initialization,
and policy handoff were different. Visual inspection, synchronized telemetry,
and repeated multi-seed tests were therefore treated as part of the development
loop rather than as a final presentation step.

## V0 — Pristine SONIC release baseline

**Question:** Can the unmodified `sonic_release/last.pt` policy execute the new
capoeira reference without task-specific training?

**Method:** The original policy was evaluated against the 81-frame reference.
For recording only, the final pose was repeated for two seconds and early
tracking termination was disabled. Policy weights and actions were unchanged.

**Result:** The pelvis fell below 0.50 m at frame 16 and below 0.40 m at frame
21. The robot lost the reference before the kick and remained on the floor
during the diagnostic buffer.

**Lesson:** The release model provided a useful motion prior, but a new dynamic
skill required task-specific fine-tuning.

## V1 — Uniform full-motion tracking

**Problem addressed:** V0 could not follow the custom `s_batido` sequence.

**Changes:**

- Fine-tuned from `sonic_release/last.pt` with 512 parallel environments.
- Trained all 81 frames for 2,000 iterations at a `2e-5` actor learning rate.
- Applied the standard SONIC full-body tracking objective uniformly across the
  whole motion.

**Result:** The policy learned the broad movement, but the airborne highlight
lacked sufficient launch energy and right-leg extension. Landing balance was
also weak. The final snapshot reported mean reward `2.8666`, mean episode length
`44.17`, body-position error `0.1105`, and joint-position error `0.1823`.

**Lesson:** Treating every frame equally encouraged average tracking quality but
did not prioritize the visually and dynamically critical kick.

## V2 — Phase-specific highlight learning

**Problem addressed:** V1 underperformed on the most important airborne phase.

**Changes:** The 81-frame motion was divided into support, launch, airborne
highlight, and landing segments. Each segment received different rewards for
support contact, pelvis vertical velocity, right-leg pose, pelvis orientation,
and landing position.

### Stage 1: highlight priority

- Started from V1 step 2000 with a fresh optimizer and `5e-6` learning rate.
- Temporarily removed end-effector early termination and startup physics
  randomization so the policy could experience the launch and kick repeatedly.

**Result:** Reached frame 69/81 and produced the clearest airborne rotation and
right-leg kick among V2 candidates.

### Stage 2: robustness priority

- Continued from Stage 1 while restoring strict end-effector termination and
  physics randomization.

**Result:** Active-frame tracking error improved, but the policy terminated at
frame 50/81 and did not reach the full highlight.

**Lesson:** Phase-specific rewards were effective, but strict gates introduced
too early could prevent the policy from collecting experience in later phases.

## V3 — Landing and upright recovery

**Problem addressed:** V2 ended immediately after the highlight and did not
demonstrate controlled recovery.

**Changes:**

- Branched from V2 Stage 1 step 1000, not from the stricter Stage 2 branch.
- Preserved the original 81 frames and appended 100 recovery frames: 50 frames
  returning toward upright and 50 frames holding the final pose.
- Added rewards for two-foot contact, upright pelvis orientation, low pelvis
  linear/angular velocity, and pelvis projection near the foot-support center.
- Reduced the learning rate to `2e-6` to limit forgetting of the kick.

**Result:** Step 600 completed 181/181 samples in Isaac Sim. The recorded nominal
evaluation reported 98% two-foot contact during recovery, mean pelvis speed
`0.0630 m/s`, and pelvis-to-foot-center distance `0.0153 m`.

**Lesson:** Recovery needed an explicit reference horizon and its own objective;
it did not emerge automatically from pose imitation.

## V4 — Real-robot-readiness and hardware-risk pass

**Problem addressed:** V3 was successful in a nominal Isaac run but had not been
optimized against disturbances or actuator/contact risk.

**Changes:**

- Continued from V3 step 600 with a fresh optimizer.
- Replaced source-motion absolute wrist, foot, pelvis, and orientation gates
  with phase-aware physical failure conditions.
- Added friction, joint-offset, center-of-mass, and mass randomization.
- Added recovery pushes plus penalties for dangerous non-foot contact, hand and
  landing overload, excessive joint speed, and high actuator demand.

**Result:** The selected step 100 reached 20/20 strict nominal, 20/20 moderate,
18/20 official-randomization, and 20/20 recovery-push runs in Isaac. Compared
with original V3, measured dangerous non-foot impact dropped from `2278.69 N`
to `0 N`, and foot/ankle peak contact dropped from `1788.99 N` to `1016.47 N`.
The official MuJoCo loop completed the motion 10/10 times but recovered upright
in only 6/10, while motor torque reached the `139 Nm` limit in every run.

**Lesson:** Isaac robustness gains did not guarantee repeatable deployment-loop
recovery. Torque saturation became a first-class selection metric.

## V5 — Settled launch and actuator stability

**Problem addressed:** V4 MuJoCo failures mixed an unsafe startup state with
motion-policy recovery failures.

**Changes:**

- Required 0.5 seconds of continuous upright and low-velocity state before
  releasing the motion command.
- Added knee torque reserve, joint-speed penalties above `2.5 rad/s`, stronger
  two-foot support, launch/recovery upright rewards, and action smoothing.
- Ran a second refinement stage after ankle/knee oscillation remained visible.

**Result:** V5 preserved the 181-frame move across 20/20 Isaac hardware-profile
runs. Relative to V4, the Isaac foot/ankle contact peak fell from `1016 N` to
`519 N`, joint-acceleration peak from `1128` to `733 rad/s²`, and joint-speed
peak from `22.21` to `21.26 rad/s`. However, the official MuJoCo settled-start
gate passed 0/10, so the kick command was correctly withheld.

**Lesson:** A motion policy should not be expected to repair an incompatible
deployment initialization. Standing control and policy handoff had to be made
explicit.

## V6 — Buffered standing start and end

**Problem addressed:** Isaac started directly from a dynamic reference pose,
while deployment handed control from the G1 default standing pose.

**Changes:** Built a 328-sample reference with an exact standing start, smooth
approach, eased launch, original capoeira highlight, velocity-continuous landing
coast, recovery, and final standing hold. Fine-tuning ran for 400 iterations
from V5 Stage 2.

**Result:** Step 300 completed all 20 Isaac profile runs. A single MuJoCo screen
looked successful, but the clean ten-run confirmation reproduced only 1/10
initial gates, 1/10 full motions, and 0/10 final stability gates; motion torque
again peaked at `139 Nm`.

**Lesson:** Single successful rollouts were not reliable evidence. Clean
multi-run confirmation became mandatory for every candidate.

## V7 — Startup diagnosis and targeted retiming

**Problem addressed:** V6 combined true policy failures with an incorrect
standing diagnostic and an abrupt reference-velocity discontinuity.

**Changes:**

- Tested the official standing controller without sending a motion command.
- Corrected startup order: policy engagement first, then safety-band release.
- Rejected a wide retiming that created an unrealistic 69-frame hover.
- Added only five interpolation samples around the two sharp discontinuities,
  preserving every key pose while reducing the target spike from `50.1` to
  `16.7 rad/s`. The final reference contained 333 frames.
- Fine-tuned with torque-reserve, action-rate, joint-acceleration, landing, and
  recovery objectives.

**Result:** The corrected standalone standing test passed 10/10. The selected V7
policy completed 20/20 Isaac profile runs, then passed 10/10 MuJoCo starts and
10/10 full 333-frame motions. Strict final stabilization passed 2/10; failed
runs still showed high joint/base angular velocity and `139 Nm` saturation.

**Lesson:** Fixing the harness removed a false failure, while local retiming was
better than globally slowing the skill. Landing energy still exceeded the
recovery controller's reliable capture region.

## V8 — Landing-recovery specialization

**Problem addressed:** V7 executed the skill but recovered reliably in only a
minority of MuJoCo seeds.

**Changes:**

- Kept the capoeira highlight unchanged through frame 167.
- Slowed touchdown by 3× and recovery by 2×.
- Retained a 75-frame exact deployment-standing hold, producing 467 samples at
  50 Hz.
- Optimized capture point over the two-foot support area, recovery joint speed,
  landing contact overload, knee torque reserve, and randomized actuator
  stiffness/damping.
- Trained 300 iterations with 384 environments on a preemptible H100, saving
  every 25 iterations.

**Result:** All 112 unique Isaac checkpoint/profile/seed evaluations completed.
The selected step 25 completed 20/20 Isaac profile runs. In the official MuJoCo
loop it passed 10/10 initial gates and 10/10 full 467-frame motions, but strict
final stabilization passed only 3/10. ONNX parity error was `0` for the encoder
and `1.6689300537109375e-6` maximum absolute difference for the decoder.

**Lesson:** Slower landing and explicit capture-point optimization improved the
best observed recovery rate without sacrificing the kick, but recovery remained
seed-sensitive. The selected V8 policy is a simulation result and is **not
approved for physical G1 deployment**.

## Current release artifacts

- Before/after video: [`videos/G1 Robot.mp4`](../videos/G1%20Robot.mp4)
- V8 final report: [`exports/v8/FINAL_REPORT.md`](../exports/v8/FINAL_REPORT.md)
- ONNX policy: <https://huggingface.co/hyunho7979/sonic-capoeira-v8>
- Motion dataset: <https://huggingface.co/datasets/hyunho7979/sonic-capoeira-v8>
