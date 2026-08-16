# SONIC V8 landing stability

V8 keeps the V7 capoeira highlight unchanged through frame 167, slows the
touchdown trajectory by 3x, slows the recovery trajectory by 2x, and retains a
75-frame exact deployment standing hold.  The resulting motion has 467 frames
at 50 Hz.

The fine-tune starts from the recovered V7 final checkpoint with a fresh
optimizer.  It directly optimizes a 2.5 rad/s recovery joint-speed ceiling,
capture point over the two-foot support area, lower landing contact overload,
stronger knee torque reserve, and randomized actuator stiffness/damping.

Run a 32-environment, 2-iteration smoke test first.  The production run uses
384 environments, 300 iterations, and a checkpoint every 25 iterations so it
can recover from a preemptible VM eviction.

Acceptance requires Isaac nominal/randomized completion followed by at least
10 official C++/MuJoCo trials.  A trial passes only if the full motion completes
and the final 75 frames maintain world-up >= 0.95, peak joint speed <= 2.5
rad/s, and peak base angular speed <= 0.6 rad/s.  The VM must be stopped after
artifacts are synchronized locally.
