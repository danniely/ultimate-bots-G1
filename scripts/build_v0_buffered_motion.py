#!/usr/bin/env python3
"""Append a two-second diagnostic tail to the original SONIC motion library."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--buffer-seconds", type=float, default=2.0)
    parser.add_argument("--source-frames", type=int)
    args = parser.parse_args()

    library = joblib.load(args.source)
    if len(library) != 1:
        raise ValueError(f"Expected one motion, got keys={list(library)}")

    source_key, source = next(iter(library.items()))
    fps = float(source["fps"])
    extra_frames = int(round(args.buffer_seconds * fps))
    if extra_frames <= 0:
        raise ValueError("buffer must contain at least one frame")

    lengths = {
        len(value)
        for value in source.values()
        if isinstance(value, np.ndarray) and value.ndim > 0
    }
    if len(lengths) != 1:
        raise ValueError(f"Inconsistent source array lengths: {lengths}")
    source_frames = lengths.pop()
    if args.source_frames is not None:
        if not 0 < args.source_frames <= source_frames:
            raise ValueError(
                f"source-frames must be within 1..{source_frames}, got {args.source_frames}"
            )
        source_frames = args.source_frames

    output: dict[str, object] = {}
    for name, value in source.items():
        if isinstance(value, np.ndarray) and value.ndim > 0:
            original = value[:source_frames]
            tail = np.repeat(original[-1:], extra_frames, axis=0)
            output[name] = np.concatenate((original, tail), axis=0)
        else:
            output[name] = value

    destination_key = f"{source_key}_v0_buffered"
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({destination_key: output}, args.destination, compress=3)
    print(
        f"wrote={args.destination} source_frames={source_frames} "
        f"buffer_frames={extra_frames} total_frames={source_frames + extra_frames} "
        f"fps={fps:g}"
    )


if __name__ == "__main__":
    main()
