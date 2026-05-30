# 현재 세션 / 다음 세션 시작 지침

최신 갱신일: **2026-05-30 (오후)** — ⭐ **온톨로지 prefix 표준화(`1aa0743`) + manifest 단일정본 재설계 Phase 1(`f751397`) — 둘 다 push됨**. origin/main HEAD `f751397`. 이전 같은 날: Three-Worlds S1(Phase 0/1/3a/4) + Phase 5 가드레일. **다음 궁극 목표: facet class/individual 리모델(재설계 Phase 3)**.

## ⭐ 2026-05-30 (오후) — prefix 표준화 + manifest 단일정본 재설계 Phase 1 (push 완료)

**승인 plan**: `~/.claude/plans/calm-hugging-pond.md`(이제 **온톨로지 체계 재설계** — Phase 1 manifest / Phase 2 구조심화 / Phase 3 facet 리모델). 동기: 버전·패치 난립 + 6 로더 제각각 하드코딩 → "무엇이 온톨로지인가" 단일 정본 부재.

**A. prefix/namespace 표준화** (`1aa0743`): cashtoss.info 네임스페이스마다 정본 짧은이름1+IRI1.
- `agent:` 의미 과부하 → `agent:Worker`(행위자) **`actor:` 분리**. 별칭 통일(context→ctx/hazard→haz/sit→she/penalty→pen). 화석 `kosha-instances.original.ttl` 삭제(레거시 28k). guide-profile-patch orphan 수정(`kosha:KoshaGuide`→`guide:KoshaGuide`). 생성기 `regenerate_subclass_patch.py` axis casing(accident=UPPER, agent/ctx=Pascal). pipe-A pilot `ontology/hazard#`→`risk/hazard#`.
- **신규 가드레일**: `validate_prefixes.py`(+`make verify-prefixes`), `compare_graphs.py`(그래프 동치 오라클). 검증: 위반 0 / 레거시 0 / 리즈너 conforms=626.
- v3 G-patch(incompat/guide-profile/penalty-relations/restructure)는 **Phase G TBox SoT라 유지**(삭제 안 함). ⚠️ restructure-patch는 파싱실패(`<>` 누락 3줄) — Phase 2 수리 대상.

**B. manifest 단일정본** (`f751397`) — 평탄화(merge) 아니라 명명:
- `assembly/manifest_source.py`(SSOT 59파일·6 profile) → `gen_manifest.py` → `assembly-manifest.json`. `assembly/manifest.py`(소비자 `load_profile`). `validate_manifest.py`+`make verify-manifest`(silent orphan 0+freshness 게이트).
- **6 소비자 repoint**: Python 5(run_shacl/local_consistency/serve_facets/run_inference/run_guide_hazard) + **Java Fuseki**(번들 `org.apache.jena.atlas.json`, 추가 의존성 0, bind-mount라 이후 파일집합 변경 시 Java 재빌드 불필요).
- **base v1→v2 정정 = facet 버그 해결**: serve_facets/run_inference가 v1 base 로드+subclass 누락 → v2+subclass/disjoint → **facet-explorer haz 2→137 / agent 1→37 owl:Class** 정상.
- 검증(no-op): 6 profile==기존 하드코딩(set-equality), run_shacl conforms=626 불변, Fuseki 21파일·base 981,440, local_consistency merged 26 동일. **serving/consistency/shacl 그래프 불변**.

**핵심 발견(Phase 3 동기)**: facet 코드 class/individual 비정합 — haz/agent: fine=class·canonical=individual, **ctx: 전부 individual·subClassOf 0**(107 정의 중 29만 facet 사용, `ctx:ForkliftOperation` 등 78 잠금 → forklift 변별 상실의 근원). 데이터 개체(SR/CI/Guide/관찰)는 individual 유지가 정답.

**다음 (우선순위)**: **Phase 3 facet 리모델**(haz/agent/ctx→일관 owl:Class+subClassOf taxonomy, canonical도 class화, ctx 계층 신설, **punning으로 기존 facet assertion 51,776 보존**, 데이터 개체는 individual 유지 → forklift fine 변별 복원 → PG 재물질화) = **궁극 목표**. / (선택) P1.6b 물리 archive 이동(17파일 archive/) + serving-snapshot 78MB 삭제 / Phase 2 구조심화(layer 디렉토리 + SWRL→SHACL parity-gated + restructure 수리). **serve_facets(3031)는 재시작해야 고쳐진 explorer(haz=137) 반영**.

## ⭐ 2026-05-30 — Three-Worlds CI/Guide 매칭 재설계 S1 (Phase 0/1/3a, working tree)

**메인 작업.** 사용자 재정의: open-world(사진 hazard) → closed-world(SR/CI/Guide) 매핑, **온톨로지=SoT + 업데이트 메커니즘, PG=특정시점 스냅샷**. 문제: 실사진에서 SR은 매칭되나 **CI/Guide 안 됨**. 근본 원리(사용자 합의): **CI는 고유 control 세계, Guide는 분야별로 control을 묶는 bundle 계층. open-world O는 CI·Guide와 각각 독립 facet 매칭, 구조(Guide-bundles-CI)는 랭킹 corroboration.** boilerplate=canonical CI의 guide-degree(구조). PG-side 인버전(derive_guide_hazard_features+export_guide_hazard_to_abox) 폐기 → 온톨로지 유도 → PG 물질화. 승인 plan: `~/.claude/plans/calm-hugging-pond.md`.

**Phase 0 — Canonical-CI 레이어** ✅: `kosha-ontology-v4-canonical-ci-patch.ttl`(`CanonicalChecklistItem ⊑ ChecklistItem` + `realizesControl`/`bundlesControl`/`controlBundledBy`). `derive_canonical_ci.py`(정규화-텍스트 NFKC 군집): **54,631 instance → 51,263 canonical**(축소 6.2% — 정확-텍스트는 literal boilerplate만; 큰 dedup은 semantic merge=Phase 3b gated), degree=guide_frequency(max 130), boilerplate 71(degree≥10). PG staging: `canonical_checklist_items`/`guide_control_bundle`/`checklist_items.canonical_ci_id`. `export_canonical_ci_abox.py` → `kosha-instances-canonical-ci.ttl`(466k triple, facet/degree/basedOnSR 집계 직접 부여 → inverse 링크 불요).

**Phase 1 — facet 유도(ontology SHACL)** ✅: `kosha-rules-guide-hazard-shacl.ttl`(6 CONSTRUCT: CI-SR 상속 3 + non-boilerplate Guide rollup 3) + `run_guide_hazard_rules.py`(rdflib fast-path, fixpoint) → `kosha-instances-ci-guide-hazard-derived.ttl`. **Guide rollup 10,423**(addressesHazard 2484 / guideAddressesAgent 3227 / guideAppliesToContext 4712, boilerplate 제외). **CI-SR 상속=0**(pipe-B step6가 이미 SR-enrich → CI accident 희소(27%)는 SR로 못 메움, **Phase 2 orphan 재태깅이 유일 lever**).

**Phase 3a — ontology→PG 물질화** ✅: `import_guide_facets_to_pg.py`(IRI→code SSOT 역변환 + wc_meta) → `kosha_guides` facet 컬럼(addresses_hazard **832 guide**>구 인버전 659 / agent 986 / context 979). `make verify-codes-shape` 대상(derived) **conforms=True**.

**검증 데모**(지게차 facets accident=CAUGHT_IN/COLLISION/CRUSHED_OVERTURNED, ctx=VEHICLE, PG 직접쿼리): **O↔CI 독립 매칭 = 좌석안전띠·포크삽입·차량브레이크·통로보호 등 정확 + boilerplate 71 억제 ✅**. O↔Guide = 항만하역 등 관련 + 광범위 VEHICLE 오매칭(오토바이배달) 잔존 → **Phase 4 fusion(corroboration 랭킹)이 sharpen 예정**.

