# 현재 세션 / 다음 세션 시작 지침

최신 갱신일: **2026-05-17 (밤)** — F.3 first batch (`11e46c6`) + A hot-fix (`d0b2262`) + **F.3.3 Gate 3 regression PASS** (`eb7843f` → merge `5b10980`) + **14-docs sweep** (`af26e13` → merge `f5bde60`, 메인 HEAD)

이 문서는 다른 Claude/Codex/LLM 세션이 현재 상태를 빠르게 이어받기 위한 시작점이다.

불변 메타 규칙(팀 구조, 9단계 작업 모델, 폐기 용어, 절대 금지)은 루트 [../../CLAUDE.md](../../CLAUDE.md) 참고.

## 🚀 다음 세션 시작 시 먼저 읽을 문서 순서

### 즉시 (5분 내 컨텍스트 파악)
1. **[../../CLAUDE.md](../../CLAUDE.md)** — 자동 로드 (불변 규칙 + 팀 구조)
2. **이 문서** (status/current-session.md) — 현재 상태 + 다음 작업
3. **[../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)** ⭐ — **메인 plan, 이번 두 세션의 핵심 성과**

### 깊이 (필요 시)
4. [../architecture/4-layer-architecture.md](../architecture/4-layer-architecture.md) — Layer 0-4 전체 구조
5. [../architecture/ontology-learning-layer.md](../architecture/ontology-learning-layer.md) — Layer 4 7-module 정밀 설계
6. [../architecture/llm-dependency-evolution.md](../architecture/llm-dependency-evolution.md) — LLM 의존 폐지 path
7. [../governance/ontology-learning-references.md](../governance/ontology-learning-references.md) — 9 학계 paper 요약

### 기존 baseline / 디렉토리 구조
8. [evaluation-baseline.md](evaluation-baseline.md) — 5번 enrichment baseline (변화 없음)
9. [../architecture/team-structure.md](../architecture/team-structure.md), [stage-mapping.md](../architecture/stage-mapping.md)
10. [../governance/repositories.md](../governance/repositories.md), [data-governance.md](../governance/data-governance.md)

## 📍 현재 상태 한 문장 요약

> "Phase 0/B/A/C + E-prep + E.2 (Openllet 통합) + Phase 3 (reasoning catch 1,902건) + **F.3 first batch + F.3.3 Gate 3 PASS (8 candidate production-safe) + 14-docs sweep 모두 완료**. 다음: **F.1 Normalizer auto-registration (1주, 별도 plan)**."

## 🎯 핵심 성과 (2026-05-16 ~ 17)

### Phase 0/B/A/C (LLM 자율 도메인 보강) — 완료
- **baseline_v2**: she_accuracy 55.81% → **60.72%** (+4.9%p), overall 13.31% → **15.25%** (+1.94%p)
- **active_v2**: positive avg_procedures 3.07 → **2.26** (−26.4%) — LLM rerank 효과
- **8 real-test-photo**: 4/5 over-promote 차단 확인 (지게차/영세제조/포크레인/음식점)
- **Phase C 자율 학습**: 2,528 analysis_log + 31개 신규 incompatibility 자율 채택

### Phase E-prep + E.2 (Openllet 통합) — 완료
- **Step 1**: 50 CQ + 55 class layer (B 26/A 20/Bridge 9) + 7 reuse scorecard
- **Step 2**: kosha-ontology-v2.owl (BFO + LKIF imports + 64 subClassOf)
- **Step 3**: kosha-disjoint-axioms.ttl (84 industries, 2,192 disjoint) + 22 SWRL + 26 SHACL
- **Step 4**: OntoClean 13 violations → **1** (92% 자동 수정)
- **E.2**: Fuseki Java가 v2 ontology + disjoint + SHACL + 172 subClassOf 로드 (commit `3520cab`)
- **Verification**: SHACL Conforms: True ✅, Openllet inference 정상

### Phase 3 (catalog v4 + SHE patterns + reasoning catch) — 완료
- **Phase 3A audit**: 1,914 synthetic codes hybrid ensemble 검증
- **Phase 3B catalog v4**: +170 신규 codes + 169 sub + 193 aliases
- **Phase 3C direct LLM SHE patterns**: 498 신규 → validation 후 누적 **1,616** PG she_patterns
- **Phase 3D**: synthetic v1~v10 EN enum transform + baseline_v3
- **Phase 3 validation**: ontology reasoning이 LLM 환각/과대추정 **1,902건 catch** (보고서 `docs/status/reasoning-catch-effectiveness-2026-05-17.md`)
- **8 real-test-photo 라이브**: 평균 사진당 1건 부적절 추천을 reasoning이 사용자 앞에서 reject

