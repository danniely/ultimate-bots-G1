# V7 real-robot stability plan

V7 separates two failure modes that were mixed together in V6.

1. Run the official C++/MuJoCo stack ten times without ever issuing a motion
   command. Record which standing-settle gate fails: upright, joint velocity,
   or base angular velocity.
2. Do not start GPU fine-tuning until the standing baseline is repeatable.
3. Time-stretch the abrupt section of the V6 reference around frames 147–170.
   Preserve the important capoeira poses while limiting target joint speed and
   recomputing all velocities.
4. Fine-tune from the selected V6 step-300 checkpoint with torque reserve,
   action-rate, joint-acceleration, landing and recovery rewards.
5. Select checkpoints by Isaac completion first, then official MuJoCo start,
   full-motion and final-stability rates. Never bypass a safety gate.

Completion requires at least 10/10 standing-settle trials, Isaac completion
under nominal and randomized profiles, and repeatable MuJoCo closed-loop
completion with a stable final hold.