**Phase 4 — 서빙 엔진** ✅ (구현+검증, **wiring ⏳**): `models.py`(PgCanonicalChecklistItem/PgGuideControlBundle + PgKoshaGuide facet 컬럼 + PgChecklistItem.canonical_ci_id), `hazard_rule_engine.query_ci_for_facets`/`query_guide_for_facets`(query_sr_for_facets 미러, CI 특이도=1/log2(2+guide_degree)), `match_fusion_service.fuse_matches`(O↔CI/Guide 독립 + **Guide corroboration boost**: 매칭 CI를 bundle한 Guide 가산). **WSL venv 실검증**(`scripts/verify_fusion_matching.py`): 지게차 → **B-M-11 지게차 안전작업 + A-G-18 항만하역이 corroboration으로 top, 오토바이배달 top-8 탈락** ⭐. O↔CI = 좌석안전띠·포크삽입 등 정확. (화학 시나리오: corroboration 미발화(분석 guide가 안전 CI 미bundle) → CI→guide recall 채널 추가가 후속 튜닝 후보.)

**Phase 4 wiring** ✅ (2026-05-30): `analysis_pipeline`이 `get_immediate_checklist_items`/`get_standard_guides`(무순위 junction/CI-count 전이 경로) 대신 `match_fusion_service.build_recommendation_rows`(계약형 CI/Guide row 어댑터 — 대표 instance + work_process_steps 보강) 호출로 교체. SR과 동일 게이트(`actionable_matches or observable_violation_signal`)로 negative-case false positive 방지. **검증**: WSL venv로 import OK → **Gate 3 PASS**(2,360 replay, false_positive_rate 0.87 유지·SR/SHE/penalty 회귀 0) → **8-photo eval**(Vision, parallel): 8/8 100% mapping, 48 procedures, 크래시 0.
- ⚠️ **정직한 한계**: 지게차 photo의 fusion procedures가 canonical `VEHICLE` 매칭 → 항만하역·컨베이어·이동식크레인 등 **광범위 vehicle/material-handling guide**(합리적이나 핀포인트 아님). **2026-05-29 ctx_boost의 fine `FORKLIFT_OPERATION` 변별 상실**(canonicalization이 FORKLIFT→VEHICLE 뭉갬). corroboration은 작동하나 소수 forklift CI가 다수 generic CI guide에 밀림. → **task: Phase 4 튜닝(fine work_context 보존·매칭 + corroboration을 CI 특이도 합으로 가중)**.

**다음**: Phase 4 튜닝(fine work_context 변별) → Phase 2(orphan 재태깅) → Phase 3b(hard-cut 인버전 삭제 + semantic merge). 재현 파이프라인: `derive_canonical_ci.py --apply` → `export_canonical_ci_abox.py` → `run_guide_hazard_rules.py` → `import_guide_facets_to_pg.py --apply` → (서빙) `verify_fusion_matching.py` / 8-photo eval.

## 2026-05-30 — Phase 5 incremental 가드레일 (Deferred #2 일부, working tree 미커밋)

2026-05-29 Deferred 후속 #2(Phase 5 incremental) 중 **자기완결·저위험 2건** 구현. 둘 다 SSOT(`canonical-code-vocabulary.json`) 파생 — 하드코딩/ PG re-tag 무영향. 자세히: [../dev-notes/phase5-incremental-guardrails.md](../dev-notes/phase5-incremental-guardrails.md).

**2a — SHACL codes∈canonical 가드레일** (선언적; `make verify-codes` regex 게이트의 보완재):
- `ontology-team/06-reasoning/ontology/scripts/gen_canonical_code_shape.py` → `kosha-canonical-code-shape.ttl` (자동 생성, NodeShape 4 = 축별 3 + feature union). 각 shape `sh:targetObjectsOf <코드 술어> + sh:in <정본 IRI> + sh:Violation`.
- 허용 = `canonical_set ∪ meta_set` = accident 23 / agent 10 / **work_context 36(=29+7 wc_meta)** = **69 IRI**. `canonical_vocab.meta_set(axis)` 공개 접근자 신설(additive — wc_meta=SAFETY_MGMT 등 rollup 항등 정당 축값).
- `validate_canonical_codes.py`(pyshacl) + `make verify-codes-shape` / `make gen-canonical-shape`.
- 검증: 전체 ABox **958,666 triple → conforms=True** (Phase 4-B "구어휘 잔여 0"을 SHACL allowlist로 독립 재확인). 음성 테스트(`haz:Crush`/`CAUGHT_IN`/`agent:ArcFlash`/`ctx:Forklift`) **4건 적발 + exit 1**, 정본 통과.

**2c — Layer 4.7 Continual pending 승격 추적** (gate WARN → 정식 태스크):
- `data-team/05-enrichment/llm-scripts/continual_pending_promotion.py` + `make continual-pending`. live PG(SR+CI+GUIDE) 빈도로 pending 코드 랭킹 + tier(PROMOTE≥8 / WATCH≥3 / NOISE). **읽기전용**(mutate 금지), queue 산출(gitignored).
- 현재 스냅샷: accident/agent 0건. **work_context 7건**(전부 GUIDE) — PROMOTE=`WET_FLOOR_WORK`(11), WATCH=`NIGHT_SOLO_WORK`(6), NOISE 5. 승격 결정은 사용자 몫(→ `build_canonical_vocabulary.py` 룰 보강 후 재생성).

**회귀 0**: `audit --gate` CRITICAL=0/WARN=7 PASS, `canonical_vocab`+`code_iri_mapper`(62) self-test PASS.

**신규**: gen_canonical_code_shape.py, validate_canonical_codes.py, kosha-canonical-code-shape.ttl, continual_pending_promotion.py, phase5-incremental-guardrails.md. **수정**: canonical_vocab.py(+meta_set), Makefile(+3 target), .gitignore. **⚠️ 미커밋 — 다음 세션에서 검토 후 commit.**

## ⭐ Canonicalization + KOSHA-22 Sprint — 단일 세션 완주 (2026-05-29) ⭐

지게차 사진 실측에서 정규화(risk_features)는 정확한데 SHE/Guide/즉시조치/표준절차가 엉뚱하게 나온 문제의 **근본 원인 = 단일 정본(canonical) 코드 어휘 미강제(4세대 어휘 공존: catalog 세밀 / PG 거친 / GUIDE seed / 온톨로지 dual-URI)**를 전 surface 정합 + 재발 방지로 해결. 커밋 `bbc9b8c`~`5fdd8a0` (+ merge `f4f078a`), 8커밋 origin/main 반영.

**Phase 1-3 — 정본 SSOT + PG canonical + 서빙 연결** (`bbc9b8c`, `7a465b0`):
- ⭐ 신규 SSOT: `shared/reference/canonical-code-vocabulary.json` (accident 23=**KOSHA-22 공식** / agent 10 / work_context 29) + 단일 소비자 모듈 `shared/reference/canonical_vocab.py` (`to_canonical(axis,code)`, 교차축 인지, self-test PASS). 빌더 `data-team/05-enrichment/llm-scripts/build_canonical_vocabulary.py`.
- **Additive 듀얼 태깅**(덮어쓰기 금지 — fine 코드 보존, SHE 1,616 패턴 무변경): SR/CI에 `*_canonical` jsonb + GUIDE에 `canonical_code`/`canonical_axis` 컬럼 신규, populate (SR 626 / CI 54,631 / GUIDE 70,296). schema `serving-team/07-materialization/pg-sync-scripts/schema_canonical_columns.sql` + `apply_canonical_tags.py`.
- 서빙: `hazard_rule_engine.query_sr_for_facets`/`get_guides_by_hazard_features` canonical 컬럼 조회 → 끼임(CAUGHT_IN)/전도(FALL)/지게차(VEHICLE) SR 커버리지 **0→76**.

