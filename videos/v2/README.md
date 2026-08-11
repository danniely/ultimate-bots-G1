# SONIC v2 Isaac Sim videos

These filenames describe the purpose of each training phase instead of using the ambiguous labels "Stage 1" and "Stage 2".

- `highlight_priority_relaxed_physics_isaac.mp4`: the competition/highlight candidate. It was trained with relaxed termination checks and without physics randomization so that the policy could reach the airborne kick highlight.
- `robustness_priority_strict_physics_isaac.mp4`: the stricter-physics candidate. It continued from the highlight-priority policy with strict hand/foot termination checks and physics randomization restored.

Both videos are closed-loop SONIC policy evaluations rendered in Isaac Sim on RunPod. They are not MuJoCo trajectory replays.
