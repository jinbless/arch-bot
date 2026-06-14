# Ontology Team

온톨로지팀은 6단계(OWL/SHACL/리즈너)를 담당한다. **향후 public `kosha-ontology-reasoning` repo로 분리되어 오픈소스 공개 예정** (Framework + KOSHA TBox + ABox 모두).

## 단계

| 단계 | 디렉토리 | 역할 |
|---|---|---|
| 6. Reasoning | [06-reasoning/](06-reasoning/) | 공리/OWL/SHACL → 온톨로지 리즈너로 문제 발견·수정 |

## 책임

- 데이터팀이 만든 TBox/ABox를 받아 **공리 적용 + OWL DL 추론** (Openllet 등)
- SHACL shapes로 일관성 검증
- 부정확한 매핑/관계를 찾아내고, 6번 완성 시 5번(LLM enrichment)을 자연스럽게 대체
- 시각화 도구 ([06-reasoning/visualization/](06-reasoning/visualization/)) 운영

## 최근 변경 (2026-06-14) — Track A ② 추론 수직 슬라이스 (reasoner→PG)

리즈너 도출 관계를 **Fuseki 요청 경로에서 빼고** emit→TTL→PG로 물질화. R-1/R-3는 더 이상 Fuseki Pellet on-demand가 아니라 PG-served다.

- 신규 emit 스크립트 `scripts/emit_inferred_relations.py` (`--mode strict|chapter|hazard`) → 신규 3 TTL:
  - `kosha-inferred-relations.ttl` — **R-1 exemptedBy 107** (strict DL, NS→exempt-NS, SR별 서빙; 95 distinct SR)
  - `kosha-coapplicable-chapter.ttl` — **K-R2 coApplicable** same-Chapter relaxation, **16,429 distinct pair** (양방향 → 32,858 row)
  - `kosha-dependson-hazard.ttl` — **K-R4 dependsOn** same-Hazard relaxation, **35,165 distinct pair** (양방향 → 70,330 row)
- **R-2 strict coApplicable = 0** (SR↔Article 1:1). rule_id로 strict R-1 vs relaxed K-R2/K-R4 구분.
- 서빙은 신규 PG table `sr_inferred_relations` (총 **103,295 row**)을 읽는다. R-3 HighSeverityPenalty(3,579)는 `sr_inferred_relations`에 저장하지 않고 `penalty_rule_index.severity_score>=5` SQL로 재현.
- PROV run-tracking table `materialization_runs` (run_id, rule_set, ontology_commit=git rev, source_ttl_sha256=content-hash, triple_count, status).
- 신규 Makefile target: `reasoning-emit{,-chapter,-hazard}`, `phase-g5{,b,c}-schema/import/verify`.
- Gate: f1-regression all-metric delta **0.0000** (analysis hot-path 불변), latency PASS, verify-baseline PASS, phase-g5/g5b/g5c-verify PASS. (commit `87d9e63`/`7c50304`/`e6140bb`, main push 완료)

⚠️ 아래 2026-05-19 Pellet/SWRL 표(R-1 107 / R-3 3,579)와 2026-05-28 `kosha-rules-k-general-shacl.ttl` 53,378-pair 노트는 **on-demand 시점 수치**다 → 현재 R-1은 PG-served, same-Hazard/same-Chapter는 K-R4 35,165 / K-R2 16,429 pair로 PG 물질화됨 (아래 각 절 정정 노트 참조).

### A4/A5 오픈소스 거버넌스 산출물 (2026-06-14)