**#95 지게차 충돌 잔존 fix** (`64a2a96`): 광범위 COLLISION/ERGONOMIC에서 '오토바이 배달' guide 오매칭 → `get_guides_by_hazard_features` **2-tier ctx_boost**(scene 구체 fine work_context(FORKLIFT_OPERATION) 보유 guide 강부스트 +0.30 [entity_type 무관 하위행 fine 활용], generic VEHICLE만 공유 약부스트 +0.05) + `_merge_guide_paths` CI-only −0.06. **실제 Vision 재실행 bad-hit 0** (오토바이 소멸, '지게차 운전자 교육' 표준절차 등장).

**Phase 4-B — 온톨로지 KOSHA-22 전면 마이그레이션** (`94bcdbb`): 3 공존 어휘 → KOSHA-22 단일 CamelCase **62개**.
- `serving-team/08-app/backend/app/integrations/code_iri_mapper.py`: 하드코딩 8/11/13 테이블 폐지 → **SSOT 파생 + 결정적 `_camel()`** + 구→KOSHA22 LEGACY 매핑 (sparql_queries 백워드 호환 유지).
- `ontology-team/06-reasoning/ontology/scripts/migrate_vocab_to_kosha22.py`: 50 TTL 결정적 fragment 치환 **~20,820건** (Crush→CaughtIn, Cut→CutLaceration, FallingObject→StruckBy, agent ArcFlash→Electricity, agent/ctx UPPER→CamelCase 등). `kosha-instances.original.ttl` 백업 제외.
- `kosha-ontology-v4-kosha22-vocab-patch.ttl` (62 NamedIndividual, `gen_kosha22_vocab_patch.py` 생성) + `kosha-accident22-disjoint.ttl` KOSHA-22 CamelCase 재작성.
- 검증(`validate_kosha22_migration.py`): 활성 TTL 구어휘 잔여 **0**, rdflib 파싱 OK(ABox 956k triples), disjoint rdf:type 위반 **0**, Gate 3 2,360 PASS.

**Phase 5 — 재발 방지 가드레일** (`c5e3bac`, `012b845`, `5fdd8a0`):
- ⭐ `scripts/audit_code_consistency.py --gate` — 온톨로지 UPPER/dual-URI 재발 시 **exit 1** (SSOT 인지; PG fine 코드의 pending(UNKNOWN) orphan은 WARN, open-class 허용). **`make verify-codes`** 등록. **게이트가 실제로 Phase 4-B의 agent/ctx UPPER 25종 누락을 적발 → 1,856건 자동 수정 → PASS** (재발방지 메커니즘 작동 입증).
- exporter 3종(`export_owl`/`export_guide_hazard_to_abox`/`export_8photo_to_abox`) → `code_iri_mapper` SSOT 일원화 (향후 PG 재생성 dual-URI 재발 차단).

**검증 수치** (Gate 3 baseline 대비, 전 단계 회귀 0): overall 0.1331→0.3254, penalty 0.1835→0.4729, sr 0.7636→0.7771, she 0.5581→0.5758.

**⏸️ Deferred 후속 (라이브 영향 없음 — 온톨로지 offline, 서빙은 PG 기반이라 forklift fix 이미 live)**:
1. **Fuseki Openllet reload** (~30분 warmup, 선택적 SPARQL enrichment만 영향): WSL `cd ontology-team/06-reasoning/ontology/docker && docker compose restart fuseki`. ⚠️ **2026-05-30 발견**: `KoshaFusekiServer.java`의 sources 목록이 in-place 마이그레이션된 `kosha-instances.ttl`(volume-mount, restart로 반영)은 로드하나 `kosha-ontology-v4-kosha22-vocab-patch.ttl`(62 NamedIndividual)은 **미포함** → 단순 restart론 정본 개체 선언이 안 됨. 결정 필요: (a) patch를 sources에 추가 + Java image rebuild, 또는 (b) 서빙층 patch 불요 확인.
2. **Phase 5 incremental** (저우선, 게이트 1차 방어):
   - ✅ **2a SHACL codes∈canonical** + ✅ **2c Layer 4.7 continual** — 2026-05-30 완료 (위 §2026-05-30, 미커밋).
   - ⏳ **catalog 죽은코드 deprecated + WRONG_AXIS work_context 정리** — 사용자 판단 + PG re-tag blast radius. 주의: `INTERLOCK_BYPASS`/`LOTO_NOT_APPLIED`/`SAFETY_DEVICE_BYPASS`는 이미 work_context 소속(→UNKNOWN_CONTEXT, catalog L2007–2034) — "WRONG_AXIS 18" 정확 목록 미보존 + "분리" 의도 불명확(meta-condition 별도 분리? 4/5번째 축에서 이동?). curation 의도 확인 필요. 2c가 pending 빈도 정량화(PROMOTE-tier=`WET_FLOOR_WORK` 1개뿐) → 긴급도 낮음.
3. **HTTP 서버 기동**: WSL `cd /mnt/c/project/arch-bot && make dev-up` (PRIMARY는 WSL venv 전용 → Git Bash에서 미기동). 기동 시 지게차 분석이 새 로직으로 LIVE.
4. **LFS**: `kosha-instances.ttl` 58MB(>GitHub 권장 50MB) → git-lfs 후보. 계획: [../dev-notes/large-file-management-plan.md](../dev-notes/large-file-management-plan.md). git history 영향 → 사용자 명시 승인 후 진행.

**다음 세션 재현/검증 (WSL, /mnt/c/project/arch-bot)**:
```bash
make verify-codes        # 코드 어휘 하드게이트 (드리프트 시 exit 1)
serving-team/08-app/backend/.venv/bin/python ontology-team/06-reasoning/ontology/scripts/validate_kosha22_migration.py  # disjoint 0 + 구어휘 0
python shared/reference/canonical_vocab.py   # SSOT self-test
```

## ⭐ axiom-100% Sprint — Phase A~K 완주 (2026-05-20~27)

온톨로지 공리 커버리지 100% 목표. SWRL 의사코드 30개를 정형 추론 가능 facts로 전환.

- **v4 TBox 패치 9종** (Phase A~J): `kosha-ontology-v4-{deps,alethic,bridge,deontic,violation,penalty-extra,restrictions,hazard-direct,asymmetric}-patch.ttl`. owl:Restriction **35** (allValuesFrom ABox-safe), owl:AsymmetricProperty **1** (`law:modifiesAsymmetric`, inverseOf 충돌 회피), NaturalLanguageHazardCategory **21**.
- **SWRL R-14~R-30 → SHACL CONSTRUCT 전환** ⭐ (Phase C~F): Pellet이 12개 SWRL 조합에서 **NEXPTIME blowup**(22분 무한 재시작) → `kosha-rules-r14-r30-shacl-construct.ttl` (12 sh:rule CONSTRUCT). Java sources에서 4개 SWRL ttl 주석 처리. R-1/R-3만 SWRL native 유지 (Pellet 정상: R-1 107 + R-3 3,579 inferred).
- **K-general SHACL** (Phase K): `kosha-rules-k-general-shacl.ttl` — 같은 Hazard → `core:dependsOn` **36,949** + 같은 Chapter → `core:coApplicable` **16,429** = **53,378 pair** (on-demand materialization, gitignore).
- **production ABox enrichment**: 8-photo eval → `kosha-instances-production-8photo.ttl` (R-10~R-30 fire 입증). sh:NodeShape 총 **1,964**.
- 검증: `scripts/verify_axiom_100pct.py` (5-step) Overall OK. Gate 3 regression PASS.
- Plan/Runbook: [../workplans/ontology-axiom-100pct.md](../workplans/ontology-axiom-100pct.md), [../dev-notes/axiom-100pct-phase-a.md](../dev-notes/axiom-100pct-phase-a.md) / [-b](../dev-notes/axiom-100pct-phase-b.md) / [-c-j](../dev-notes/axiom-100pct-phase-c-j.md).

