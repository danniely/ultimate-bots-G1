# V6 buffered launch and recovery

V6 fixes the deployment-state mismatch discovered in the V5 MuJoCo audit.
Isaac evaluation previously teleported the robot directly into the dynamic
reference state, while the deployment controller handed control from the G1
default standing pose to a dynamic first frame.

The V6 reference contains 328 samples at 50 Hz:

| Frames | Phase |
|---:|---|
| 0-49 | Exact deployment standing pose, zero velocity |
| 50-84 | Smooth approach to the original first pose |
| 85-109 | Eased launch through original frames 0-12 |
| 110-177 | Original capoeira frames 13-80 |
| 178-252 | Velocity-continuous landing coast and recovery to deployment standing pose |
| 253-327 | Final standing hold, zero velocity |

Training starts from the V5 Stage 2 policy with a fresh optimizer. Checkpoint
selection requires preservation of the airborne highlight and full 328-frame
completion in Isaac, followed by the official ONNX/C++ MuJoCo loop from the
same default standing pose. The primary deployment gate is 0.5 continuous
seconds of world-up >= 0.95, peak joint speed <= 2.5 rad/s, and base angular
speed <= 0.6 rad/s before launch; the same thresholds are checked again during
the final hold.
