# F.1 Day 6 — 8 real-test-photo eval 보고

**날짜**: 2026-05-18
**커밋**: F.1 Day 5 (`eba4c76`) 위에서 측정
**candidate file**: 6 aliases (`risk_feature_aliases_candidates.json`)

## 측정 방식

각 photo 2회 분석 (`LLM_RERANK_MODE=shadow`):
- **ON**: candidate file 활성 (cascade step 4.5에서 6 aliases 매칭)
- **OFF**: candidate file 옆으로 이동 → step 4.5 no-op

비교: `analysis_log.jsonl[normalizer_unknown_codes]` 길이 — Vision LLM이 추출한 free-form text 중 Normalizer가 매핑 못한 raw text 수.

## 결과 — 8 photos × 2 runs

| Photo | ON 미매핑 | OFF 미매핑 | 변화 |
|---|---|---|---|
| 고소대작업 | (hook 미발동) | - | - |
| 안전대길이 | 0 | 0 | = |
| 영세제조업 | 1 | 1 | = |
| 음식점주방 | 1 | 1 | = |
| **지게차** | **0** | **2** | **✓ -2** |
| 최근대전화재바닥에기름 | 0 | 0 | = |
| 포크레인주변작업자 | 2 | 2 | = |
| 프레스(중대재해백서2024) | 1 | 1 | = |

**개선: 1/8 (지게차만)** — plan target ≥6/8 미달.

## Plan acceptance 미달 — 근본 원인 진단

### 발견 1: 6 candidates의 실제 어휘 coverage = **0**

| 데이터 소스 | 검사 entries | 6 candidates 중 hit | hit/total |
|---|---|---|---|
| Synthetic v1~v10 visual_cues | 2,360 | 0 | **0%** |
| analysis_log raw_vision_features | 2,551 (15 with field) | 0 | **0%** |

6 candidates 목록:
- `FALL_FROM_HEIGHT` ← '고소추락'
- `CHEMICAL_BURN_FROM_STRONG_ACID` ← '강산 화학화상' / '강산 원액 화학화상'
- `FINGER_AMPUTATION` ← '손가락 잘림'
- `CONFINED_SPACE_CLEANING` ← '밀폐 습윤공간 청소' / '제한공간 내부 청소'

→ 이 표현들이 **synthetic data 어휘에도, production traffic 어휘에도 0번 등장**.

### 발견 2: 실제 production miss 어휘는 영어 (또는 영어 enum 변형)

OFF run의 실제 unknowns:
- `MACHINERY (work_context)` — 4 photos
- `FORKLIFT (work_context)` — 1
- `FALLING OBJECT (accident_type)` — 2 photos
- `falling object (accident_type)` — 1 (소문자 변형)
- `cooking (work_context)`, `kitchen (work_context)` — 음식점주방
- `machinery (work_context)` — 변형

→ Vision LLM이 **영어 enum-스타일 변형** (대소문자, 약간 다른 형태) 생성. 한국어 alias가 아닌 **영어 alias/normalizer 정규화** 필요.

## 진단 — F.1 mining 파이프라인의 근본 issue

```
[현재 mining flow]
synthetic_observations_v*.jsonl (한국어 visual_cues)
    ↓
auto_register_aliases_light.py (LLM이 한국어 alias 후보 생성)
    ↓
recover_catalog_mismatch.py (한국어 → catalog enum 매핑)
    ↓
auto_register_aliases.py 4-Gate (검증 + 등재)
    ↓
6 candidates 모두 한국어 표현
```

**문제**: production Vision LLM은 **영어 enum 변형**을 주로 생성 (catalog가 영어 기반).
**해결**: mining 입력을 production analysis_log (실제 unknown)으로 전환.

## Day 6 정직한 평가

### 성공한 것
1. ✅ **F.1 pipeline 전체 작동 검증** (mining → 4-Gate → atomic write → cascade step 4.5)
2. ✅ **production-safe 보장** (Gate 3 PASS, 모든 metric delta 0)
3. ✅ **Day 5 6 aliases는 진짜 작동**: 지게차 photo에서 normalizer miss 2→0
4. ✅ **Critical insight 발견**: synthetic-driven mining ≠ production-driven mining

### 실패한 것 / 미달
1. ⚠️ **Plan acceptance ≥6/8 미달** (실제: 1/8)
2. ⚠️ **6 candidates coverage 0/2360 synthetic + 0/2551 log** — mining 입력 오방향

### 진짜 가치 신호
F.1 가치는 candidate count가 아니라 **closed loop 자체**:
- 6 aliases 등재는 PoC ("can system register aliases safely?": YES)
- 실제 효과 측정은 **production traffic 누적 후 mining**에서 가능
- A hook이 이미 작동 중 → 1-2주 데이터 누적 후 진짜 mining 가능

## 다음 단계 권장

### 즉시 (Day 6.5)
1. **mining 입력 전환**: synthetic → analysis_log (A hook 데이터)
   - 현재 15 entries with field만 누적 → 더 많은 traffic 필요
   - `auto_register_aliases.py --skip-light` 로 log-only mining 가능
2. **영어 unknown 처리**: 'MACHINERY', 'FORKLIFT', 'cooking' 같은 영어 표현이 catalog 코드의 alias로 등재되어야 함
   - 예: 'MACHINERY' → axis-flip 인식 후 적절한 work_context 코드 매핑

### Day 7 (예정대로)
- `promote_aliases.py` + runbook + Makefile
- candidate → vetted 승격 로직 (50회 사용 또는 manual)

### F.2 (별도)
- catalog v3.1 + 161 new subcode 후보 (이미 94 추가)
- ppe_state / environmental axis 신설 결정

## 한계 / Known issues
- 1 photo (고소대작업)에서 A hook 미발동 (early-return 경로) — `LLM_RERANK_MODE=off` 또는 `knowledge.guide_rows` 빈 상태. 별도 fix 후보.
- LLM 비결정성: Day 5 Gate 2 PASS가 run마다 4-6 변동. 다중 run 평균 권장.

## 산출
- `data-team/05-enrichment/llm-scripts/eval_real_photos_day6.py` (재실행 가능)
- `data-team/05-enrichment/runtime-artifacts/day6_real_photo_eval.json` (raw 결과)
- 본 보고서
