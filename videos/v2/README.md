# SONIC v2 Isaac Sim videos

These filenames describe the purpose of each training phase instead of using the ambiguous labels "Stage 1" and "Stage 2".

- `highlight_priority_relaxed_physics_isaac.mp4`: the competition/highlight candidate. It was trained with relaxed termination checks and without physics randomization so that the policy could reach the airborne kick highlight.
- `robustness_priority_strict_physics_isaac.mp4`: the stricter-physics candidate. It continued from the highlight-priority policy with strict hand/foot termination checks and physics randomization restored.
- `highlight_priority_relaxed_physics_full_motion_isaac.mp4`: the same highlight-priority policy rendered through the complete reference-motion timeline, with early failure termination disabled for diagnosis.
- `robustness_priority_strict_physics_full_motion_isaac.mp4`: the same robustness-priority policy rendered through the complete reference-motion timeline, with early failure termination disabled for diagnosis.

All videos are closed-loop SONIC policy evaluations rendered in Isaac Sim on RunPod. They are not MuJoCo trajectory replays.

The `full_motion` videos do not turn a failed rollout into a successful one. They intentionally continue after the original failure thresholds (frame 69 for the highlight-priority policy and frame 50 for the robustness-priority policy) so the remaining physical behavior can be inspected. The 81-frame reference timeline contains 80 simulation intervals, so each MP4 contains 80 encoded frames at 50 fps (1.6 seconds).
