# Unitree G1 Capoeira Kick — SONIC Capoeira V8

This repository contains the reproducible experiment files for fine-tuning
NVIDIA SONIC to perform a short, high-impact capoeira kick on Unitree G1.

The NVIDIA source checkout is kept separately at
`/workspace/GR00T-WholeBodyControl`. This repository stores only our motion
data, configuration, scripts, metrics, selected checkpoints, ONNX exports, and
before/after videos.

## Project overview

I taught Unitree G1 a capoeira kick using a real human motion reference. I
initially explored AI-generated video, but it often ignored physical constraints
and did not provide the motion quality needed for training.

Having separate training and validation environments made cross-validation
especially challenging. The policy was trained in NVIDIA Isaac Sim, while
differences in physics, contacts, friction, and actuator response made the same
motion less reliable in MuJoCo. I improved the result by dividing the motion
into launch, kick, landing, and recovery phases and applying phase-specific
rewards and penalties. Repeated training and Isaac Sim–MuJoCo validation
gradually produced a more accurate and stable motion.

### Submission links

- **Before and after simulation:** [G1 Robot.mp4](videos/G1%20Robot.mp4)
- **ONNX policy:** [SONIC Capoeira V8 on Hugging Face](https://huggingface.co/hyunho7979/sonic-capoeira-v8)
- **Motion dataset:** [SONIC Capoeira V8 dataset on Hugging Face](https://huggingface.co/datasets/hyunho7979/sonic-capoeira-v8)
- **Code and training configuration:** this repository

### Validation snapshot

- Isaac Sim evaluation: **112/112 completed rollouts** across the recorded V8
  screening matrix.
- ONNX parity: encoder max absolute difference `0`; decoder max absolute
  difference `1.67e-6`.
- MuJoCo cross-validation: **10/10 full-motion rollouts**, with **3/10** meeting
  the stricter final-stabilization gate.

> **Safety note:** This is a simulation research result. The policy has not
> been approved for deployment on a physical robot.

## 학습 과정 기록: v1 → v2 → v3

이 프로젝트의 버전 번호는 같은 모델을 단순히 더 오래 학습한 순서가
아니다. 눈으로 확인한 실패 원인에 맞춰 **보상, 종료 조건, 학습 데이터의
길이**를 단계적으로 바꾼 실험 버전이다.

```text
NVIDIA SONIC release checkpoint
└── v1: 전체 자세 추적 기준선
    └── v2 Stage 1: 하이라이트 우선 / 완화된 학습 조건  ← v2 최종 선택
        ├── v2 Stage 2: 강건성 우선 / 엄격한 조건 복원   ← 비교용 분기
        └── v3: 하이라이트 보존 + 착지 후 2초 균형 회복 ← v3 당시 선택
```

> `fresh optimizer`는 가중치를 처음부터 다시 학습했다는 뜻이 아니다.
> 이전 체크포인트의 policy/critic 가중치는 불러오고, optimizer의 모멘텀과
> 학습률 상태만 새로 시작했다.

### 한눈에 보는 차이

| 버전 | 시작 가중치 | 모션 길이 | 학습 | 핵심 변경 | 대표 결과 |
|---|---|---:|---:|---|---|
| v1 | `sonic_release/last.pt` | 81프레임, 1.62초 | 2,000회, LR `2e-5` | 기본 SONIC 전체 자세 추적 보상으로 사용자 모션에 최초 파인튜닝 | 전반적인 동작은 따라갔지만 공중 발차기와 착지 안정성이 부족함 |
| v2 Stage 1 | v1 step 2000 | 81프레임 | 1,000회, LR `5e-6` | 구간별 보상 추가, 하이라이트를 경험하도록 일부 종료 조건·물리 랜덤화 제거 | 69/81프레임 도달. 공중 회전과 오른발 킥의 표현력이 가장 좋았음 |
| v2 Stage 2 | v2 Stage 1 step 1000 | 81프레임 | 1,000회, LR `5e-6` | Stage 1의 보상은 유지하고 엄격한 종료 조건·물리 랜덤화 복원 | 오차는 줄었지만 50/81프레임에서 종료되어 하이라이트 전에 실패 |
| v3 | v2 Stage 1 step 1000 | 181프레임, 3.62초 | 750회, LR `2e-6` | 100프레임(2초) 회복 목표와 착지·균형 보상 추가 | step 600이 181/181프레임 완료. 양발 접촉률 98%, 정상 물리 평가 성공률 100% |

위 결과는 버전마다 종료 조건이 다르므로 보상값만 직접 비교하면 안 된다.
특히 v2 Stage 1은 표현력 학습을 위해 종료 조건을 완화한 실험이고, v2
Stage 2는 더 엄격한 조건에서의 비교 실험이다.

### v1 — 전체 모션을 동일하게 추적한 기준선

**목표:** 커스텀 `s_batido` 모션을 SONIC에서 처음 재현한다.

- NVIDIA가 공개한 `sonic_release/last.pt`에서 시작했다.
- 512개 병렬 환경에서 2,000 iteration을 학습했다.
- 81개 모든 프레임에 기본 SONIC 보상을 동일하게 적용했다. 특정 발차기
  구간이나 착지 구간을 별도로 강조하지 않았다.
- 최종 학습 스냅샷은 mean reward `2.8666`, mean episode length `44.17`,
  body position error `0.1105`, joint position error `0.1823`이었다.
- 전반적인 모션 트래킹은 가능했지만, 중요한 공중 하이라이트에서 필요한
  추진력·오른쪽 다리 신전과 착지 후 균형은 충분히 학습되지 않았다.

체크포인트:
`checkpoints/v1/s_batido_sonic_v1_step_002000.pt`

### v2 — 공중 발차기 하이라이트를 구간별로 강조

v1의 문제는 모든 프레임이 사실상 같은 중요도로 취급되어, 대회에서 중요한
공중 발차기를 특별히 잘할 이유가 부족하다는 것이었다. v2는 기존 SONIC
보상을 유지하면서 모션을 네 구간으로 나누고 추가 보상을 적용했다.

| 프레임 | 구간 | 추가로 강조한 행동 |
|---:|---|---|
| 0–24 | 지지 | 최소 한 손목과 한 발목의 유효한 지면 접촉 |
| 25–40 | 도약 | 지지 접촉 유지와 기준 모션의 골반 수직 속도 추적 |
| 41–69 | 공중 하이라이트 | 오른쪽 골반·무릎·발목의 위치, 방향, 관절각과 골반 방향 |
| 70–80 | 착지 | 골반 위치 추적 |

#### v2 Stage 1 — Highlight priority, relaxed training conditions

- v1의 policy/critic을 불러오고 optimizer는 새로 시작했다.
- 학습률을 `2e-5`에서 `5e-6`으로 낮춰 기존 동작이 급격히 무너지는 것을
  줄였다.
- 손·발 위치 기반 조기 종료를 제거하고 재질, 관절 초기값, 무게중심,
  질량 랜덤화를 잠시 껐다. 정책이 중간에 끊기지 않고 도약과 공중 구간까지
  경험하도록 만든 curriculum 단계다.
- 기록된 평가에서 69/81프레임까지 도달했고, v2 후보 중 공중 발차기의
  표현력이 가장 좋아 최종 하이라이트 체크포인트로 선택했다.

체크포인트:
`checkpoints/v2/stage1/s_batido_v2_stage1_step_001000.pt`

#### v2 Stage 2 — Robustness priority, strict physics conditions

- Stage 1 step 1000에서 이어서 같은 구간별 보상으로 학습했다.
- 기본 SONIC의 손·발 위치 종료 조건과 물리 랜덤화를 다시 켜 다양한 물성에서도
  버티는 강건성을 목표로 했다.
- 활성 구간의 body/joint position error는 Stage 1보다 작았지만, 엄격한
  end-effector 종료 조건 때문에 50/81프레임에서 끝났다. 공중 하이라이트를
  온전히 보여주지 못했으므로 대회용 최종본과 v3의 시작점으로 선택하지 않았다.

체크포인트:
`checkpoints/v2/stage2/s_batido_v2_stage2_step_001000.pt`

세부 수치와 영상 설명은 `exports/v2/RESULTS.md`와 `videos/v2/README.md`에
있다.

### v3 — 기존 하이라이트를 유지하면서 착지 후 일어서기

**목표:** v2 Stage 1의 공중 발차기를 보존하면서, 영상이 착지 직후 끝나지
않고 로봇이 일어나 균형을 잡는 모습까지 완성한다.

- 표현력이 더 좋았던 **v2 Stage 1 step 1000**에서 분기했다. v2 Stage 2
  위에 이어 학습하지 않았다.
- 원본 81프레임은 그대로 유지하고 100프레임을 추가했다. 앞 50프레임은
  착지 자세에서 안정적인 직립 자세로 부드럽게 이동하고, 뒤 50프레임은 그
  자세를 유지한다. 전체 길이는 181프레임, 50 FPS에서 3.62초다.
- v2 보상에 다음 회복 전용 보상을 더했다.
  - 양발이 동시에 바닥을 지지하는가
  - 골반이 기울지 않고 직립하는가
  - 착지 후 골반의 선속도·각속도가 줄어드는가
  - 골반의 수평 투영점이 양발 중앙에 머무는가
- 학습률을 `2e-6`으로 더 낮추고 750 iteration을 학습해 기존 공중
  하이라이트의 catastrophic forgetting을 줄였다.
- 50 iteration 간격 후보를 모두 평가해 step 600을 선택했다. step 200은
  70프레임에서 종료됐지만 step 250–750은 전체 동작을 완료했고, step 600이
  하이라이트 보존과 회복 안정성 사이에서 가장 좋은 균형을 보였다.
- 최종 정상 물리 평가에서 181/181프레임, success `100%`, 회복 구간 양발
  접촉률 `98%`, 평균 골반 속도 `0.0630 m/s`, 골반-양발 중심 거리
  `0.0153 m`를 기록했다.

v3 당시 선택 체크포인트:
`checkpoints/v3/s_batido_v3_recovery_step_000600.pt`

최종 영상:
`videos/v3/s_batido_v3_landing_recovery_full_isaac.mp4`

선택 근거와 전체 지표는
`exports/v3/final/metrics/selection_summary.md`에 기록되어 있다.

## RunPod layout

```text
/workspace/
├── GR00T-WholeBodyControl/  # NVIDIA upstream source
└── ultimate-bots-G1/        # this repository
/opt/
└── env_isaaclab/            # regenerable Python 3.11 environment
```

## Setup

```bash
bash /workspace/ultimate-bots-G1/scripts/setup_runpod.sh
```

Large final artifacts are tracked with Git LFS. Intermediate checkpoints stay
on the RunPod volume and are not committed.

The Python environment lives on the faster container disk because Isaac Sim
contains many small files. Re-run the setup script after recreating a Pod.

### Nebius GPU VM

On a Nebius Ubuntu VM created from an NVIDIA GPU image, clone this repository
to `/srv/sonic/ultimate-bots-G1`, then run:

```bash
bash /srv/sonic/ultimate-bots-G1/scripts/setup_nebius.sh
```

The Nebius installer keeps the repository, NVIDIA checkout, and Python
environment together on the VM boot disk under `/srv/sonic`. Stopping the VM
stops compute charges while the disk remains billable and persistent.

## Frame-level evaluation diagnostics

Use `scripts/run_sonic_eval_debug.sh` for evaluation runs that need debugging.
It saves the rendered video and synchronized 50 Hz telemetry under one run ID
in `exports/evaluations/<RUN_ID>/`.

The canonical `frames/*.npz` contains actual/reference joint positions and
velocities, errors, controller targets, actions, applied/computed torques,
tracked-body and pelvis state, contact forces, and every termination flag. A
flattened `frames/*.csv` is written simultaneously for quick inspection.
`frames/metadata.json` records joint/body ordering and units.

```bash
RUN_ID=after_reward_v2 \
CHECKPOINT=/workspace/ultimate-bots-G1/checkpoints/final/s_batido_sonic_step_002000.pt \
bash /workspace/ultimate-bots-G1/scripts/run_sonic_eval_debug.sh
```

## s_batido v2 curriculum

The original 2,000-iteration result is frozen under `checkpoints/v1/`. Version
2 starts from those policy and critic weights with a fresh optimizer and lower
learning rate; it does not restart from the released SONIC checkpoint.

The v2 reward plan is recorded in `experiments/v2/reward_plan.yaml`. Stage 1
temporarily removes endpoint terminations and startup physics randomization so
the policy can experience the takeoff and airborne highlight. Stage 2 restores
the normal termination and randomization rules for robustness.

```bash
bash /workspace/ultimate-bots-G1/scripts/start_sonic_v2_stage1.sh

CHECKPOINT=/path/to/stage1/model_step_001000.pt \
bash /workspace/ultimate-bots-G1/scripts/start_sonic_v2_stage2.sh
```

## v3 landing recovery

v3 starts from the selected v2 Stage 1 highlight checkpoint. It keeps the
original 81-frame move and appends a 100-frame recovery target: one second to
return to a stable upright stance and one second to hold it. Recovery-specific
rewards cover two-foot contact, upright pelvis, low base velocity, and keeping
the pelvis projection centered over the feet.

On Nebius, after converting the generated CSV bundle to
`data/motion_lib/s_batido_v3_recovery.pkl`, run a smoke test first:

```bash
NUM_ENVS=32 ITERATIONS=2 SAVE_INTERVAL=1 \
EXPERIMENT_NAME=s_batido_v3_smoke \
OUTPUT_DIR=/srv/sonic/ultimate-bots-G1/exports/v3/smoke \
bash /srv/sonic/ultimate-bots-G1/scripts/start_sonic_v3.sh
```

The full run defaults to 512 environments and 750 iterations with a lower
learning rate than v2 to reduce catastrophic forgetting of the airborne
highlight.
