#!/usr/bin/env python3
"""Run the official SONIC MuJoCo loop headlessly and release its safety band.

This is a deterministic test harness for automated sim2sim regression runs.  It
does not change robot dynamics or controller gains; it only replaces the manual
viewer key ``9`` with a timed release of the simulator's elastic safety band.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import threading
import time

from gear_sonic.data.robot_model.instantiation.g1 import instantiate_g1_robot_model
from gear_sonic.scripts.run_sim_loop import SimWrapper
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
from gear_sonic.utils.mujoco_sim.simulator_factory import SimulatorFactory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-after", type=float, default=8.0)
    parser.add_argument("--release-file", type=Path)
    args = parser.parse_args()

    config = SimLoopConfig(enable_onscreen=False, enable_offscreen=False, verbose=False)
    wbc_config = config.load_wbc_yaml()
    wbc_config["ENV_NAME"] = config.env_name

    wrapper = SimWrapper(
        robot_model=instantiate_g1_robot_model(),
        env_name=config.env_name,
        config=wbc_config,
        onscreen=False,
        offscreen=False,
        enable_image_publish=False,
    )
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
    SimulatorFactory.start_simulator(wrapper.sim, as_thread=False)


if __name__ == "__main__":
    main()
