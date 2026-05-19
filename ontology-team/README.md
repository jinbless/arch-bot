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

## 최근 변경 (2026-05-19, origin/main `448a8d0`)

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