## ⭐ guide-accuracy Sprint — P0~P3 완주 (2026-05-28)

실 서비스에서 CI 추천은 정확하나 Guide가 엉뚱하게 추천되는 문제 근본 해결 (boilerplate CI fan-out + CI 개수 단독 랭킹).

- **P1 CI 변별력**: `checklist_items.guide_frequency` 컬럼 (동일 텍스트 CI의 distinct source_guide 수) backfill **3,953 CI 갱신, max 130**. `ci_weight = 1/log2(1+gf)` (gf=130 → 0.14).
- **P0 Guide 랭킹 교체**: `hazard_rule_engine.get_guides_from_srs()` CI **개수** → **Σ(ci_weight) 변별력 가중합** + 정규화 + 산업 일치. boilerplate 자동 억제.
- **P2 Guide 직접 위험 매핑 레이어** ⭐: `derive_guide_hazard_features.py` → `guide_entity_feature_candidates(entity_type='GUIDE', method='guide_hazard_weighted_majority')` **2,115행 / 659 Guide**. 신규 `get_guides_by_hazard_features()` (CI 경유 없는 직접 조회) + `_merge_guide_paths()` (직접 우선 + CI union, 교집합 bonus +0.15).
- **P3 온톨로지 정합**: `kosha-ontology-v4-guide-hazard-patch.ttl` (`guide:addressesHazard`/`guideAddressesAgent`/`guideAppliesToContext` + `ciGuideFrequency`/`isBoilerplate`) + `kosha-instances-guide-hazard.ttl` (659 Guide, 2,115 triple).
- **8-photo guide eval**: mapping rate 80% → **100%** (27/27), guide_hazard_direct mapping **85%**, boilerplate Guide 출현 **0**. Gate 3 regression PASS (synthetic 회귀 없음).
- Runbook: [../dev-notes/guide-recommendation-accuracy.md](../dev-notes/guide-recommendation-accuracy.md).

## 🎯 Hazard-Direct Pivot — 단일 세션 완주 (2026-05-19) ⭐

본 세션의 핵심 성과. 23일 plan을 단일 세션에서 완주:

- **Phase 1 Day 1**: `ONTOLOGY_OBSERVATION_SCHEMA`에 `hazards[]` 추가 + 14개 표준 라벨 prompt (commit `acd2303`)
- **Phase 2 Day 1**: `generate_hazard_name_seed.py` (Sonnet 4.6 자동 seed) (commit `7a17b47`)
- **Phase 2-5 통합** (commit `7c97118`):
  - Phase 2 Day 2-7: Sonnet 19/21 accepted + 2 manual override → 21 vetted alias 등재
  - Phase 2 Day 3-4: `normalize_hazards_array()` 신규 함수 (hazard_normalizer.py)
  - Phase 3 Day 1-3: `hazard_to_guide_service.py` + analysis_pipeline `HAZARD_DIRECT_MODE` 통합
  - Phase 4 Day 1: `HazardItem` + `GuideRef` + `HazardGuideRelation` Pydantic + AnalysisResponse 확장
  - **Phase 5 Day 1**: 8 real-test-photo 실호출 → **25/25 (100%) 매핑** ⭐ (AC-2 ≥85% **PASS**)
- **Phase 4 Day 2** (commit `5256573`): Frontend `RiskOverviewPanel` 확장 + `HazardGuideRelationsPanel` 신규

8 photo eval 핵심 수치:
- 8/8 photos analyzed
- 25 hazards / **25 mapped (100%)** / 25 relations
- 48 standard_procedures (legacy 병행, 호환성 OK)
- 14 penalty paths (Phase G.3 차별점 보존)
- moellab overlap 18/37 (자연어 표현 차이)

Sprint plan + 결과: [../workplans/hazard-direct-architecture-pivot.md](../workplans/hazard-direct-architecture-pivot.md)
효과성 raw 데이터: [../../data-team/05-enrichment/runtime-artifacts/hazard_direct_8photo_eval.json](../../data-team/05-enrichment/runtime-artifacts/hazard_direct_8photo_eval.json)

이전 갱신:
- 2026-05-18 (저녁): Tier 1 재포함 + Tier 2 F.3 closing (T2.A-D) + Tier 3.A enum
- 2026-05-18 (오전): F.3 first batch + F.1 sprint (5 vetted aliases) + F.2 sprint (catalog v3.3, 5 axes × 481 codes)

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

> "Phase 0/B/A/C + E-prep + E.2 + Phase 3 + F.3 first batch + F.1 + F.2 (이전) + Tier 1-3.A + **Phase G PG materialization (G.1: guide_domain_incompatibilities 2,016 rows + G.2: guide_usage_profiles 1,038 PG primary + G.3: penalty_rule_index 4,076 rows → penalty_accuracy +27.16%p ⭐ + G.4: she_patterns_reasoner_derived view)** + **Tier 4 후속 (AsymmetricProperty 패치로 Openllet 정상화 + SWRL Pellet 실행기 통합 → R-1: 107 + R-3: 3,579 inferred ⭐ + Pellet reporting 명시화)** + **T4 #1 후속 sprint (approve 57 / modify 19 / defer 1, batch promote -10.17%p VETOED → matcher refactor sprint plan 작성) + moellab.info/ohs 위험요소 비교 (37/37 합리적, architecture pivot 후보 식별: hazard-direct)**. 사용자 구조 step 4 본격 입증. 다음 1순위: hazard-direct architecture pivot (sprint plan 작성 TBD)."

## 🎯 핵심 성과

### Phase G PG materialization + Tier 4 후속 (2026-05-19)

**사용자 구조 step 4 본격 입증**: "온톨로지화된 KB → PG 적재 → 실 서비스 자동 반영" 완성.

