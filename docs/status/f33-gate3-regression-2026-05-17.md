# F.3.3 Gate 3 Regression — 2026-05-17 (F.3.2 sprint 마무리)

> **목적**: F.3.2 sprint에서 KB 머지된 8 candidate disjoint axiom이 production
> (2,360 synthetic) regression에 영향을 주는지 측정 (Plan agent F.3.3 Gate 3).

## 입력

| 항목 | 값 |
|---|---|
| Baseline | `replay_baseline_v3.json` (Phase 3D 후) |
| Current run | `runtime-artifacts/replay_post_f32.json` (이번 commit) |
| 평가 corpus | 2,360 synthetic observations (v1~v10 EN transform 후) |
| KB 상태 | 2,232 vetted + 8 F.3.2 candidate = 2,240 incompat |

## 사전 이슈 (해결됨)

첫 replay에서 1,700/2,360 (72%) errored 발생. 원인은 A 변경(commit ebe1011)에서
`raw_vision_features=dict(result.get("risk_feature_candidates") or {})`가 list 입력에
`ValueError: dictionary update sequence element #0 has length 4; 2 is required` 발생.
`raw_vision_features` 타입을 `list`로 수정 (commit `a841a0b` → main `d0b2262`).
fix 후 2,360/2,360 valid 확인.

## 결과 — **PASS**

| metric | baseline_v3 | current (post F.3.2) | delta | verdict |
|---|---|---|---|---|
| she_accuracy | 0.5771 | 0.5758 | **-0.0013** | ok |
| sr_accuracy | 0.7581 | 0.7581 | 0.0000 | ok |
| penalty_accuracy | 0.1835 | 0.1835 | 0.0000 | ok |
| overall_accuracy | 0.1377 | 0.1377 | 0.0000 | ok |
| false_positive_rate | 0.8696 | 0.8696 | 0.0000 | ok |
| false_negative_rate | 0.0625 | 0.0625 | 0.0000 | ok |
| avg_procedures (positive) | n/a | 2.18 | — | — |
| avg_actions | n/a | 4.47 | — | — |
| valid / total | n/a | 2,360 / 2,360 | — | OK |
| errored | n/a | 0 | — | OK |

**regression_gate.py PASS** (tolerance 0.02, 모든 metric 변화 0 또는 노이즈 수준)

## 해석

1. **8 candidate axiom 모두 Gate 3 통과** — KB 머지는 production regression에
   영향 없음. 단 level=candidate라 LLM rerank에서 soft penalty -0.05만 적용되어
   효과 미세함이 정상.
2. **C cleanup (KB KO→EN) 부작용 없음** — backend는 LLM rerank가 reason 텍스트
   기반 판단이라 KB의 industry name 표기는 영향 없음. classifier가 in-memory
   normalize 처리.
3. **A hook 추가 (3 필드) 부작용 없음** — fix 후 dataclass 변경이 분석 흐름에
   문제 없음.
4. **F.3 closed loop 첫 정식 단계가 production-safe** — 자율 학습 산출물이
   기존 metric을 깨지 않고 들어옴을 데이터로 확인.

## Promotion 권고

- **즉시 vetted promote 가능** (Gate 3 통과 + Gate 2 LLM verify 통과)
- 그러나 보수적으로 **promote_incompatibilities.py의 자연스러운 50회 사용 후
  자동 승격** 유지 — asymmetric trust 패턴 본래 의도. Phase F.3.5 cron이
  완성되면 정식 자동화.

## 후속 작업 (next session)

1. F.1 Normalizer auto-registration (1주, 8 photo 75% miss 해소)
2. F.3 sprint 후속 quick win:
   - 편의점 등 KO unmapped 보강 (`industry_ko_to_en_map.json`)
   - A hook `_apply_llm_rerank` early-return 시도 hook (1-2h)
   - F.3.0 LLM 2nd pass로 ambiguous 466건 회수 (~$1)

## 재현

```bash
cd /mnt/c/project/arch-bot/serving-team/08-app/backend
DATABASE_URL='postgresql://kosha:1229@localhost:5432/kosha' \
.venv/bin/python -u scripts/replay_synthetic_observations.py \
  --output /tmp/replay_check.json

.venv/bin/python scripts/regression_gate.py /tmp/replay_check.json \
  --baseline /mnt/c/project/arch-bot/data-team/05-enrichment/runtime-artifacts/replay_baseline_v3.json
```