### Phase F.3 자율 axiom learning loop — 첫 정식 단계 완료 ⭐
- **F.3.0 (commit `8ff40d7`)**: 2,525 excluded entries 5 카테고리 분류 — `axiom_missing 36.44%` (920건, **210 unique pair**) → PROCEED_F3
- **F.3.5-prep (commit `ebe1011`)**: `analysis_log.jsonl`에 Runtime 4번 환류 채널 3 신규 필드 (`normalizer_unknown_codes`, `she_match_count`, `raw_vision_features`)
- **C cleanup (commit `2ea800d`)**: `guide_domain_incompatibilities.json` 2,232 entries 100% KO→EN translated (mining 정확도 normalize)
- **F.3.2 first batch (commit `9219c7c`)**: 49 LLM verify → **8 accepted candidate axiom** (incompatible_count 2,232 → 2,240)
- **Merge `11e46c6`** + GitHub push 완료
- **A hot-fix (commit `a841a0b` → main `d0b2262`)**: `raw_vision_features` 타입을 `dict` → `list`로 수정. ebe1011에서 dict() 변환 시 `risk_feature_candidates`(array)를 받아 `ValueError: dictionary update sequence element #0 has length 4; 2 is required` 발생. 2,360 synthetic replay에서 1,700 errored 원인. 3-case quick test로 0 errored 검증 후 push.
- **F.3.3 Gate 3 regression PASS (commit `eb7843f` → main `5b10980`)**: 2,360 synthetic replay 전체 valid, 0 errored. she_accuracy delta `-0.0013` (노이즈 범위), 모든 metric 회귀 없음. 8 candidate axiom **production-safe 검증 완료** — 수동 vetted 승격 가능 (50회 대기 불필요). 보고서 `docs/status/f33-gate3-regression-2026-05-17.md`.
- **14-docs sweep (commit `af26e13` → main `f5bde60`, HEAD)**: F.3 first batch + hot-fix + F.3.3을 14개 docs 전 영역(README/architecture/status/workplans/governance/backlog) 반영. 메타 일관성(current-session ↔ evaluation-baseline ↔ workplans) cross-check 완료.

### 학계 reference 통합 — 완료
- 9 paper 분석 (`ontology-team/reference-article/`)
- Layer 4 = 7 module 정밀 구성
- 우리 차별점: deontic 도메인 + 한국어 + asymmetric trust + Task C SOTA + Task D 학계 미답

## 📦 신규 산출물 (오늘 후반 — main에 push 완료)

오늘 후반 (F.3 sprint + F.3.3 + sweep) commits + merge:
- `classify_reject_reasons.py` + 산출 jsonl/json + sample_100 (F.3.0)
- `analysis_pipeline.py` 수정 (Runtime 4번 hook 3 필드, A) + hot-fix (`raw_vision_features` list)
- `translate_incompat_industries.py` + KB 변환 (C)
- `mine_missing_axioms.py` + 8 candidate (B)
- `data-team/05-enrichment/runtime-artifacts/replay_post_f32.json` (F.3.3 replay)
- `docs/status/f30-reject-reason-classification-2026-05-17.md` (F.3.0 보고서)
- `docs/status/f33-gate3-regression-2026-05-17.md` (F.3.3 PASS 보고서)
- `docs/` 전반 14 docs sweep (`af26e13`): README/architecture/status/workplans/governance/backlog

오늘 오후~저녁 (Phase 3 sprint) 18 commits — 자세히는 git log main 참조.

전체 산출물 history: [../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)

## ⚠️ 다음 세션 시작 시 주의사항

1. **현재 작업 worktree**: `.claude/worktrees/trusting-chandrasekhar-7b2041/` (claude/trusting-chandrasekhar-7b2041 branch). main에 머지·push 완료, 정리 시 worktree 제거 가능
2. **API 키**: `serving-team/08-app/backend/.env`에 OPENAI_API_KEY 설정됨 (sk-proj-A5... prefix, len 164). 정상 작동 확인 (F.3.2 49 verify 성공)
3. **8 candidate axiom 'level=candidate' 상태**: `promote_incompatibilities.py`가 50회 사용 후 vetted 자동 승격 — 또는 F.3.3 Gate 3 regression 통과 시 수동 즉시 승격
4. **편의점 KO unmapped 발견** (B에서): `industry_ko_to_en_map.json` 84 entry에 빠진 산업명. mapping 확장 후보
5. **A hook 한계**: `LLM_RERANK_MODE=off` 또는 `knowledge.guide_rows` 비어있는 early-return 시 hook 미실행. 별도 항상-실행 hook 후보
6. **stash@{0}**: `WIP on main: ca55ac6` (이전 세션 8 real-test-photo PNG/JPG untracked). 무관함, 보존

