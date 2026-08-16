#!/usr/bin/env python3
"""Run the official MuJoCo loop headlessly while recording an MP4."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import threading
import time

import mujoco

from gear_sonic.data.robot_model.instantiation.g1 import instantiate_g1_robot_model
from gear_sonic.scripts.run_sim_loop import SimWrapper
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-after", type=float, default=60.0)
    parser.add_argument("--release-file", type=Path)
    parser.add_argument("--stop-file", type=Path)
    parser.add_argument("--max-seconds", type=float, default=30.0)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()

    config = SimLoopConfig(enable_onscreen=False, enable_offscreen=True, verbose=False)
    wbc_config = config.load_wbc_yaml()
    wbc_config["ENV_NAME"] = config.env_name
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:] = (0.0, 0.0, 0.75)
    camera.distance = 3.2
    camera.azimuth = 135.0
    camera.elevation = -14.0
    camera_configs = {
        "record": {
            "height": args.height,
            "width": args.width,
            "params": camera,
        }
    }
    wrapper = SimWrapper(
        robot_model=instantiate_g1_robot_model(),
        env_name=config.env_name,
        config=wbc_config,
        onscreen=False,
        offscreen=True,
        enable_image_publish=False,
        camera_configs=camera_configs,
    )
    # The current official simulator factory does not forward camera_configs.
    # Install the recorder camera after construction without changing dynamics.
    wrapper.sim.sim_env.camera_configs = camera_configs
    wrapper.sim.sim_env.mj_model.vis.global_.offwidth = max(
        wrapper.sim.sim_env.mj_model.vis.global_.offwidth, args.width
    )
    wrapper.sim.sim_env.mj_model.vis.global_.offheight = max(
        wrapper.sim.sim_env.mj_model.vis.global_.offheight, args.height
    )
    wrapper.sim.sim_env.init_renderers()

    def release_band() -> None:
        deadline = time.monotonic() + max(0.0, args.release_after)
        if args.release_file is not None:
            while time.monotonic() < deadline and not args.release_file.exists():
                time.sleep(0.02)
        else:
            time.sleep(max(0.0, args.release_after))
        band = wrapper.sim.sim_env.elastic_band
        if band is not None:
            band.enable = False
            print("AUTO_RELEASE elastic_band=false", flush=True)

    threading.Thread(target=release_band, daemon=True).start()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    writer = subprocess.Popen(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{args.width}x{args.height}", "-r", str(args.fps),
            "-i", "-", "-an", "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p", str(args.output),
        ],
        stdin=subprocess.PIPE,
    )
    sim = wrapper.sim
    render_interval = max(1, round((1.0 / args.fps) / sim.sim_dt))
    deadline = time.monotonic() + args.max_seconds
    sim_count = 0
    try:
        while time.monotonic() < deadline and not (
            args.stop_file is not None and args.stop_file.exists()
        ):
            step_start = time.monotonic()
            sim.sim_env.sim_step()
            if sim_count % render_interval == 0:
                frame = sim.sim_env.update_render_caches()["record_image"]
                assert writer.stdin is not None
                writer.stdin.write(frame.tobytes())
            elapsed = time.monotonic() - step_start
            if elapsed < sim.sim_dt:
                time.sleep(sim.sim_dt - elapsed)
            sim_count += 1
    finally:
        if writer.stdin is not None:
            writer.stdin.close()
        writer.wait(timeout=30)
        sim.close()
    print(f"CAPTURE_DONE frames={sim_count // render_interval} output={args.output}", flush=True)


if __name__ == "__main__":
    main()
