# 온톨로지 구조 findings (top-down audit)

> 2026-05-31 top-down 구조 audit 산출. risk→haz/agent/ctx→she + guide/core/industry/bridge/actor 전수.
> **pen/law/app/sr은 별도 세션** 진행(미포함). 도구: `scripts/inspect_node.py`, `scripts/gen_catalog.py`(→CATALOG.md).
> 원칙: 생성물 손수정 금지(생성기 수정), 단일변수+게이트(compare_graphs/graph_diff·리즈너·verify-manifest/prefixes).

## 이미 수정 완료 (이 세션)
- ✅ **Fix A** (`ba11895`): canonical⊑axis 연결 — floating 480→0. (gen_facet_taxonomy.py)
- ✅ **Fix B** (`ac327a8`): haz:Hazard UPPER_SNAKE 레거시 개체 12 제거 (live 참조 0).
- ✅ 도구: inspect_node(`8670c6a`) · catalog(`d99da77`).
- ✅ **B1** (F6/F7): ctx 16 + agent:UnknownAgent 한글 라벨 보강. 신규 `shared/reference/facet-ko-labels.json` SSOT + gen_kosha22_vocab_patch.py @ko emit 확장. graph-diff +17 @ko only, 3축 label없음 0.
- ✅ **B2** (F14/F8): v2.owl에서 **8 haz alias 축-레벨 개체** 제거(Cut/Slip/Crush/Ergonomic/Burn/ColdExposure/FoodContamination/FallingObject — 코퍼스 haz: 참조 0, facet-taxonomy에 fine 클래스로 보존됨) + **core:Relation** owl:Class 선언(dangling 0). 부작용: 8 fine 클래스 개체라벨 상실→무명 fine 집단(fine-label 정책 커버).
- ⚠️ **B2 정정** (`<commit>`): core:Worker·guide:DocumentRequirement·guide:DomainTerm는 **코퍼스에서 live**(각 55/3435/7726회)인데 B2가 잘못 제거함 — ref-check가 **코퍼스 제외 + IRI형 grep**(prefixed `guide:` 놓침) 이중실수. graph-diff로 3개 복원(+9). **F13/F16은 오탐(live)으로 정정.** 교훈: 제거 전 코퍼스 포함 rdflib 재확인(catalog dead 메트릭에 caveat 추가).
- ✅ **B3a** (F2): `kosha-facet-axis-disjoint.ttl` 신규 — risk:RiskFeature 축 owl:AllDisjointClasses. manifest 등록(SRV/CON/MAT/FAC). ⚠️ **B3a 정정**(아래) — 최초 10축은 **haz:AccidentType⊥haz:Hazard 비일관**을 유발했고 lazy `prepare()` 거짓양성으로 미검출됨. B4 게이트가 적발 → **9축으로 축소**.
- ✅ **B4** (F10/F15): guide/core property **25개 domain/range 코퍼스-aware 보강**. 신규 `kosha-ontology-v4-domain-range-patch.ttl`(+36 triple = domain 25 + range 11) + 도출기 `scripts/derive_property_domain_range.py`(956K ABox 포함 full union **1,475,471 triple**에서 주어/목적어 rdf:type 전수집계). manifest 등록(SRV/CON/MAT/FAC). **안전성**: 25개 속성의 주어·목적어가 코퍼스에서 이미 **100% 해당 type(untyped 0)** → domain/range 추론은 기존 type 재확인 **NO-OP**, range 전부 guide:/sr:/law:(facet 축 아님). **단일변수 증명**: ① CON union(코퍼스 포함 998,064) +36 정확·기존중복 0. ② disjoint 충돌 검사를 patch 포함/제외 토글 시 **충돌 7개 동일·B4 술어 기여 0건** → B4 비유발 입증. catalog (e) 누락 59→34. **F17(bridge appliesTo/observedIn)·core:hasViolation·guide:sourceGuide/sourceSection·core:identifier/text/title 8개는 의도적 multi-signature/cross-cutting → 제외(by-design, 오탐).**
- ⚠️ **B3a 정정** (B4 Openllet 게이트가 적발): owl:Nothing 실쿼리로 **KB 비일관 확인** — `haz:Fall/StruckBy/Collapse/CaughtIn/ChemicalExposure/ErgonomicStrain/ElectricShock` 7 canonical 코드가 **haz:AccidentType이자 haz:Hazard**(같은 코드가 `sr:addressesAccidentType`→AccidentType, `sr:addressesHazard`→haz:Hazard 양쪽 목적어)인데 B3a가 둘을 disjoint 선언. haz:Hazard는 **하위 0의 near-empty 축(F4)**라 독립 축 아님 → `kosha-facet-axis-disjoint.ttl`에서 **haz:Hazard 제외(10→9축)**, 충돌 0·Openllet 일관 복구. 교훈: ① Openllet lazy prepare의 "Server Started"는 일관성 증거 **아님** — 실제 추론 쿼리(owl:Nothing) 필수. ② disjoint pre-check는 type/subClassOf뿐 아니라 **domain/range 주입까지** 포함해야(신규 `scripts/check_disjoint_consistency.py`). **F4(haz:Hazard↔AccidentType 통합)는 B5에서 정식 결정.**
- ✅ **B5/F4** (haz:Hazard **클래스 폐지**): 최초 (a) `AccidentType ⊑ Hazard`(`bb76d1f`)는 AccidentType만 2-level로 내려 **축 계층 비대칭**(타 축은 RiskFeature 직속)을 만들어 사용자가 반려 → **(c) haz:Hazard 클래스 자체를 삭제**. 근거: 4 Hazard-range 속성(sr/guide:addressesHazard·risk:correspondsToHazard·haz:hasHazard) 객체가 코퍼스 **100% AccidentType**(738/2484/8/8, agent/ctx 0)이라 Hazard은 빈·중복 클래스. **repoint**: 4 range + 3 allValuesFrom 제약(v4-restrictions) + R-11 SWRL classPredicate + demo fixture → `haz:AccidentType`, **haz:Hazard 선언 삭제(v2.owl)**. 서빙 무영향(serving-team .py 참조 0 확인). **결과**: AccidentType이 RiskFeature 직속 단일 부모로 복귀(균일 평탄), class 628→627, **haz:Hazard 잔여 참조 0**. 게이트: compare_graphs(전부 Hazard→AccidentType repoint·facet-disjoint 동치), check_disjoint 0, verify-manifest/prefixes, Openllet 재적재 일관.
- 🔍 **F5 / 중복label / 속성중복 triage** (코드 변경 0 — 정밀조사로 셋 다 단순 결함 아님 판명): **F5** ctx 5축은 개체 보유(5/10/17/6/11)+she:range 타깃이라 구조 결함 아님(she:has* used=0 = SHE/data 갭) → 재특성화. **중복label**(F19) 4쌍은 정당한 cross-axis homonym(의미충돌 아님). **속성중복**(F20) sr:addressesHazard~addressesAccidentType는 F4c로 range만 같아졌으나 **둘 다 활성**(서로 다른 룰 서브시스템)이라 통합은 별도 refactor. → top-down 백로그 정밀화(불필요 churn 방지). 잔여 선택지: 다축 ctx prune(SHE 설계)·sr 속성 통합(refactor)은 사용자 결정 대기.
- ✅ **catalog 결정화** (`2a5e74d`): gen_catalog 중복label IRI 정렬 — 재생성 시 timestamp 외 무변경(헛 diff 제거). top-down 작업 중 CATALOG.md 안정 최신 유지.
- ✅ **SHE ABox 온톨로지 통합** (F5 근본 해결): F5의 ctx 5축 dormant 진짜 원인 = **SHE 패턴 ABox(965 패턴 × 6축 맥락)가 데이터팀 `she-data/she-instances-v1.ttl`에만 있고 온톨로지 manifest 미등록** + 2026-04 생성이라 **KOSHA-22 이전 legacy 어휘**(haz:Crush/Cut/FallingObject/Slip/Ergonomic/FoodContamination 등). 신규 생성기 `scripts/gen_she_abox.py`가 그 소스를 **migrate_vocab_to_kosha22 결정적 치환으로 forward 마이그레이션**(롤백 아님 — 데이터 100% 재활용, 코드 155개 전수 resolve·gap 0) → `kosha-instances-she.ttl`(49,689 triple) 생성 + manifest 편입(SRV/CON/MAT/FAC). 게이트: verify-manifest(54)/prefixes, check_disjoint **0**. ⚠️ **Openllet 1차 재적재가 datatype 비일관 적발** — `she:triggerText`가 한국어 @ko(langString)인데 range가 xsd:string(1,623건) → v2.owl에서 **range xsd:string→rdfs:Literal 완화**(데이터가 정답, 스키마가 과엄격) 후 재적재 owl:Nothing 일관. **she:hasPPEState/AgentState/… 0→965, F5 5축 실채움.** ('온톨로지가 정본, data-team 산출물은 그에 맞춰 migrate' 원칙.) 교훈: disjoint뿐 아니라 **datatype range도 실추론 게이트가 잡음**(check_disjoint는 클래스 disjoint만 검사).
- ✅ **데이터 커버리지 detector** (`scripts/check_data_coverage.py`·`make data-coverage`): F5/SHE형 "**스키마는 있는데 ABox 데이터 0**" 갭을 **상시 자동 탐지** — 전체 ABox union 로드해 ① 인스턴스 0 클래스(punned/app runtime 제외) ② used=0 property를 검출, **app(runtime)·rule-head·facet-fine을 분리**해 우선 triage 제시. 베이스라인: 구조적 빈 클래스 87(industry 80 + Incompatibility/GuideUsageProfile 등 PG물질화 스키마) · dormant 52(app/rule-head 제외) · facet fine 339(prune 정책). orphan-TTL 스윕(manifest 밖 cashtoss TTL)과 함께 "데이터팀 미적재" 상시 그물. **원칙: 발견 증상을 그때마다 도구화**(B3a→check_disjoint, F5→이 detector).
- ✅ **facet fine 코드 한글 라벨 (F6/F7 완결, nolabel 339→0)**: facet-taxonomy의 fine 클래스 418개가 라벨 전무였음 → `gen_facet_taxonomy.py`가 **`risk_feature_catalog.json`의 한글 label을 읽어 `rdfs:label @ko` emit**(412) + catalog 미보유 6(ArcFlash/Corrosion/HeavyLifting/Posture/Repetitive/Slip)은 `facet-ko-labels.json` 보충(B1 SSOT fallback). 번역 아님 — **데이터팀 catalog의 한글 재활용**(코드 origin이 한국어 관찰). compare_graphs **-0/+418 전부 라벨**(다른 변경 0), verify-prefixes OK, **catalog nolabel 339→0**. 라벨=annotation이라 reasoner 게이트 불요. ('fine vocab prune 정책'은 라벨 부여로 keep 방향 — CI 미참조 fine은 별도 prune 검토 여지.)

