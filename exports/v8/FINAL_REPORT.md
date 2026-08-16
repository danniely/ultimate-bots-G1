# SONIC V8 landing-recovery 결과

## 결론

V8의 최종 보존 후보는 `step 25`이다. Isaac Sim에서는 평가한 112개 고유
checkpoint/profile/seed 조합이 모두 모션을 완주했지만, 공식 C++ 폐루프
MuJoCo에서 `step 25`의 착지 후 최종 안정화는 10회 중 3회만 성공했다.
따라서 이 모델은 **real-robot ready가 아니며 실제 G1에서 실행하면 안 된다.**

## 학습

- 기반 모델: V7 targeted final, fresh optimizer
- 환경/iteration: 384 envs, 300 iterations
- 최종 mean reward: 51.04432
- 최종 mean episode length: 337.77
- time-out completion: 0.7466
- adaptive failure rate mean: 0.0173
- 최종 체크포인트: `model_step_000300.pt`
- 선택 체크포인트: `checkpoints/v8/s_batido_v8_landing_step_000025.pt`

## Isaac Sim 교차검증

- 25-step 체크포인트 12개를 nominal/moderate/official/recovery-push로 검사했다.
- 전체 고유 평가: 112/112 완주, progress rate 1.0.
- step 25는 네 profile 각각 5 seeds에서 20/20 완주했다.
- Isaac 완주만으로 착지 후 폐루프 안정성을 판정할 수 없으므로 MuJoCo 결과를
  최종 안전 기준으로 사용했다.

## 공식 C++/MuJoCo 폐루프

모든 후보가 초기 안전 게이트를 우회하지 않고 10/10 통과했으며, 467 motion
frame도 10/10 실행했다. 차이는 착지 후 최종 서기 안정화에서 발생했다.

| checkpoint | 초기 안정 | 전체 모션 | 최종 안정 | 최종 안정률 |
| --- | ---: | ---: | ---: | ---: |
| step 25 | 10/10 | 10/10 | 3/10 | 30% |
| step 125 | 10/10 | 10/10 | 2/10 | 20% |
| step 275 | 10/10 | 10/10 | 0/10 | 0% |
| step 300 | 10/10 | 10/10 | 1/10 | 10% |

주요 실패는 회복 구간(대략 frame 307-344)에서 시작한다. 착지 뒤 support
polygon 안으로 capture point를 충분히 회수하지 못한 seed에서 관절 속도와
base angular velocity가 증가하고, 일부 관절은 139 Nm torque saturation에
도달한다. 이후 upright가 무너지므로 V8은 성공 seed 영상을 보존하되 실제
로봇 투입을 보류한다.

## ONNX 및 영상

- encoder parity max abs diff: 0.0
- decoder parity max abs diff: 1.6689300537109375e-6
- 모든 parity 출력은 finite이다.
- Isaac: `videos/v8/v8_step025_isaac_full.mp4` (H.264, 1920x1088, 50 fps,
  466 frames, 9.32 s)
- MuJoCo: `videos/v8/v8_step025_mujoco_closed_loop.mp4` (H.264, 960x720,
  30 fps, 617 frames, 20.57 s)

원시 평가 로그와 seed별 telemetry는 `exports/v8` 및
`exports/evaluations/v8_*`에 보존했다. GPU 종속 TensorRT engine은 재현 가능한
ONNX 산출물이 아니므로 Git 보존 대상에서 제외했다.