- **Phase G.1** (commit `d6b4589`) — `core:Incompatibility` ontology TBox 보강 + `guide_domain_incompatibilities` PG (2,016 rows: 8 vetted + 2,008 candidate, T2.D 8/8 PASS 자동 반영) + `shadow_reasoner.py` PG primary + JSON fallback. 10/10 sample equality. PG p50 0.4μs (cache warm).
- **Phase G.2** (commit `2f7ef92`) — `guide:GuideUsageProfile` OWL class **전체 신규 정의** (14 properties, ontology 가장 큰 갭 해결: SHACL shape는 있었으나 OWL class 부재) + 기존 PG `guide_usage_profiles` (1,038 rows) ontology backed + `guide_domain_profile.py` PG primary. Gate 3 PASS, `false_negative_rate -0.0189` 개선.
- **Phase G.3** (commit `8ddc2c7`) — `penalty:appliesTo/penaltyType/maxFine/maxPrisonYears` ontology 보강 + 신규 PG `penalty_rule_index` (**4,076 SR→PenaltyRule mappings**, kosha-instances.ttl → PG 자동 추출) + `hazard_rule_engine._load_penalty_index` PG primary. **penalty_accuracy +27.16%p ⭐, overall_accuracy +18.81%p ⭐** (TTL parse 우회 + 더 완전한 mapping).
- **Phase G.4** (commit `434f35f`) — 신규 PG view `she_patterns_reasoner_derived` (77 F.2 v3.1 link SHE 노출, read-only architectural layer) + Openllet `inferred=0` 근본 원인 분석 (law:modifies AsymmetricProperty + inverseOf 충돌 = FunInv 경고).
- **Tier 4 AsymmetricProperty 패치** (commit `5edae0b`) — `kosha-ontology-v2.owl` + `.formatted.ttl`에서 `law:modifies`의 `owl:AsymmetricProperty` 제거 + Fuseki rebuild + container recreate. **FunInv 경고 사라짐 + SPARQL 추론 작동 검증** (`hazard:FALL_FROM_HEIGHT rdfs:subClassOf+ ?super` → `owl:Thing` + `hazard:FALL`).
- **Tier 4 #4 Pellet reporting** (commit `1bacd44`) — `KoshaFusekiServer.java`에 `getDeductionsModel()` 명시 호출 + lazy materialization 안내 부연.
- **Tier 4 #2 AdministrativeFine** (commit `70d2862` 일부) — Decision Skip: `withAdministrativeFine: 0`은 design intent (RULE 조문은 OSHA 제38/39 위임으로 criminal-only). OSHA 제175조 admin은 별도 Pipe-A 확장 sprint. 문서: `docs/dev-notes/t4-administrative-fine-scope-decision.md`.
- **Tier 4 #1 77 SHE matcher 통합** (commit `70d2862` 일부) — 5 SHE batch 시도 → she_accuracy -7.07%p VETOED (~1.4%p/SHE), rollback 정상 작동 + utf-8 fix. 근본 원인: matcher의 broadness 처리 (promote만으로 해결 불가). 별도 sprint 이관. 문서: `docs/dev-notes/t4-77-she-matcher-integration-decision.md`.
- **Tier 4 #3 SWRL Pellet 실행기 통합** (commit `448a8d0`) ⭐ — 신규 `kosha-rules-r1-r3-swrl.ttl` (R-1 exemptedBy + R-3 HighSeverityPenalty, OWL/RDF SWRL serialization) + KoshaFusekiServer.java sources + docker rebuild. **SPARQL 검증**: R-1 `?s core:exemptedBy ?o` → **107 inferred**, R-3 `?s a penalty:HighSeverityPenalty` → **3,579 inferred** (severityScore ≥ 5와 100% 일치, swrlb:greaterThanOrEqual built-in 정상 평가).

**4-Layer 흐름 완전 입증** (Phase G + T4 후):
```
Vision LLM (T3.A enum) → normalizer → PG (G.1-3 materialized) → 답변
                                       ↑
       Fuseki + Pellet ← TTL ← Ontology TBox (G.1-3 patches) ← Mining (F.3.0/3.2)
                                                              + SWRL rules R-1/R-3 (T4 #3)
                                                              + SHACL shapes (T2.B)
```