## 🛣️ 다음 작업 우선순위

### 1순위: Phase F.1 — Vocabulary auto-registration (1주)
- Module 4.1 — Layer 1 alias 사전 자율 등재
- 코드: 신규 `data-team/05-enrichment/llm-scripts/auto_register_aliases.py`
- 패턴: `mine_overpromote_patterns.py` + `mine_missing_axioms.py` (F.3.2 첫 batch) 재사용
- 4-Gate 검증 (embedding + multi-LLM + counter-example + asymmetric trust)
- 입력: A에서 추가한 `analysis_log.jsonl[normalizer_unknown_codes]` 필드 mining
- 효과: 8 real-test-photo의 6/8(75%) Normalizer miss 자율 해소

### 2순위 (작은 quick win — F.3 후속 정리):
- **편의점 등 KO unmapped 보강**: `industry_ko_to_en_map.json` 확장 (5분)
- **A hook always-on**: `_apply_llm_rerank` early-return 경로 hook 호출 또는 별도 hook (1-2h)
- **8 candidate axiom 수동 vetted 승격**: F.3.3 Gate 3 PASS 확인 — 50회 자동 대기 불필요, `promote_incompatibilities.py` 즉시 실행 가능 (30분)
- **F.3.0 LLM 2nd pass** (~$1): ambiguous 466건 LLM 재분류 → axiom_missing 추가 회수 (1h)

### 3순위 (학계/품질):
1. OntoGPT 통합 (`pip install ontogpt`)
2. Two-way CoT prompt 전환 (기존 LLM-scripts)
3. OOPS! Pitfall Scanner + LinkML schema 검증

## 🔧 OHS 실행 (시연용)

PG + Fuseki 컨테이너 (이미 동작 중):
```bash
docker ps | grep -E 'kosha-pg|kosha-fuseki'
```

backend + frontend dev-up (WSL):
```bash
cd /mnt/c/project/arch-bot
# baseline 시연 (LLM rerank off, 비용 0)
make dev-up
# 또는 LLM rerank 활성 시연 (Phase B+A.4 효과 시각화)
LLM_RERANK_MODE=active make dev-up
make dev-check
```

브라우저: http://127.0.0.1:5173/ohs/

8 real-test-photo: `C:\project\arch-bot\real-test-photo\`

## 📊 검증 명령 (회귀 확인)

```bash
# rdflib parse + Local consistency check
cd /mnt/c/project/arch-bot
/mnt/c/project/arch-bot/serving-team/08-app/backend/.venv/bin/python \
  data-team/05-enrichment/llm-scripts/local_consistency_check.py --skip-instances --skip-sparql

# 2,360 synthetic replay (baseline 측정)
cd /mnt/c/project/arch-bot/serving-team/08-app/backend
DATABASE_URL='postgresql://kosha:1229@localhost:5432/kosha' \
.venv/bin/python -u scripts/replay_synthetic_observations.py \
  --output /tmp/replay_check.json

# regression gate (baseline vs current)
.venv/bin/python scripts/regression_gate.py /tmp/replay_check.json
```

## 🌟 핵심 통찰 (다음 세션 결정 기준)

1. **현재 SHE 부족분 = LLM 보강 JSON으로 메꿈** → 정형 OWL/SWRL/SHACL로 점진 대체
2. **Vision LLM만 영구 유지** (인식 영역). Semantic reasoning은 reasoner로 이전
3. **Layer 4 (Ontology Learning) 별도 layer 필수** — long-tail 도메인 자율 적응
4. **closed vocabulary 기각** (사용자 결정) — 학계 SOTA와 일치
5. **자율 등재 위험성** — 4-gate 검증 (embedding + multi-LLM + counter-example + asymmetric trust)
6. **우리 시스템의 학계 차별점** = LKIF-Core × BFO + 한국어 + asymmetric trust + Task C SOTA + Task D 미답
7. **7단계 PG 재물질화** = reasoner 추론 결과 → PG → 서빙 ms 응답

## 5단계/6단계 전환 시각화

```
[현재 5단계] LLM 의존 hybrid
   Vision LLM → Normalizer → SHE 매칭 → LLM enrichment lookup → Phase B LLM rerank → dynamic KB

[Phase E.2 후 6단계] declarative reasoning
   Vision LLM → BFO Photo instance → Openllet OWL DL → SWRL/SHACL → 정형 추론

[Phase F+ Layer 4] cross-cutting 자율 학습
   Layer 1-3 데이터 → 7 module → vocabulary/class/rule 자동 등재 → asymmetric trust

[Phase G 7단계] PG materialize
   reasoner 결과 → PG table → 서빙 PG SELECT only (ms, LLM 0회)
```
