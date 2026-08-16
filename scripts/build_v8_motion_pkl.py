#!/usr/bin/env python3
"""Retarget the compressed SONIC motion library from V7 to V8 timing."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np

from build_v8_landing_motion import (
    LANDING_END,
    LANDING_FACTOR,
    LANDING_START,
    RECOVERY_END,
    RECOVERY_FACTOR,
)


def factor_for(frame: int) -> int:
    if LANDING_START <= frame < LANDING_END:
        return LANDING_FACTOR
    if LANDING_END <= frame < RECOVERY_END:
        return RECOVERY_FACTOR
    return 1


def slerp(left: np.ndarray, right: np.ndarray, amount: float) -> np.ndarray:
    left = left / np.linalg.norm(left)
    right = right / np.linalg.norm(right)
    dot = float(np.dot(left, right))
    if dot < 0.0:
        right, dot = -right, -dot
    if dot > 0.9995:
        value = left + amount * (right - left)
        return value / np.linalg.norm(value)
    theta = np.arccos(np.clip(dot, -1.0, 1.0))
    return (
        np.sin((1.0 - amount) * theta) * left
        + np.sin(amount * theta) * right
    ) / np.sin(theta)


def retime(values: np.ndarray, quaternion: bool = False) -> np.ndarray:
    output: list[np.ndarray] = []
    for frame in range(len(values) - 1):
        factor = factor_for(frame)
        for substep in range(factor):
            amount = substep / factor
            if quaternion:
                value = slerp(values[frame], values[frame + 1], amount)
            else:
                value = values[frame] + amount * (values[frame + 1] - values[frame])
            output.append(value)
    output.append(values[-1].copy())
    return np.asarray(output, dtype=values.dtype)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    library = joblib.load(args.source)
    if list(library) != ["s_batido_v7_targeted_sonic"]:
        raise ValueError(f"Unexpected V7 motion keys: {list(library)}")
    source = library["s_batido_v7_targeted_sonic"]
    output = {
        "root_trans_offset": retime(source["root_trans_offset"]),
        "pose_aa": retime(source["pose_aa"]),
        "dof": retime(source["dof"]),
        "root_rot": retime(source["root_rot"], quaternion=True),
        "smpl_joints": retime(source["smpl_joints"]),
        "fps": source["fps"],
    }
    lengths = {len(value) for value in output.values() if isinstance(value, np.ndarray)}
    if lengths != {467}:
        raise ValueError(f"Unexpected V8 lengths: {lengths}")
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"s_batido_v8_landing_sonic": output}, args.destination, compress=3)
    print(f"wrote={args.destination} frames=467 fps={output['fps']}")


if __name__ == "__main__":
    main()