main HEAD: `3502eff` (T4 #1 후속 + moellab 비교 후). origin/main 동기화 완료.

### T4 #1 후속 sprint + moellab 위험요소 비교 (2026-05-19)

**T4 #1 후속 sprint** (commits `a26c888` → main `1bfd6b8`) — 77 pending_review SHE matcher 통합의 별도 sprint 전 단계 1차 정리:
- 77 SHE manual review (사용자 1차 분류, single-file HTML UI 도구):
  - **approve 57 / modify 19 / defer 1 / reject 0** (사용자가 패턴 폐기할 만큼 비현실적인 것은 없다 판정)
  - modify 19 → 5개 테마 자동 분류 (PPE 과도 8 + 사진불가 3 + 좁은조건 4 + 비현실 3 + 도메인불일치 1)
- Step 2 approve 57 batch promote 재시도: **Batch 1 (5 SHE) → she_accuracy -10.17%p VETOED, rollback 자동**. 5회 audit history 모두 동일 패턴 (-7~-10%p) → **matcher 자체 로직 문제 입증**
- Step 3 patch proposal 자동 생성 (19/19 PG-only patch, ontology 영향 없음)
- 다음 sprint plan: [`she-matcher-broadness-refactor.md`](../workplans/she-matcher-broadness-refactor.md) — 7-day plan (broadness-aware ranking + PPE state weakening + `approved_derived` 신규 + SHACL shape + PG→TTL export)
- Runbook: [t4-77-she-manual-review-results.md](../dev-notes/t4-77-she-manual-review-results.md)

**moellab.info/ohs 위험요소 비교 분석** (commit `833dcd7` → main `3502eff`) — 우리 프로젝트의 초안과 dev server 비교:
- 비교 범위: GPT 직접 출력 `hazards[]` 만 (외부 시스템 부속 legal_reference / related_guides / checklist / resources 제외)
- 8개 사진 / **37 hazards 식별 모두 합리적** (false positive 없음, 자연어 카테고리 직관적: "끼임/협착", "전도/미끄럼", "추락" 등)
- `preventive_measures` 평균 3-4개 / hazard, 사진 context 반영
- **architecture pivot 후보 식별** ⭐:
  - Vision LLM HAZARD_DIRECT_SCHEMA → hazards[] 그대로 표시 (moellab 스타일)
  - hazard.name → catalog 529 codes 매핑 (T1.C alias 활용)
  - 우리 ontology reasoning으로 Guide 추천 (moellab title_match 한계 회피)
  - Guide procedure + GPT preventive 병기 (사용자 화면)
  - SHE matcher 회귀 부담 본질적 감소 (Step 2 -10.17%p 우회)
- 다음 sprint plan: `docs/workplans/hazard-direct-architecture-pivot.md` (TBD, 별도 plan)
- Runbook: [moellab-vs-devserver-comparison.md](../dev-notes/moellab-vs-devserver-comparison.md)

### Tier 1 재포함 + Tier 2 F.3 closing + Tier 3.A (2026-05-18 저녁)

- **Tier 1 재포함** (commit `93c49fe`): 직전 `b66fa36` commit이 T1.B npz 바이너리 + 마이그레이션 스크립트만 staged하고 T1.A/T1.C 코드 working tree만 잔존했던 누락 발견 + 재포함:
  - T1.A `promote_she_review.py` — `rollback_batch` `result.rowcount` + 사후 verification + `stuck_ids` 검출 (5 stuck SHE bug 재발 방지)
  - T1.B `auto_register_aliases.py` + `recover_catalog_mismatch.py` — numpy `load/save_embedding_cache` (~87% 크기 축소 적용)
  - T1.C `hazard_normalizer.py` step 4.5 `_log_alias_usage()` + `promote_aliases.load_meta_latest` 'used' action 집계 (`promote_aliases --auto` production-ready)
- **T2.A F.3.1 pyshacl reasoner shadow channel** (commit `93c49fe`): 신규 `pyshacl_shadow_validator.py` (offline batch CLI) + `shadow_reasoner.py` (serving runtime, lazy module cache, ~50μs/photo) + `analysis_pipeline.py` `_append_analysis_log`에 `reasoner_rejects` kwarg 추가. **2580 analysis_log rows → 859 reasoner_rejects** (62.8% processable rows). Gate 3 PASS.
- **T2.B F.3.4 KB compile + Fuseki reload** (commit `78886b3` + `ac98d4c`): 신규 `compile_kb_to_ttl.py` → `kb-candidates.ttl` (2200 → 2192 shapes after T2.D, sh:Info severity). `KoshaFusekiServer.java` sources array에 kb-candidates.ttl 추가. docker image rebuild (`docker-fuseki:latest` sha256 `08837972`). container `docker compose up -d --force-recreate fuseki` 완료. **SPARQL 검증**: `SELECT COUNT(?s) WHERE { ?s a sh:NodeShape }` → **2216 NodeShapes** (kb-candidates 2192 + serving 24). Fuseki Java v2 read-only blocker 해결 (rebuild + recreate 패턴).
- **T2.C F.3.5 drift detection + Makefile f3-* 통합** (commit `78886b3`): 신규 `f3_drift_check.py` (6 metric 추적, exit code 0/1/2). `Makefile` f3-help/shadow-validator/promote-candidates/compile-kb/drift-check/weekly-cycle targets. cron 권장: `0 2 * * 0 cd /path && make f3-weekly-cycle`.
- **T2.D 8 F.3.2 candidates 1-by-1 vetted promotion** (commit `ac98d4c` → main `325ad37`): 신규 `promote_f32_per_candidate.py` (1-by-1 + full replay + Gate 3 wrap + 자동 rollback). **8/8 candidate PASS** (예상 5-6 PASS 대비 100% 통과). 모든 F.3.2 axiom vetted 승격 (vetted_count 0 → 8). 1차 실행 시 cp949 unicode bug 발견 → 모든 ✓✗→— 를 ASCII로 교체 후 PYTHONIOENCODING=utf-8 + python -u 로 재실행 성공.
- **Tier 3.A Closed Vocab Schema Enum** (commit `606b91f` → main `b237e78`): `openai_client.py` `ONTOLOGY_OBSERVATION_SCHEMA.risk_feature_candidates.text`에 catalog 529 codes enum. `_load_catalog_codes()` lazy module-level load (12.6KB schema JSON, OpenAI strict mode 한도 내). Gate 3 PASS (delta noise 수준). **analysis_log normalizer_unknown_codes 76 → 4 (−94.7%)**. 잔존 4건 (THF, CO, MOBILE_EQUIPMENT, WAREHOUSE) — OpenAI strict mode enum의 edge-case 누락 (강제력 ~99.6%).

**효과 정리** (Layer 4 Module 4.4 closed loop 완성):
```
mining (F.3.0/3.2)   →   verify (F.3.3 Gate 3)   →   compile (T2.B compile_kb_to_ttl.py)
                                                     ↓
monitor (T2.C f3_drift_check.py)   ←   deploy (Fuseki container restart + SPARQL endpoint)
```

main HEAD: `b237e78` (Tier 3.A merge), 직전 `325ad37` (Tier 2 merge).

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

## 📦 신규 산출물 (2026-05-19 Phase G + T4 — origin/main push 완료)

**Phase G 신규 산출**:
- Ontology TBox 4 patches:
  - `ontology-team/06-reasoning/ontology/kosha-ontology-v3-incompat-patch.ttl` (G.1: `core:Incompatibility` class + 5 metadata properties)
  - `ontology-team/06-reasoning/ontology/kosha-ontology-v3-guide-profile-patch.ttl` (G.2: `guide:GuideUsageProfile` class + 14 properties + cardinality restrictions)
  - `ontology-team/06-reasoning/ontology/kosha-ontology-v3-penalty-relations-patch.ttl` (G.3: 4 relation/datatype properties)
  - `ontology-team/06-reasoning/ontology/kosha-rules-r1-r3-swrl.ttl` (T4 #3: R-1 exemptedBy + R-3 HighSeverityPenalty SWRL OWL serialization)
- Ontology TBox 1 수정: `kosha-ontology-v2.owl` + `.formatted.ttl` (`law:modifies`의 `owl:AsymmetricProperty` 제거, T4 fix)
- PG schema 3 신규:
  - `serving-team/07-materialization/pg-sync-scripts/schema_guide_domain_incompatibilities.sql`
  - `serving-team/07-materialization/pg-sync-scripts/schema_penalty_rule_index.sql`
  - `serving-team/07-materialization/pg-sync-scripts/schema_she_patterns_reasoner_derived.sql`
- PG import scripts 2 신규:
  - `serving-team/07-materialization/pg-sync-scripts/import_domain_incompatibilities_to_pg.py`
  - `serving-team/07-materialization/pg-sync-scripts/import_penalty_to_pg.py`
- Validation scripts 1 신규: `serving-team/07-materialization/validation-scripts/sample_query_equality.py`
- Bench script 1 신규: `serving-team/08-app/backend/scripts/bench_shadow_reasoner.py`
- PG ORM 3 신규 (`app/db/models.py`): `PgGuideDomainIncompatibility`, `PgPenaltyRoute`, `PgPenaltyRuleIndex`
- Backend code 4 수정 (PG primary):
  - `app/services/shadow_reasoner.py` (G.1, JSON fallback 유지)
  - `app/services/guide_domain_profile.py` (G.2)
  - `app/services/hazard_rule_engine.py` (G.3, `_load_penalty_index_from_pg()`)
  - `app/services/openai_client.py` (T3.A enum, 이전 sprint)
- Fuseki Java 수정: `KoshaFusekiServer.java` (kb-candidates + SWRL TTL sources 추가 + Pellet reporting 명시화)
- Makefile: `phase-g-help/phase-g1-schema/import/verify/phase-g-verify` targets
- Manual review 자산: `data-team/05-enrichment/runtime-artifacts/pending_review_she_for_manual_review.json` (77 SHE 8-axis + visual_triggers)

**신규 dev-notes (이번 세션, 7 runbooks/decisions)**:
- [phase-g.1-domain-incompatibilities-pg.md](../dev-notes/phase-g.1-domain-incompatibilities-pg.md)
- [phase-g.2-guide-usage-profiles-pg.md](../dev-notes/phase-g.2-guide-usage-profiles-pg.md)
- [phase-g.3-penalty-rule-index-pg.md](../dev-notes/phase-g.3-penalty-rule-index-pg.md)
- [phase-g.4-she-patterns-reasoner-derived.md](../dev-notes/phase-g.4-she-patterns-reasoner-derived.md)
- [t4-administrative-fine-scope-decision.md](../dev-notes/t4-administrative-fine-scope-decision.md)
- [t4-77-she-matcher-integration-decision.md](../dev-notes/t4-77-she-matcher-integration-decision.md)
- [t4-swrl-pellet-integration.md](../dev-notes/t4-swrl-pellet-integration.md)

전체 산출물 history: [../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)

---

## 📦 신규 산출물 (2026-05-19 T4 #1 후속 + moellab 비교 — origin/main push 완료)

**T4 #1 후속 산출 (commit `a26c888` → main `1bfd6b8`)**:
- 신규 dev-note: [t4-77-she-manual-review-results.md](../dev-notes/t4-77-she-manual-review-results.md)
- 신규 sprint plan: [she-matcher-broadness-refactor.md](../workplans/she-matcher-broadness-refactor.md) (7-day, hazard-direct pivot 후 보조 track으로 통합 또는 후행)
- 신규 script 2개:
  - `data-team/05-enrichment/llm-scripts/patch_she_visual_triggers.py` (Step 3 patch proposal 생성)
  - `data-team/05-enrichment/runtime-artifacts/she_review_ui.html` (94KB single-file 검토 UI)
- 신규 정본 자산:
  - `data-team/05-enrichment/runtime-artifacts/pending_review_she_REVIEWED.json` (77/77 사용자 검토 결과)
  - `data-team/05-enrichment/runtime-artifacts/pending_review_she_PATCH_PROPOSAL.json` (19/19 자동 patch)
- 수정: `data-team/05-enrichment/llm-scripts/promote_she_review.py` (`--only-from-review-json` 옵션)

**moellab 비교 산출 (commit `833dcd7` → main `3502eff`)**:
- 신규 dev-note: [moellab-vs-devserver-comparison.md](../dev-notes/moellab-vs-devserver-comparison.md)
- 보조 (git 미추적, 다음 세션 재현 자산): `.compare_moellab/*.json` (8개 사진 raw API 응답)
- 수정 1개: `.gitignore` (외부 raw 캡처 + manual review 보조 파일 + auto-gen logs 추가)

전체 산출물 history: [../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)

---

## 📦 신규 산출물 (2026-05-18 저녁 Tier 1-3.A — main에 push 완료)

**신규 파일**:
- `data-team/05-enrichment/llm-scripts/pyshacl_shadow_validator.py` (T2.A offline batch)
- `data-team/05-enrichment/llm-scripts/compile_kb_to_ttl.py` (T2.B)
- `data-team/05-enrichment/llm-scripts/f3_drift_check.py` (T2.C)
- `data-team/05-enrichment/llm-scripts/promote_f32_per_candidate.py` (T2.D)
- `data-team/05-enrichment/llm-scripts/_migrate_embedding_cache_to_npz.py` (T1.B 1회성)
- `serving-team/08-app/backend/app/services/shadow_reasoner.py` (T2.A serving runtime)
- `ontology-team/06-reasoning/ontology/kb-candidates.ttl` (T2.B output, 2192 SHACL shapes)
- `data-team/05-enrichment/runtime-artifacts/f32_per_candidate_promotion_results.json` (T2.D summary)
- `data-team/05-enrichment/runtime-artifacts/f3_drift_log.jsonl` (T2.C 시계열)
- `data-team/05-enrichment/runtime-artifacts/kb_candidates_compile_audit.json` (T2.B audit)

**수정 파일**:
- `serving-team/08-app/backend/app/services/analysis_pipeline.py` (T2.A: happy + skipped path 모두 `shadow_validate` + `reasoner_rejects` kwarg)
- `serving-team/08-app/backend/app/services/hazard_normalizer.py` (T1.C: step 4.5 `_log_alias_usage`)
- `serving-team/08-app/backend/app/integrations/openai_client.py` (T3.A: 529 codes enum + `_load_catalog_codes()`)
- `ontology-team/06-reasoning/ontology/docker/fuseki/src/main/java/kr/or/kosha/KoshaFusekiServer.java` (T2.B: sources array + kb-candidates.ttl)
- `data-team/05-enrichment/llm-scripts/promote_she_review.py` (T1.A: rollback verification + stuck_ids)
- `data-team/05-enrichment/llm-scripts/auto_register_aliases.py` (T1.B: npz load/save)
- `data-team/05-enrichment/llm-scripts/recover_catalog_mismatch.py` (T1.B: npz load/save)
- `data-team/05-enrichment/llm-scripts/promote_aliases.py` (T1.C: 'used' action 집계)
- `Makefile` (T2.A-D: f3-help/shadow-validator/promote-candidates/compile-kb/drift-check/weekly-cycle)

**신규 docs (이번 세션 저녁)**:
- [F.3-axiom-discovery.md](../dev-notes/F.3-axiom-discovery.md) — T2.A/B/C/D 통합 runbook
- [T3.A-closed-vocab-schema-enum.md](../dev-notes/T3.A-closed-vocab-schema-enum.md) — T3.A runbook
- [t2d-per-candidate-promotion-2026-05-18.md](t2d-per-candidate-promotion-2026-05-18.md) — T2.D 8/8 PASS 보고
- [t3a-closed-vocab-schema-enum-2026-05-18.md](t3a-closed-vocab-schema-enum-2026-05-18.md) — T3.A 76→4 분석

전체 산출물 history: [../workplans/llm-accelerated-ontology-engineering.md](../workplans/llm-accelerated-ontology-engineering.md)

---

## 📦 신규 산출물 (오늘 후반 — main에 push 완료, 2026-05-17~18 오전)

오늘 후반 (F.3 sprint + F.3.3 + sweep) commits + merge:
- `classify_reject_reasons.py` + 산출 jsonl/json + sample_100 (F.3.0)
- `analysis_pipeline.py` 수정 (Runtime 4번 hook 3 필드, A) + hot-fix (`raw_vision_features` list)
- `translate_incompat_industries.py` + KB 변환 (C)
- `mine_missing_axioms.py` + 8 candidate (B)
- `data-team/05-enrichment/runtime-artifacts/replay_post_f32.json` (F.3.3 replay)
- `docs/status/f30-reject-reason-classification-2026-05-17.md` (F.3.0 보고서)
- `docs/status/f33-gate3-regression-2026-05-17.md` (F.3.3 PASS 보고서)
- `docs/` 전반 14 docs sweep (`af26e13`): README/architecture/status/workplans/governance/backlog

## ⚠️ 다음 세션 시작 시 주의사항

1. **현재 작업 worktree**: `.claude/worktrees/trusting-chandrasekhar-7b2041/` (claude/trusting-chandrasekhar-7b2041 branch). **origin/main + PRIMARY 동기화 완료** (`f4f078a`, 2026-05-29 canonicalization sprint). PRIMARY(`C:/project/arch-bot`) = origin/main 동일 SHA. 정리 시 worktree 제거 가능 (모든 작업 커밋·푸시·배포됨).
2. **PG materialization runtime path**: shadow_reasoner (G.1) + guide_domain_profile (G.2) + hazard_rule_engine._load_penalty_index (G.3) 모두 **PG primary + JSON/TTL fallback** 패턴. PG cache 갱신 = backend restart 필요. PG row 변경 시 `_load_*_from_pg()` 캐시 reset 또는 service 재시작.
3. **Fuseki container 상태**: `kosha-fuseki` 신규 image (`docker-fuseki:latest`, 981,485 triples 로드, kb-candidates.ttl + kosha-rules-r1-r3-swrl.ttl 포함). SWRL R-1: 107 + R-3: 3,579 inferred triples 검증됨. 다음 docker compose 시 동일 image 자동 사용.
4. **Pellet inferred count log "0"은 정상**: `infModel.size()` lazy materialization quirk. 실제 추론은 SPARQL query 시 on-demand 실행 (검증 완료). 로그 메시지에 안내 포함.
2. **API 키**: `serving-team/08-app/backend/.env`에 OPENAI_API_KEY 설정됨. 정상 작동 확인 (T2.D 8회 replay 모두 성공)
3. **8 F.3.2 candidate axiom 모두 vetted 승격 완료** (T2.D 8/8 PASS). vetted_count 0 → 8. 잔여 candidate-only 진행 시 동일 `promote_f32_per_candidate.py --apply` 패턴.
4. **Fuseki container 새 image 적용 중**: `docker-fuseki:latest` sha256 `08837972` (kb-candidates.ttl 17,618 triples 로드, 총 981,409 triples). `docker compose up -d`에 동일 image 자동 사용. 다음 TTL 추가 시 동일 (Java sources 수정 + rebuild + recreate).
5. **T2.D 1차 cp949 unicode bug 처리됨**: `promote_f32_per_candidate.py` 모든 ✓✗→— → ASCII 교체. 재실행 시 `PYTHONIOENCODING=utf-8 python -u` 권장.
6. **T3.A 잔존 4 free-creates**: THF, CO, MOBILE_EQUIPMENT, WAREHOUSE — OpenAI strict mode enum의 edge-case (~99.6% 강제력, 0.4% 누락). 별도 분석 후보 (또는 normalizer step에서 hard reject 가능).
7. **편의점 KO unmapped** (이전 sprint에서 발견): `industry_ko_to_en_map.json`에 `편의점 → CONVENIENCE_STORE` 매핑 추가됨 (Quick Win Task 3). T2.D 후보 [6/8] 편의점×METAL_MACHINING가 vetted 통과 확인.
8. **A hook 항상 실행됨** (Quick Win Task 2 + T2.A): `_apply_llm_rerank`의 early-return 3 경로 모두 `_log_skipped_analysis` 호출 → analysis_log에 `mode=off_skipped_*` 기록. T2.A `reasoner_rejects` field도 happy + skipped path 모두 추가됨.
9. **stash@{0}**: `WIP on main: ca55ac6` (이전 세션 8 real-test-photo PNG/JPG untracked). 무관함, 보존

## 🛣️ 다음 작업 우선순위

### ✅ 완료: Phase G — PG 재물질화 (G.1-4, 2026-05-19)
- G.1: `guide_domain_incompatibilities` PG (2,016 rows, ontology `core:Incompatibility`)
- G.2: `guide_usage_profiles` PG + `guide:GuideUsageProfile` 신규 OWL class (ontology 가장 큰 갭 해결)
- G.3: `penalty_rule_index` PG (4,076 rules) — **penalty_accuracy +27.16%p ⭐**
- G.4: `she_patterns_reasoner_derived` view + Openllet root cause 분석
- Runbooks: `docs/dev-notes/phase-g.{1,2,3,4}-*.md`

### ✅ 완료: Tier 4 후속 (2026-05-19)
- AsymmetricProperty 패치 (Openllet SPARQL 추론 검증)
- T4 #4 Pellet reporting 명시화
- T4 #2 AdministrativeFine: Skip (design intent)
- T4 #1 77 SHE: 별도 sprint 이관
- T4 #3 SWRL Pellet 실행기 통합 (R-1: 107 + R-3: 3,579 inferred) ⭐
- Runbooks: `docs/dev-notes/t4-{administrative-fine,77-she-matcher,swrl-pellet}-*.md`

### ✅ 완료: Tier 1 재포함 (T1.A/B/C, 2026-05-18 저녁)
- T1.A promote_she_review rollback verification + stuck_ids 검출
- T1.B npz cache load/save (95MB → 12MB, 87% 축소)
- T1.C hazard_normalizer step 4.5 alias usage tracking + promote_aliases 'used' 집계

### ✅ 완료: Tier 2 F.3 closing (T2.A/B/C/D, 2026-05-18 저녁, Module 4.4 closed loop)
- T2.A pyshacl reasoner shadow channel (offline batch + serving runtime)
- T2.B KB compile to TTL + Fuseki Java edit + docker rebuild + container restart + **SPARQL 2216 NodeShapes 검증**
- T2.C drift detection + Makefile f3-* 통합
- T2.D 8/8 F.3.2 candidates vetted (예상 5-6 대비 100% 통과)
- Runbook: [../dev-notes/F.3-axiom-discovery.md](../dev-notes/F.3-axiom-discovery.md)
- Makefile: `make f3-help` 참고

### ✅ 완료: Tier 3.A Closed Vocab Schema Enum (2026-05-18 저녁)
- `ONTOLOGY_OBSERVATION_SCHEMA.risk_feature_candidates.text`에 catalog 529 codes enum
- **free-creates 76 → 4 (-94.7%)** (Hybrid Day 3 partial → 본격 schema-level enum)
- Gate 3 PASS (delta noise 수준)
- Runbook: [../dev-notes/T3.A-closed-vocab-schema-enum.md](../dev-notes/T3.A-closed-vocab-schema-enum.md)

### ✅ 완료: Phase F.1 — Vocabulary auto-registration (Day 1-7, 2026-05-18 오전)
- 5 vetted aliases (FALL_FROM_HEIGHT, FINGER_AMPUTATION 등) + 1 candidate
- 4-Gate closed loop: embedding + LLM verify + regression + asymmetric trust
- Runbook: [docs/dev-notes/F.1-auto-register-aliases.md](../dev-notes/F.1-auto-register-aliases.md)
- Makefile: `make f1-help` 참고

### ✅ 완료: Phase F.2 — Taxonomy Discovery (Day 1-7, 2026-05-18 오전)
- catalog v3.1 (404 codes, 3 axes) → **v3.3 (481 codes, 5 axes)**
- 신규 axis: ppe_state (50 codes), environmental (18 codes)
- 790 SHE OTHER → specific (Sonnet 4.6, Gate 3 PASS)
- 79 v3.1-link SHE (status=pending_review, 수동 승격 대기)
- Runbook: [../dev-notes/F.2-taxonomy-discovery.md](../dev-notes/F.2-taxonomy-discovery.md)
- Makefile: `make f2-help` 참고

### 다음 작업 우선순위 (T4 #1 후속 + moellab 비교 완료 후):

**1순위: hazard-direct architecture pivot** ⭐ (sprint plan 작성 완료, Phase 1 즉시 시작 가능):
- 📄 **Plan: [docs/workplans/hazard-direct-architecture-pivot.md](../workplans/hazard-direct-architecture-pivot.md)** (3주, 5 Phase × 평균 5일)
- 핵심 가설: Vision LLM이 위험요소(hazards) 자연어로 직접 출력 → 우리 ontology로 Guide 추천 → SHE matcher 의존도 본질 감소
- moellab(우리 초안)의 GPT 직접 hazard 식별이 8/8 사진 / 37/37 합리적 (Step 2 SHE matcher -10.17%p VETOED와 대조)
- Phase 1: HAZARD_DIRECT_SCHEMA + GPT prompt 갱신 (~3일)
- Phase 2: hazard.name → catalog 529 codes alias 매핑 (T1.C 확장 + Sonnet 4.6 seed, ~1주, ~$0.20)
- Phase 3: hazards-based Guide 추천 layer + A/B 검증 (parallel/primary/off mode, ~1주)
- Phase 4: 응답 schema 확장 + Frontend `RiskOverviewPanel`/`HazardGuideRelationsPanel` (~3일)
- Phase 5: Gate 3 통합 + 정본 문서 + Architectural debt 3가지 해소 (~3일)
- 결정 완료: seed = Sonnet 4.6 자동 + 사용자 vetted / SHE matcher refactor = 후행 별도 sprint

**2순위: SHE matcher broadness-aware refactor** (T4 #1 후속, 보조 track):
- [she-matcher-broadness-refactor.md](../workplans/she-matcher-broadness-refactor.md) (7-day plan)
- hazard-direct pivot의 Phase 3 보조 track으로 통합 또는 후행 (SHE matcher 의존도는 본질적으로 감소하지만 fallback으로 유지)

**3순위: OSHA admin penalty Pipe-A 확장** (T4 #2 후속, 4-6h):
- 제175조 administrative fines (6단계, 5천만원~300만원) 추출. `step1_extract_penalties.py` 확장. 결과 → penalty_rule_index에 sanction_type='AdministrativeFine' rows 추가.

**4순위: SWRL 확장 + 학계 작업**:
- ✅ **완료 (axiom-100% Sprint)**: R-4~R-30은 SWRL serialization 대신 **SHACL CONSTRUCT로 변환** (Pellet NEXPTIME 회피). `kosha-rules-r14-r30-shacl-construct.ttl` (12 rules) + `kosha-rules-k-general-shacl.ttl` (R-2/R-4 일반화, 53,378 pair). R-1/R-3만 SWRL native 유지.
- **8-photo real-test eval** (`make f1-eval`, ~$0.40 + 8분): Phase G + T4 효과 실제 사진 검증.

**3순위 (Tier 4 중장기, 1-3개월) — 별도 plan**:
- F.5 GraphRAG (Module 4.6, 2주)
- F.4 CQ Reverse + Photo persist (Module 4.5, 3-4주)
- Phase J OBO Foundry 등재 (1-3개월) — **사용자 명시: 나중에 별도 계획**
- Two-way CoT prompt 전환 (1일, +0.2 F1 기대)
- OOPS! Pitfall Scanner 통합 (2-3h)

**T3.A 잔존 4건** (THF/CO/MOBILE_EQUIPMENT/WAREHOUSE): 별도 sprint 또는 normalizer hard reject로 점진 보강.

**비채택** (도메인 부적합 — 2026-05-17 결정):
- **OntoGPT 통합** — F.1 alias mining에 자체 LLM verify(`mine_missing_axioms.py` 패턴)로 충분, 추가 가치 없음
- **OntoClean 메타-validation** — 170 atomic codes / 498 SHE patterns에 비용 비대칭. BFO+LKIF 62-class TBox 통합(Phase E-prep)에서만 유효했으며 이미 13→1 완료. F.1은 taxonomy 변경 없는 alias 등재 작업이므로 적용 영역 외

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