오픈소스 공개 목표(본 README 하단)를 뒷받침하는 메타데이터/SKOS 산출물:
- `kosha-ontology-metadata.ttl` — 릴리스 버전 **2.0.0** (`owl:versionIRI .../ontology/2.0.0`, `owl:versionInfo "2.0.0"`, `kosha-ontology-v2.owl` 계보). VoID (전체 일관성 assembly scope): `void:triples` **1,049,862**, `void:classes` **625** (named owl:Class, facet fine class 포함; core 개념 TBox ~62), `void:properties` **164** (ObjectProperty 119 + DatatypeProperty 45).
- `kosha-codes-skos.ttl` (`gen_skos_scheme.py`, Makefile `gen-skos`) — 축별 3 SKOS ConceptScheme(accident-type/hazardous-agent/work-context), **504 concept / 2,659 triple**. `skos:broader` 418(same-axis rollup→canonical), `skos:relatedMatch` 21(cross-axis agent→accident-type), `rdfs:seeAlso` 62(canonical→OWL haz:/agent:/ctx: class). punning/위계 오선언 회피 위해 broadMatch/exactMatch 대신 relatedMatch + seeAlso 사용.
- A4 dual license: `LICENSE` (Apache-2.0, code) + `LICENSE-ontology.md` (CC-BY-4.0, ontology/data) + `CITATION.cff` (CFF 1.2.0, version 2.0.0).
- Namespace는 여전히 `cashtoss.info`다 (`w3id.org/ohs-kr` 이전은 향후 step A2).

## 최근 변경 (2026-05-31, origin/main `678a7d1`)

**facet 구조 top-down audit + 구조 수정** (정본: [docs/backlog/ontology-structural-findings.md](../docs/backlog/ontology-structural-findings.md)).

신규 진단 도구(재사용):
- `scripts/inspect_node.py` — 한 IRI의 전체 triple(주어/목적어 양방향) + **출처 파일** 카드. `--list <prefix>` scope 개요.
- `scripts/gen_catalog.py` → `06-reasoning/ontology/CATALOG.md` — 전체 class 계층 + property + 자동 이상징후(floating/label/dead/dup/dom-rng/punning). ⚠️ ref/dead는 대용량 코퍼스 제외 → guide/core/app 클래스는 코퍼스 포함 재확인 필수.

구조 수정:
- **Fix A** `ba11895`: `gen_facet_taxonomy.py`에 canonical⊑axis emit → **floating 480→0**(facet이 risk:RiskFeature까지 연결).
- **Fix B** `ac327a8`: haz:Hazard UPPER_SNAKE 레거시 개체 12 제거(클래스는 property range로 유지).
- **B1** `1f32a61`: ctx 16+agent 한글 라벨 — 신규 `shared/reference/facet-ko-labels.json` SSOT.
- **B2+정정** `b81436a`/`678a7d1`: haz alias 축-레벨 개체 8 제거 + `core:Relation` 선언(dangling 0); 오제거 3 복원(core:Worker·guide:DocumentRequirement/DomainTerm = 코퍼스 live — 제거 전 코퍼스 확인 교훈).
- **B3a** `0a82546`: `kosha-facet-axis-disjoint.ttl` — risk:RiskFeature 10축 owl:AllDisjointClasses.

남은: B3b(저가치)/B4 domain-range/B5 빈 축/B6 BFO grounding (findings 문서).

## 이전 변경 (2026-05-28, origin/main `4aa3cca`)

**axiom-100% Sprint (Phase A~K) + guide-accuracy Sprint (P0~P3)**.

axiom-100% — v4 TBox 패치 9종 신규:
- `kosha-ontology-v4-{deps,alethic,bridge,deontic,violation,penalty-extra,restrictions,hazard-direct,asymmetric}-patch.ttl`
- 핵심: owl:Restriction **35** (allValuesFrom, ABox-safe), `law:modifiesAsymmetric` owl:AsymmetricProperty **1** (inverseOf 충돌 회피 위해 별도 property), `risk:NaturalLanguageHazardCategory` **21**.