## findings 목록

| # | 범주 | 이슈 | 심각 | batch |
|---|---|---|:--:|:--:|
| F1 | grounding | risk:RiskFeature=BFO:Quality인데 자식 mixed(agent=Object, ctx=Process/Occurrent). BFO 본문 미로드라 리즈너 미검출. 490 facet이 모순 grounding 상속 | 高 | B6 |
| F2 | disjoint | risk 축 서로소 **0** → **B3a로 9축 disjoint ✅**(haz:AccidentType/agent/ctx6/NLH). ⚠️ haz:Hazard는 AccidentType와 코드공유로 제외(정정·F4) | 中 | ✅(B3a+정정) |
| F3 | disjoint | agent·ctx canonical 서로소 **0** (haz만 12). 정책 불일치 | 中 | B3 |
| F4 | 빈 축 | haz:Hazard 빈·중복 클래스 → **B5로 클래스 폐지 ✅(c)**(4 range·3 allValuesFrom·SWRL → AccidentType repoint, v2.owl 선언 삭제). AccidentType RiskFeature 직속 복귀(균일). 잔여참조 0·Openllet 일관 | 中 | ✅(B5) |
| F5 | 빈 축 → **해결(SHE 통합)** | ctx 5 sub축은 개체 보유+she:has* range 타깃이나 used=0이었음 — 진짜 원인은 **SHE ABox(965패턴×6축)가 데이터팀에만 있고 온톨로지 미통합 + legacy 어휘**. **she-instances를 canonical forward 마이그레이션해 온톨로지 편입**(`kosha-instances-she.ttl`, gen_she_abox.py) → she:hasPPEState 등 **0→965, 5축 실채움**. triggerText datatype range도 완화 | 中 | ✅(SHE통합) |
| F6 | label | **ctx canonical 16/29 한글 label 없음** — ctx:ChemicalWork(ref 6160!)·ElectricalWork·Demolition 등 다용 | 中 | B1 |
| F7 | label | agent:UnknownAgent 무명 | 低 | B1 |
| F8 | alias | haz:AccidentType 개체 31 vs canonical class 23 → **8 alias**: Cut/Slip/Crush/Ergonomic(중복)+Burn/ColdExposure/FoodContamination(무명)+FallingObject(누락 정식유형?) | 中 | B2 |
| F9 | 배치 | she:VisualTrigger가 risk 아래 아닌 BFO-only standalone | 低 | B6 |
| F10 | dom/rng | guide 속성 25 누락 → **B4로 23 보강 ✅**(코퍼스 single-signature). sourceGuide/sourceSection 2는 5 content타입 공유 provenance라 의도적 무제약 | 中 | ✅(B4) |
| F11 | grounding | guide:ChecklistItem 이중 grounding(Quality+lkif:Norm) | 低 | B6 |
| F12 | grounding | guide:GuideUsageProfile 무 grounding(⊑ 없음) | 低 | B6 |
| F13 | ~~dead~~ **오탐** | ~~guide:DocumentRequirement·DomainTerm ref=0~~ → **코퍼스에서 3435/7726회 live**. B2 정정으로 복원. **유효 finding 아님.** | — | ✅정정 |
| F14 | **broken** | **core:Relation dangling** — core:Incompatibility ⊑ 선언 안 된 core:Relation(triple 0). 프로젝트 유일 dangling | 中 | B2 |
| F15 | dom/rng | core 속성 6 누락 → **B4로 2 보강 ✅**(coApplicable=SR↔SR, exemptedBy=NS↔NS). hasViolation·identifier/text/title 4는 multi-signature/cross-cutting 의도적 무제약 | 中 | ✅(B4) |
| F16 | ~~dead~~ **오탐** | ~~core:Worker ref=0~~ → **코퍼스에서 55회 live**(audit 코퍼스 제외 탓). B2 정정으로 복원. **유효 finding 아님.** | — | ✅정정 |
| F17 | ~~dom/rng~~ **오탐** | bridge appliesTo/observedIn은 **의도적 multi-signature**(observedIn: VO→Hazard/SR→Ctx; appliesTo: SR→Hazard/Equip/Finding). range 박으면 B3a 충돌. v4-bridge-patch 주석에 명시. **유효 finding 아님** | — | ✅정정 |
| F18 | label | industry 7건 — Industry_GENERAL `"general"@ko`(영문 오태깅) + 언더스코어 leak 6(`"자동차_정비소"@ko` 등). 라벨은 **생성물 kosha-disjoint-axioms.ttl**(build_disjoint_axioms.py)에 있고 upstream industry 라벨 소스(Layer 4)에서 옴 → **손수정 불가, upstream 소스 수정 필요(일부 data-team 세션 영역)**. (+명과학 등 의미 오타 수동검토) | 低 | B1→deferred |
| F19 | ~~중복 label~~ **비결함** | catalog (d) 4쌍(근로자 actor/core·기타·비상대응·정비)은 **정당한 cross-axis/type homonym** — 각자 다른 namespace·축에서 정확(@en도 동일 = 같은 개념명의 다른 축 적용). 근로자만 B2의 의도적 class/individual 분리. **의미 충돌 아님**. 라벨 변경은 user-facing+생성물(industry upstream)이라 비권장 | — | 조사완료 |
| F20 | ~~dup property~~ **해결(hard merge)** | (F4c 후행) `sr:addressesHazard`가 `sr:addressesAccidentType`와 range 동일(AccidentType) 동의어 + 데이터 두 술어 분산(addressesHazard 738트리플/626행, addressesAccidentType 284행; both 284·H_only **342**·A_only 0). **객체는 양쪽 모두 canonical 사고유형(fine 0)**인데 addressesHazard만 6종(ChemicalExposure/ElectricShock/FireInjury/OtherAccident/OxygenDeficiency/TempExtremeContact) 보유 → "버리기"는 342 SR 손실이라 **union 흡수 hard merge**. 적용: ABox 바이트 토큰치환(union, **-738/+417 단일변수**)·생성기(export_owl L271·gen_canonical_code_shape)·TBox 선언삭제·restriction onProperty·SWRL R-4·SHACL K-R4/R-15/16/30·demo·CATALOG. Openllet 일관 유지 | 中 | ✅(F20 merge) |
| F21 | broken (F4c 잔재) | `kosha-rules-r14-r30-shacl-construct.ttl` R-15/R-16 CONSTRUCT 본문에 `?hazd a haz:Hazard`(L66·84) 잔존 — haz:Hazard는 F4c 폐지 클래스라 매칭 0 → bridge:appliesTo/observedIn 룰 dead. 본문이 `haz:hasHazard`(RiskFeature→Hazard) 사용하나 현 모델은 risk:correspondsToHazard→AccidentType. **F4c 미완**(F20 작업 중 발견, 단일변수 위해 미수정). haz:Hazard→AccidentType repoint + hasHazard 경로 재검토 필요 | 中 | 신규(F4c 후속) |
| F22 | granularity | **fine 코드 보존+활용(graded matching)** — 서빙이 fine→canonical fold(`to_canonical`)로 변별 손실 → Vision이 fine 인식해도 엉뚱한 CI/Guide 추천. **WC-C ✅**: `query_guide_for_facets`에 GF(`guide_entity_feature_candidates`) 기반 fine work_context **fine-first 결정적**(`FINE_GRADED_MATCH` flag, WHERE=canonical 유지) — forklift 검증 **197/197 recall 불변·43 fine guide 결정적 상위**(무회귀 off=동일). ⚠️ **경험 발견**: accident_type/agent **엔티티엔 진짜 fine 태그 없음**(SR/CI/GF에 CRUSH/CUT 등 legacy 별칭만; FALL_FROM_HEIGHT 보유 guide=0) → 두 축 graded match는 **entity fine-tagging enrichment 선행 필요**(GF work_context 생성 방식을 accident/agent로 확장). work_context만 GF에 fine 51종(FORKLIFT/HEAVY_LIFTING/WELDING…). 잔여: CI fine·온톨로지 fine wc 물질화(WC-A/B)·synthetic full eval·flag ON 결정 | 中 | WC진행 |

