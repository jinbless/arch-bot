# 현재 세션 / 다음 세션 시작 지침

최신 갱신일: **2026-05-17** (Phase E-prep + Layer 4 설계 완료 세션)

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

> "Phase 0/B/A/C + Phase E-prep 완료. Layer 4 (Ontology Learning) 7-module 학계 reference 기반 정밀 설계 완료. backend 코드 운영 중 (baseline_v2 + LLM rerank). 다음: Phase E.2 (Openllet 정식 통합) 또는 Phase F.1 (vocabulary auto-registration)."

## 🎯 이번 두 세션 (2026-05-16~17) 핵심 성과

### Phase 0/B/A/C (LLM 자율 도메인 보강) — 완료
- **baseline_v2**: she_accuracy 55.81% → **60.72%** (+4.9%p), overall 13.31% → **15.25%** (+1.94%p)
- **active_v2**: positive avg_procedures 3.07 → **2.26** (−26.4%) — LLM rerank 효과
- **8 real-test-photo**: 4/5 over-promote 차단 확인 (지게차/영세제조/포크레인/음식점)
- **Phase C 자율 학습**: 2,528 analysis_log + 31개 신규 incompatibility 자율 채택

### Phase E-prep (LLM-Accelerated 정석 ontology engineering) — 완료
- **Step 1**: 50 CQ + 55 class layer (B 26/A 20/Bridge 9) + 7 reuse scorecard
- **Step 2**: kosha-ontology-v2.owl (BFO + LKIF imports + 64 subClassOf)
- **Step 3**: kosha-disjoint-axioms.ttl (84 industries, 2,192 disjoint) + 22 SWRL + 26 SHACL
- **Step 4**: OntoClean 13 violations → **1** (92% 자동 수정, 5 iteration)
- **Step 5**: 40 SPARQL queries (2% coverage, Photo persist 후 회복 예정)
- **Verification**: SHACL Conforms: True ✅ (v3, 194 triples), rdflib parse PASS

### 학계 reference 통합 — 완료
- 9 paper 분석 (`ontology-team/reference-article/`)
- Layer 4 = 7 module 정밀 구성
- 우리 차별점: deontic 도메인 + 한국어 + asymmetric trust + Task C SOTA + Task D 학계 미답

## 📦 신규 산출물 (이번 세션, 미커밋 상태)

전체 목록: [../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md) "신규 산출물" 섹션

요약:
- Ontology files: 7개 (kosha-ontology-v2.owl, disjoint-axioms.ttl, rules-v2.swrl, shapes-v3.ttl 등)
- Backend code: 5개 신규 + 8개 수정
- Data team scripts: 16개 신규 (`data-team/05-enrichment/llm-scripts/`)
- Runtime artifacts: 20+ JSON (CQ, layer, disjoint, OntoClean 등)
- Frontend: 1개 신규 (SourceBadge.tsx) + 5개 panel 수정
- Reference articles: 9 PDF (사용자 추가)
- Docs: 5개 신규 (이 세션 마무리 단계에서 추가)

## ⚠️ 다음 세션 시작 시 주의사항

1. **신규 산출물 50+ 미커밋** — 사용자 의사 확인 후 commit
2. **plan 임시 파일** (`.claude/plans/workplan-llm-domain-guard-vs-needtochang-lucky-lemon.md`)은 정식 문서로 이전됨. 무시 가능. 단 참고용으로 보존
3. **worktree**: 현재 작업이 `.claude/worktrees/strange-rosalind-601a61/`에서 진행됨. 정식 commit은 root `arch-bot/main`으로
4. **API 키**: 이전 세션에 노출된 5개 키는 사용자가 OpenAI 대시보드에서 회수 완료(2026-05-17). backend가 동작하려면 새 키를 `serving-team/08-app/backend/.env`에 두어야 함

## 🛣️ 다음 작업 우선순위

### 1순위 (선택 A): Phase E.2 — Openllet 정식 통합 (~1시간)
- Fuseki Java 코드 수정 (`ontology-team/06-reasoning/ontology/docker/fuseki/src/main/java/kr/or/kosha/KoshaFusekiServer.java`)
- 현재 `kosha-ontology.owl` (v1) hardcoded → v2 load + 추가 .ttl/.swrl import
- container rebuild + Openllet consistency check
- 효과: 진짜 OWL DL reasoner 통합 (6단계 본격 진입)

### 1순위 (선택 B): Phase F.1 — Vocabulary auto-registration (3-5일)
- Module 4.1 — Layer 1 alias 사전 자율 등재
- 코드: 신규 `data-team/05-enrichment/llm-scripts/auto_register_aliases.py`
- 패턴: Phase C.2 (`mine_overpromote_patterns.py`) 재사용
- 4-Gate 검증 (embedding + multi-LLM + counter-example + asymmetric trust)
- 효과: "매핑 불가 코드" 자율 해소, long-tail 도메인 자동 적응

### 2순위 (선택): 즉시 적용 권장 3가지
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