SWRL → SHACL CONSTRUCT 전환 ⭐ (Pellet NEXPTIME 회피):
- R-14~R-30 SWRL 12개 조합이 Pellet 무한 재시작(NEXPTIME) 유발 → `kosha-rules-r14-r30-shacl-construct.ttl` (12 sh:rule CONSTRUCT)로 변환. KoshaFusekiServer.java sources에서 R-14~R-30 SWRL ttl **4개 주석 처리** (R-1/R-3만 native).
- `kosha-rules-k-general-shacl.ttl`: 같은 Hazard → `core:dependsOn` 36,949 + 같은 Chapter → `core:coApplicable` 16,429 = **53,378 pair** (on-demand materialization, gitignore).
  - ⚠️ **2026-06-14 정정**: 이 on-demand SHACL 수치는 이후 emit→PG로 물질화되며 갱신됨 — same-Hazard dependsOn은 **K-R4 35,165 pair**(36,949와 다른 별도 집계), same-Chapter coApplicable 16,429는 더 이상 "미적재/gitignore"가 아니라 **K-R2로 PG 물질화**. (위 2026-06-14 절 참조)
- 총 sh:NodeShape **1,964** (kb-candidates 2,192 SHACL는 별도 파일, parse 합산 시).

guide-accuracy — Guide 직접 위험 매핑:
- `kosha-ontology-v4-guide-hazard-patch.ttl`: `guide:addressesHazard` / `guideAddressesAgent` / `guideAppliesToContext` + `ciGuideFrequency` / `isBoilerplate`.
- `kosha-instances-guide-hazard.ttl`: PG `guide_entity_feature_candidates(entity_type='GUIDE')` → ABox export (**659 Guide, 2,115 triple**).
- "온톨로지가 사실 보유, 서비스 랭킹은 런타임" 원칙 유지.

검증: `scripts/verify_axiom_100pct.py` (5-step, Overall OK). Runbook: [docs/workplans/ontology-axiom-100pct.md](../docs/workplans/ontology-axiom-100pct.md), [docs/dev-notes/guide-recommendation-accuracy.md](../docs/dev-notes/guide-recommendation-accuracy.md).

## 이전 변경 (2026-05-19, origin/main `448a8d0`)

**Phase G + Tier 4 후속 — ontology TBox 본격 보강 + Pellet/SWRL native 실행 검증**.

