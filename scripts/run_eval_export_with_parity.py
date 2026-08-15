#!/usr/bin/env python3
"""Run SONIC's exporter and record PyTorch-versus-ONNX numerical parity."""

from __future__ import annotations

import json
import os
import runpy
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
import torch


REPORT_PATH = Path(os.environ.get("SONIC_PARITY_REPORT", "/tmp/sonic_onnx_parity.json"))
ORIGINAL_EXPORT = torch.onnx.export
RESULTS: list[dict[str, Any]] = []


def tensors(value: Any) -> list[torch.Tensor]:
    if isinstance(value, torch.Tensor):
        return [value]
    if isinstance(value, dict):
        result: list[torch.Tensor] = []
        for nested in value.values():
            result.extend(tensors(nested))
        return result
    if isinstance(value, (list, tuple)):
        result = []
        for nested in value:
            result.extend(tensors(nested))
        return result
    return []


def first_tensor(value: Any) -> torch.Tensor:
    found = tensors(value)
    if not found:
        raise TypeError("Model produced no tensor output")
    return found[0]


def parity_export(model: torch.nn.Module, args: Any, destination: Any, *pos: Any, **kwargs: Any) -> Any:
    with torch.no_grad():
        pytorch_output = model(**args) if isinstance(args, dict) else model(*args)
    result = ORIGINAL_EXPORT(model, args, destination, *pos, **kwargs)

    input_values = tensors(args)
    session = ort.InferenceSession(str(destination), providers=["CPUExecutionProvider"])
    if len(input_values) != len(session.get_inputs()):
        raise RuntimeError(
            f"Cannot compare {destination}: {len(input_values)} PyTorch leaves vs "
            f"{len(session.get_inputs())} ONNX inputs"
        )
    feed = {
        spec.name: value.detach().cpu().numpy()
        for spec, value in zip(session.get_inputs(), input_values, strict=True)
    }
    onnx_output = session.run(None, feed)[0]
    pytorch_array = first_tensor(pytorch_output).detach().cpu().numpy()
    difference = np.abs(pytorch_array - onnx_output)
    RESULTS.append(
        {
            "model": str(destination),
            "shape": list(onnx_output.shape),
            "max_abs_diff": float(difference.max()),
            "mean_abs_diff": float(difference.mean()),
            "all_finite": bool(np.isfinite(onnx_output).all()),
        }
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(RESULTS, indent=2) + "\n")
    return result


torch.onnx.export = parity_export
runpy.run_path("gear_sonic/eval_agent_trl.py", run_name="__main__")
