# Part 3 Workplan — Synthetic KO Enum → EN Cleanup

> 언어 통일 Option A 마지막 단계. synthetic_observations_v*.jsonl의 KO enum
> 코드를 EN으로 변환. 본 commit은 prep 도구 + 워크플랜만 포함, 실행은
> 다음 세션.

> **✅ 완료됨 (2026-05-17, commit `5ee9639` Phase 3D)** — synthetic v1~v10 EN enum
> transform 적용 + `replay_baseline_v3.json` 새 baseline 생성. 후속 작업으로
> `commit 2ea800d` C cleanup (KB incompat KO→EN 2,232 entries 100% translated)도
> 완료. 본 문서는 historical reference로 보존.

## 배경

F.1-light / F.2-light에서 발견:
- synthetic_observations v1~v10 (2,360 records)이 enum 값 위치에 한국어 사용
- 영향 axis: accident_types (397 KO), hazardous_agents (797 KO),
  environmental (506 KO), ppe_states (157 KO)
- catalog/aliases/v2 OWL 등 다른 모든 layer는 EN 통일됨 (Part 1, Part 2 완료)
- synthetic만 KO 잔존 → regression baseline의 정합성 깨짐

## 도구 (이 commit에 포함)

### `data-team/05-enrichment/llm-scripts/mine_synthetic_ko_codes.py`
- 모든 synthetic v*.jsonl 스캔 → axis별 unique KO codes + frequency
- 자동 EN 후보 추출 chain:
  1. catalog label exact match (예: "추락" → FALL via catalog label)
  2. alias dict exact match
  3. f2_light_catalog_proposals.json ACCEPT/RELOCATE의 canonical_label_en
- 출력: `runtime-artifacts/synthetic_ko_codes_for_review.json`
  (각 entry에 auto_en, auto_source, freq 표시)

### `data-team/05-enrichment/llm-scripts/transform_synthetic_to_en.py`
- 최종 mapping JSON 기반 v*.jsonl 일괄 변환
- 입력: `runtime-artifacts/synthetic_ko_to_en_final.json` (사람 검토 후 완성)
- KO → EN 변환, drop_list 제거, audit 보고
- dry-run / apply 모드, 자동 backup

## 다음 세션 실행 흐름

### Step 1: mine (5분, 0 LLM call)
```bash
cd /mnt/c/project/arch-bot/.claude/worktrees/{branch}
serving-team/08-app/backend/.venv/bin/python \
  data-team/05-enrichment/llm-scripts/mine_synthetic_ko_codes.py
```
출력 확인: `synthetic_ko_codes_for_review.json` (axis별 auto/need-llm 분포)

### Step 2: LLM batch fill (1-2시간, ~$3-5)
`auto_en`이 None인 항목들 (~수백 건)에 대해 LLM 큐레이터 호출.
F.2-light 패턴 재사용 (`extend_catalog_light.py` 참고).
- 각 항목에 대해 LLM 결정:
  - 기존 catalog 코드로 매핑 가능 → 그 코드 (예: 감전 → ELECTRIC_SHOCK)
  - 새 catalog 코드 필요 → en_canonical 제안 (Part 4: catalog 추가 후보)
  - DROP (모호하거나 enum 부적합, 예: "없음", "기타") → drop_list

### Step 3: 사람 검토 + 최종 mapping 작성
LLM 결과 + 자동 매핑 통합 → `runtime-artifacts/synthetic_ko_to_en_final.json`:
```json
{
  "version": "1.0",
  "mappings": {
    "accident_types": {
      "감전": "ELECTRIC_SHOCK",
      "절단": "CUT",
      ...
    },
    "hazardous_agents": {...},
    "environmental": {...},
    "ppe_states": {...}
  },
  "drop_list": ["없음", "기타"]
}
```

### Step 4: transform (5분)
```bash
serving-team/08-app/backend/.venv/bin/python \
  data-team/05-enrichment/llm-scripts/transform_synthetic_to_en.py --apply
```
10개 JSONL 파일 변환 + 자동 backup.

### Step 5: 새 baseline 저장
```bash
cd serving-team/08-app/backend
DATABASE_URL=... .venv/bin/python -u scripts/replay_synthetic_observations.py --save-baseline
```
주의: 이전 baseline_v2와 metric 변경 가능. delta를
[docs/status/evaluation-baseline.md](../status/evaluation-baseline.md)에 기록.

### Step 6: regression test
변경된 baseline 기준으로 향후 PR이 회귀 통과하는지 확인.

### Step 7: commit
- synthetic_observations_v*.jsonl × 10 (변환)
- synthetic_ko_to_en_final.json (mapping)
- runtime-artifacts/replay_baseline.json (새 baseline)
- docs/status/evaluation-baseline.md (delta 기록)

## 예상 결과 (현재 mining 데이터 기준)

| axis | KO codes | auto-mapped 예상 | LLM 필요 예상 |
|---|---|---|---|
| accident_types | 397 | ~50 (catalog 13 코드 KO labels via alias) | ~347 |
| hazardous_agents | 797 | ~50 | ~747 |
| environmental | 506 | ~30 (catalog 미정의 axis) | ~476 |
| ppe_states | 157 | ~30 | ~127 |
| **총** | **~1857** | **~160 (9%)** | **~1700 (91%)** |

LLM 비용: 1700 × $0.001 ≈ **$1.70**, 시간 ~10분.

## 위험 / 주의

1. **Baseline shift**: synthetic 데이터 변경 = baseline 변경. 향후 회귀 비교 기준이 바뀜. 이전 baseline_v2 메트릭과 의미 다를 수 있음.
2. **catalog 확장 필요**: 1700건 중 일부는 catalog 추가 필요 (예: ELECTRIC_SHOCK은 catalog에 이미 있지만 "근골격계 부상"은 ERGONOMIC sub-class). LLM 큐레이터가 "new catalog code 제안" → 별도 Part 4로 catalog 확장 작업 발생.
3. **drop_list 결정**: "없음", "기타", "일반" 등은 enum 부적합. drop_list에 넣어 변환 시 제거. 결과적으로 expected_features 일부 axis가 비게 될 수 있음.
4. **synthetic generator 미발견**: v*.jsonl 생성 source code 없음 (이전 세션 LLM prompt로 직접 생성한 듯). 향후 추가 데이터 필요 시 generator 재구축 또는 데이터셋 freeze.

## 관련

- Part 1 완료: disjoint TTL industry URI (commit `e320ffe`)
- Part 2 완료: guide_llm_domains + profiles industry refs (commit `35ca839`)
- Part 3 이 워크플랜
- Part 2.5: profiles의 비-산업 KO 어휘 (화학물질명 49건 등)
- Part 4 (잠재): synthetic transformation 중 발견되는 new catalog code 후보