신규 ontology TBox patches (4 TTL):
- `kosha-ontology-v3-incompat-patch.ttl` (G.1): `core:Incompatibility` class + 5 metadata properties (n-ary relation)
- `kosha-ontology-v3-guide-profile-patch.ttl` (G.2): `guide:GuideUsageProfile` class + 14 properties **(ontology 가장 큰 갭 해결 — 기존 SHACL shape 있었으나 OWL class 부재)**
- `kosha-ontology-v3-penalty-relations-patch.ttl` (G.3): `penalty:appliesTo/penaltyType/maxFine/maxPrisonYears` (4 relation/datatype properties)
- `kosha-rules-r1-r3-swrl.ttl` (T4 #3) ⭐: R-1 exemptedBy + R-3 HighSeverityPenalty (OWL/RDF SWRL serialization)

수정 (2):
- `kosha-ontology-v2.owl` + `.formatted.ttl`: `law:modifies`의 `owl:AsymmetricProperty` 제거 (Tier 4 fix, `5edae0b`) → Openllet FunInv 경고 해소 + SPARQL 추론 정상화

Fuseki container 변경:
- KoshaFusekiServer.java sources array에 kb-candidates.ttl + kosha-rules-r1-r3-swrl.ttl 추가
- Pellet `getDeductionsModel()` 명시 호출 + lazy materialization 안내 (T4 #4)
- 로드 triples: 963,791 → 981,485 (+17,694 from kb-candidates 17,618 + SWRL 76)

**Pellet/SWRL 실행 검증** (SPARQL count, 2026-05-19):

| Rule | 추론 결과 | Sanity check |
|---|---|---|
| R-1 exemptedBy | **107 inferred triples** | NormStatement modifies + Exemption modality 매칭 |
| R-3 HighSeverityPenalty | **3,579 inferred triples** | severityScore >= 5 count도 **3,579** (Pellet swrlb:greaterThanOrEqual 100% 정확) |

→ Pellet/Openllet OWL DL + SWRL native 추론 입증.

> ⚠️ **2026-06-14 정정**: 위 R-1/R-3는 더 이상 Fuseki Pellet on-demand가 아니라 PG-served다 — R-1은 `sr_inferred_relations`(107 row), R-3는 `penalty_rule_index.severity_score>=5` SQL로 재현. (상단 2026-06-14 절 참조)

운영 가이드:
- 신규 TTL 추가 시: KoshaFusekiServer.java sources array 수정 → docker rebuild → container recreate (10분)
- Pellet inferred count log "0"은 정상 (lazy materialization). 실제 추론은 SPARQL query 시 on-demand 실행
- SWRL native 추론 (R-1/R-3 패턴) 후속 sprint: R-4~R-30 일괄 변환

## 이전 변경 (2026-05-18 저녁, main `b237e78`)

신규 ontology file:
- **`06-reasoning/ontology/kb-candidates.ttl`** (T2.B) — F.3.2 candidate axiom의 SHACL NodeShape, sh:Info severity (shadow validation, 실제 reject 안 함). 2,192 NodeShapes (industry × industry incompatibility 페어), 80 industries, 17,778 triples. `data-team/05-enrichment/llm-scripts/compile_kb_to_ttl.py` 에서 자동 생성.

Fuseki container 변경:
- **`KoshaFusekiServer.java`** sources array에 `/kb-candidates.ttl` 추가 (Java code edit, T2.B sprint)
- Docker image rebuild: `docker-fuseki:latest` sha256 `08837972`
- Container recreate: `docker compose up -d --force-recreate fuseki`
- 로드 triples 변화: 963,791 (이전) → **981,409** (+17,618 from kb-candidates)
- SPARQL 검증: `SELECT (COUNT(?s) AS ?n) WHERE { ?s a sh:NodeShape }` → **2,216 NodeShapes** (kb-candidates 2,192 + serving-validation-shapes-v3 24)

운영 가이드:
- 신규 TTL 추가 시 동일 패턴 (Java sources 수정 → docker rebuild → container recreate)
- Java v2 read-only blocker (allowUpdate=false) 해결됨 (rebuild 기반 적용)
- Openllet 추론 적용 (REASONER_MODE=openllet), kb-candidates는 추가 inferred triples 0 (현재 SHACL shapes만, instance 매칭은 SHACL validator 에서)

향후 정리 후보:
- vetted 8 F.3.2 axioms는 `kosha-disjoint-axioms.ttl` (OWL DisjointClasses hard reject)에 자동 포함됨 (`build_disjoint_axioms.py` 재실행 시)
- Phase G PG materialization 후 SHACL shapes는 PG에 미러 가능 (Tier 3 후속 3C)

## 다른 팀과의 인터페이스

- **← 데이터팀 (4단계)**: [data-team/04-ontology-export/](../data-team/04-ontology-export/)가 export한 TBox/ABox TTL을 입력으로 받음
- **→ 서빙팀 (7단계)**: 보정된 TBox/ABox를 [serving-team/07-materialization/](../serving-team/07-materialization/)이 PG로 재물질화

## 오픈소스 공개 범위

| 항목 | 공개 |
|---|---|
| Framework (Reasoner runner, SHACL shapes, OWL/SWRL 패턴) | ✓ |
| KOSHA TBox (클래스/속성 정의) | ✓ |
| KOSHA ABox (실제 SR/CI 인스턴스) | ✓ |

다른 산업안전 도메인 ontology 엔지니어가 reference로 활용 가능. 자세한 공개 절차는 [docs/architecture/open-source-readiness.md](../docs/architecture/open-source-readiness.md).

## 향후 repo 분리 계획

[docs/architecture/repo-split-plan.md](../docs/architecture/repo-split-plan.md) 참조.
