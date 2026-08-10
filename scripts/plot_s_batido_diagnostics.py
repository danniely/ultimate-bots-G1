#!/usr/bin/env python3
"""Create training and reference-motion diagnostic plots for s_batido."""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MOTION_DIR = ROOT / "data/source/sonic/s_batido_test_sonic"
LOG_PATH = ROOT / "exports/metrics/train.log"
OUTPUT_DIR = ROOT / "exports/diagnostics"
FPS = 50.0

JOINT_NAMES = [
    "left_hip_pitch",
    "left_hip_roll",
    "left_hip_yaw",
    "left_knee",
    "left_ankle_pitch",
    "left_ankle_roll",
    "right_hip_pitch",
    "right_hip_roll",
    "right_hip_yaw",
    "right_knee",
    "right_ankle_pitch",
    "right_ankle_roll",
    "waist_yaw",
    "waist_roll",
    "waist_pitch",
    "left_shoulder_pitch",
    "left_shoulder_roll",
    "left_shoulder_yaw",
    "left_elbow",
    "left_wrist_roll",
    "left_wrist_pitch",
    "left_wrist_yaw",
    "right_shoulder_pitch",
    "right_shoulder_roll",
    "right_shoulder_yaw",
    "right_elbow",
    "right_wrist_roll",
    "right_wrist_pitch",
    "right_wrist_yaw",
]


def parse_training_log(path: Path) -> pd.DataFrame:
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    text = ansi.sub("", path.read_text(errors="replace"))
    blocks = re.split(r"(?=Learning iteration\s+\d+)", text)
    fields = {
        "reward": r"Mean rewards:\s+([-+0-9.eE]+)",
        "length": r"Mean length:\s+([-+0-9.eE]+)",
        "joint_pos_error": r"error_joint_pos:\s+([-+0-9.eE]+)",
        "body_pos_error": r"error_body_pos:\s+([-+0-9.eE]+)",
        "anchor_pos_error": r"error_anchor_pos:\s+([-+0-9.eE]+)",
        "ee_termination": r"Episode_Termination/ee_body_pos:\s+([-+0-9.eE]+)",
        "foot_termination": r"Episode_Termination/foot_pos_xyz:\s+([-+0-9.eE]+)",
        "timeout": r"Episode_Termination/time_out:\s+([-+0-9.eE]+)",
    }
    rows = []
    for block in blocks:
        match = re.search(r"Learning iteration\s+(\d+)", block)
        if not match:
            continue
        row = {"iteration": int(match.group(1))}
        for name, pattern in fields.items():
            value = re.search(pattern, block)
            row[name] = float(value.group(1)) if value else np.nan
        rows.append(row)
    return pd.DataFrame(rows).drop_duplicates("iteration", keep="last").sort_values("iteration")


