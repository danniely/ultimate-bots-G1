#!/usr/bin/env python3
"""Create isolated V8 Isaac evaluation contexts for one checkpoint."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import yaml


def moderate_events(events: dict) -> dict:
    events = copy.deepcopy(events)
    material = events["physics_material"]["params"]
    material["static_friction_range"] = [0.6, 1.2]
    material["dynamic_friction_range"] = [0.5, 1.0]
    material["restitution_range"] = [0.0, 0.15]
    events["add_joint_default_pos"]["params"]["pos_distribution_params"] = [
        -0.005,
        0.005,
    ]
    events["base_com"]["params"]["com_range"] = {
        "x": [-0.015, 0.015],
        "y": [-0.02, 0.02],
        "z": [-0.025, 0.025],
    }
    events["randomize_rigid_body_mass"]["params"]["mass_distribution_params"] = [
        0.9,
        1.15,
    ]
    if events.get("actuator_gains"):
        gains = events["actuator_gains"]["params"]
        gains["stiffness_distribution_params"] = [0.95, 1.05]
        gains["damping_distribution_params"] = [0.9, 1.1]
    return events


def recovery_push_events(events: dict) -> dict:
    events = moderate_events(events)
    events["push_robot"]["interval_range_s"] = [5.8, 7.8]
    events["push_robot"]["params"]["velocity_range"] = {
        "x": [-0.15, 0.15],
        "y": [-0.15, 0.15],
        "z": [-0.04, 0.04],
        "roll": [-0.2, 0.2],
        "pitch": [-0.2, 0.2],
        "yaw": [-0.2, 0.2],
    }
    return events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    config_path = args.checkpoint.parent / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    training_events = config["manager_env"]["events"]
    profiles = {
        "hardware_nominal": {"_target_": training_events["_target_"]},
        "hardware_moderate": moderate_events(training_events),
        "hardware_official": copy.deepcopy(training_events),
        "hardware_recovery_push": recovery_push_events(training_events),
    }

    for name, events in profiles.items():
        profile = copy.deepcopy(config)
        profile["manager_env"]["events"] = events
        destination = args.output_root / name
        destination.mkdir(parents=True, exist_ok=True)
        checkpoint_link = destination / args.checkpoint.name
        if checkpoint_link.exists() or checkpoint_link.is_symlink():
            checkpoint_link.unlink()
        checkpoint_link.symlink_to(args.checkpoint.resolve())
        (destination / "config.yaml").write_text(
            yaml.safe_dump(profile, sort_keys=False), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