별도: ~~**fine 코드 ~330** 한글 label 없음~~ → **✅ 라벨 완료**(catalog 재활용, nolabel 339→0). CI 미참조 fine의 prune은 별도 여지(라벨 부여로 keep 방향).
별도2(F5 후행): **ctx 5 sub축의 she:has* 속성·비-canonical 개체(~49)가 dormant**(used=0) — SHE가 flat WorkContext만 써서. 다축 ctx 모델 prune vs 유지는 **SHE/data 설계 결정**(별도).

## batch-fix 계획 (additive 먼저, top grounding 마지막)

| 묶음 | 내용 | 위험 | 상태 |
|---|---|:--:|:--:|
| **B1** | label 보강 — F6/F7 ✅완료, F18(industry)/fine 정책 잔여 | 低 | F6·F7 ✅ |
| **B2** | broken/dead 정리 — F14 dangling·F16/F13 dead·F8 alias | 低~中 | ✅ |
| **B3** | disjointness — **F2 축간 ✅(B3a, 9축 — haz:Hazard 정정 제외)**, F3 agent/ctx 잔여(B3b) | 中 | B3a ✅ |
| **B4** | property domain/range — F10/F15 ✅(25 보강), F17 오탐(by-design) | 中 | ✅ |
| **B5** | 빈 축 — **F4 haz:Hazard 폐지 ✅(c)**, **F5 ctx 5축 조사완료**(비결함·she:dormant=data scope) | 中 | ✅ |
| **B6** | BFO grounding 재설계 — F1/F11/F12/F9 (top, 맨 마지막) | 高 | 대기 |

## 확인된 양호
- floating 0 ✅(Fix A) · haz canonical label 100% · thin/dead canonical 0 ✅(Fix B)
- agent/ctx canonical 축 연결 ✅ · dangling 1개뿐(core:Relation) · industry 80중 73 label 정상
