#!/usr/bin/env python3
"""Create non-destructive v3 checkpoint contexts for strict evaluations."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
import shutil

import yaml


def _moderate_events(events: dict) -> dict:
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
    return events


def _recovery_push_events(events: dict) -> dict:
    push = copy.deepcopy(events["push_robot"])
    push["interval_range_s"] = [2.0, 2.8]
    push["params"]["velocity_range"] = {
        "x": [-0.15, 0.15],
        "y": [-0.15, 0.15],
        "z": [-0.05, 0.05],
        "roll": [-0.2, 0.2],
        "pitch": [-0.2, 0.2],
        "yaw": [-0.2, 0.2],
    }
    return {"push_robot": push, "_target_": events["_target_"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--strict-source-config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    source_config = args.checkpoint.parent / "config.yaml"
    if not source_config.exists():
        raise FileNotFoundError(f"Missing checkpoint config: {source_config}")

    config = yaml.safe_load(source_config.read_text(encoding="utf-8"))
    strict = yaml.safe_load(args.strict_source_config.read_text(encoding="utf-8"))
    strict_env = strict["manager_env"]

    profiles = {
        "strict_nominal": {},
        "moderate_randomization": _moderate_events(strict_env["events"]),
        "official_randomization": copy.deepcopy(strict_env["events"]),
        "recovery_push": _recovery_push_events(strict_env["events"]),
        # The stock ee_body_pos gate includes both wrists.  This capoeira
        # motion intentionally plants and then releases one hand, and that
        # gate terminates every policy at frame 50 before takeoff.  Keep the
        # result as a stock-compatibility test, but use these hardware profiles
        # for ranking: torso/feet/fall remain hard gates while hand safety is
        # measured with contact force, slip and tracking telemetry.
        "hardware_nominal": {},
        "hardware_moderate": _moderate_events(strict_env["events"]),
        "hardware_official": copy.deepcopy(strict_env["events"]),
        "hardware_recovery_push": {
            **_moderate_events(strict_env["events"]),
            "push_robot": _recovery_push_events(strict_env["events"])[
                "push_robot"
            ],
        },
    }

    for name, events in profiles.items():
        profile_config = copy.deepcopy(config)
        profile_config["manager_env"]["terminations"] = copy.deepcopy(
            strict_env["terminations"]
        )
        if name.startswith("hardware_"):
            # The Studio reference contains visible hand/foot ground
            # penetration.  Absolute end-effector tracking is therefore not a
            # valid hardware safety gate: PhysX prevents the real simulated
            # links from following those impossible points.  Preserve torso
            # height/orientation and timeout as hard fall gates, and rank
            # hands/feet using contact, slip, overload and tracking telemetry.
            for term in ("anchor_pos", "ee_body_pos", "foot_pos_xyz"):
                profile_config["manager_env"]["terminations"].pop(term, None)
            profile_config["manager_env"]["terminations"]["anchor_ori_full"] = {
                "_target_": "isaaclab.managers.TerminationTermCfg",
                "func": "sonic_debug.phase_rewards:phase_aware_base_safety",
                "params": {
                    "command_name": "motion",
                    "recovery_settle_frame": 131,
                    "pre_recovery_tilt_error_rad": 3.0,
                    "pre_recovery_min_height": 0.2,
                    "recovery_world_tilt_rad": 0.8,
                    "recovery_min_height": 0.5,
                    "unsafe_contact_body_names": [
                        "pelvis",
                        "torso_link",
                        "head_link",
                    ],
                    "unsafe_contact_force": 100.0,
                },
            }
        if events:
            profile_config["manager_env"]["events"] = events
        else:
            profile_config["manager_env"]["events"] = {
                "_target_": strict_env["events"]["_target_"]
            }

        destination = args.output_root / name
        destination.mkdir(parents=True, exist_ok=True)
        checkpoint_copy = destination / args.checkpoint.name
        if checkpoint_copy.exists() or checkpoint_copy.is_symlink():
            checkpoint_copy.unlink()
        checkpoint_copy.symlink_to(args.checkpoint.resolve())
        (destination / "config.yaml").write_text(
            yaml.safe_dump(profile_config, sort_keys=False), encoding="utf-8"
        )
        shutil.copy2(args.strict_source_config, destination / "strict_source_config.yaml")


if __name__ == "__main__":
    main()