def rolling(series: pd.Series, window: int = 50) -> pd.Series:
    return series.rolling(window, min_periods=max(5, window // 5)).median()


def plot_training(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

    axes[0].plot(df.iteration, df.reward, color="#7aa6d8", alpha=0.22, linewidth=0.7)
    axes[0].plot(df.iteration, rolling(df.reward), color="#145da0", linewidth=2, label="50-iteration median")
    axes[0].set_ylabel("Mean reward")
    axes[0].legend(loc="best")

    duration = df.length / FPS
    axes[1].plot(df.iteration, duration, color="#88c999", alpha=0.22, linewidth=0.7)
    axes[1].plot(df.iteration, rolling(duration), color="#247a3b", linewidth=2)
    axes[1].axhline(81 / FPS, color="#222222", linestyle="--", linewidth=1.5, label="Full motion: 1.62 s")
    axes[1].set_ylabel("Mean episode duration (s)")
    axes[1].legend(loc="best")

    for col, label, color in [
        ("ee_termination", "Hand/foot endpoint", "#c73e1d"),
        ("foot_termination", "Foot XYZ", "#f19c79"),
        ("timeout", "Reached end", "#2a9d8f"),
    ]:
        axes[2].plot(df.iteration, rolling(df[col]) * 100, label=label, color=color, linewidth=2)
    axes[2].set_ylabel("Termination share (%)")
    axes[2].set_xlabel("Training iteration")
    axes[2].legend(loc="best")

    for ax in axes:
        ax.grid(alpha=0.25)
    fig.suptitle("s_batido SONIC training diagnostics", fontsize=16)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "training_progress.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_reference_motion() -> None:
    joint_pos = pd.read_csv(MOTION_DIR / "joint_pos.csv")
    joint_vel = pd.read_csv(MOTION_DIR / "joint_vel.csv")
    body_pos = pd.read_csv(MOTION_DIR / "body_pos.csv")
    body_vel = pd.read_csv(MOTION_DIR / "body_lin_vel.csv")
    t = np.arange(len(joint_pos)) / FPS

    fig, axes = plt.subplots(4, 1, figsize=(13, 15), sharex=True)

    axes[0].plot(t, body_pos.iloc[:, 2], color="#145da0", linewidth=2, label="Reference pelvis height")
    ax0b = axes[0].twinx()
    ax0b.plot(t, body_vel.iloc[:, 2], color="#d1495b", linewidth=1.8, label="Reference vertical velocity")
    axes[0].axhline(body_pos.iloc[:, 2].min(), color="#145da0", linestyle=":", alpha=0.7)
    axes[0].set_ylabel("Pelvis height (m)")
    ax0b.set_ylabel("Vertical velocity (m/s)")
    lines = axes[0].get_lines() + ax0b.get_lines()
    axes[0].legend(lines, [line.get_label() for line in lines], loc="best")

    right_indices = [6, 7, 8, 9]
    colors = ["#264653", "#2a9d8f", "#e9c46a", "#e76f51"]
    for idx, color in zip(right_indices, colors):
        axes[1].plot(t, np.degrees(joint_pos.iloc[:, idx]), color=color, linewidth=2, label=JOINT_NAMES[idx])
    axes[1].axhline(0, color="#222222", linestyle="--", linewidth=1, label="Straight knee = 0 deg")
    axes[1].set_ylabel("Reference angle (deg)")
    axes[1].legend(loc="best", ncol=2)

    for idx, color in zip(range(6, 12), plt.cm.tab10.colors[:6]):
        axes[2].plot(t, np.abs(joint_vel.iloc[:, idx]), color=color, linewidth=1.7, label=JOINT_NAMES[idx])
    axes[2].axhline(20, color="#c73e1d", linestyle="--", linewidth=1.3, label="20 rad/s warning guide")
    axes[2].set_ylabel("Absolute joint speed (rad/s)")
    axes[2].legend(loc="upper left", ncol=2, fontsize=9)

    max_speed = np.abs(joint_vel.to_numpy()).max(axis=1)
    max_joint_idx = np.abs(joint_vel.to_numpy()).argmax(axis=1)
    axes[3].plot(t, max_speed, color="#6a4c93", linewidth=2, label="Fastest joint each frame")
    peak_frame = int(np.argmax(max_speed))
    peak_joint = int(max_joint_idx[peak_frame])
    axes[3].scatter(t[peak_frame], max_speed[peak_frame], color="#c73e1d", zorder=3)
    axes[3].annotate(
        f"{JOINT_NAMES[peak_joint]}: {max_speed[peak_frame]:.1f} rad/s",
        (t[peak_frame], max_speed[peak_frame]),
        xytext=(-190, -30),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "#c73e1d"},
    )
    axes[3].set_ylabel("Max |joint speed| (rad/s)")
    axes[3].set_xlabel("Motion time (s)")
    axes[3].legend(loc="best")

    for ax in axes:
        ax.grid(alpha=0.25)
    fig.suptitle("s_batido reference-motion feasibility checks", fontsize=16)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "reference_motion.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_summary(df: pd.DataFrame) -> None:
    q = pd.read_csv(MOTION_DIR / "joint_pos.csv")
    v = pd.read_csv(MOTION_DIR / "joint_vel.csv")
    final = df.iloc[-1]
    lines = [
        "s_batido diagnostics",
        "=====================",
        f"Final iteration: {int(final.iteration)}",
        f"Final mean reward: {final.reward:.5f}",
        f"Final mean episode: {final.length / FPS:.3f} s / {len(q) / FPS:.3f} s",
        f"Final endpoint termination: {final.ee_termination * 100:.2f}%",
        f"Final foot termination: {final.foot_termination * 100:.2f}%",
        f"Reference right hip roll range: {np.degrees(q.iloc[:, 7]).min():.1f} to {np.degrees(q.iloc[:, 7]).max():.1f} deg",
        f"Reference right knee range: {np.degrees(q.iloc[:, 9]).min():.1f} to {np.degrees(q.iloc[:, 9]).max():.1f} deg",
        f"Reference max joint speed: {np.abs(v.to_numpy()).max():.2f} rad/s",
        "Actual-vs-reference joint curves unavailable: the prior evaluation saved video only.",
    ]
    (OUTPUT_DIR / "summary.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    training = parse_training_log(LOG_PATH)
    if training.empty:
        raise RuntimeError(f"No training iterations parsed from {LOG_PATH}")
    plot_training(training)
    plot_reference_motion()
    write_summary(training)
    print(f"Wrote diagnostics to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
