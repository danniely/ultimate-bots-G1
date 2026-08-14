# deployment/

Generated artifacts for MuJoCo Sim2Sim validation. Populated by
`scripts/export_onnx.sh` (run on a machine with Isaac Lab installed) --
see `docs/mujoco_validation.md` for the full workflow. Not hand-edited
except for `observation_config.yaml`, which may need correction after
verifying it against `model_config.yaml` (see the "Observation config
caveat" section of that doc).

Expected contents once export has run:

```text
deployment/
├── model_step_<N>_encoder.onnx
├── model_step_<N>_decoder.onnx
├── model_config.yaml
├── observation_config.yaml
└── motion/<motion_name>/
```
