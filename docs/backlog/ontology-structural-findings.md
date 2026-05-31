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
- ✅ **B5/F4** (haz:Hazard **클래스 폐지**): 최초 (a) `AccidentType ⊑ Hazard`(`bb76d1f`)는 AccidentType만 2-level로 내려 **축 계층 비대칭**(타 축은 RiskFeature 직속)을 만들어 사용자가 반려 → **(c) haz:Hazard 클래스 자체를 삭제**. 근거: 4 Hazard-range 속성(sr/guide:addressesHazard·risk:correspondsToHazard·haz:hasHazard) 객체가 코퍼스 **100% AccidentType**(738/2484/8/8, agent/ctx 0)이라 Hazard은 빈·중복 클래스. **repoint**: 4 range + 3 allValuesFrom 제약(v4-restrictions) + R-11 SWRL classPredicate + demo fixture → `haz:AccidentType`, **haz:Hazard 선언 삭제(v2.owl)**. 서빙 무영향(serving-team .py 참조 0 확인). **결과**: AccidentType이 RiskFeature 직속 단일 부모로 복귀(균일 평탄), class 628→627, **haz:Hazard 잔여 참조 0**. 게이트: compare_graphs(전부 Hazard→AccidentType repoint·facet-disjoint 동치), check_disjoint 0, verify-manifest/prefixes, Openllet 재적재 일관. **F5(ctx 5 빈 sub축) 잔여.**

## findings 목록

| # | 범주 | 이슈 | 심각 | batch |
|---|---|---|:--:|:--:|
| F1 | grounding | risk:RiskFeature=BFO:Quality인데 자식 mixed(agent=Object, ctx=Process/Occurrent). BFO 본문 미로드라 리즈너 미검출. 490 facet이 모순 grounding 상속 | 高 | B6 |
| F2 | disjoint | risk 축 서로소 **0** → **B3a로 9축 disjoint ✅**(haz:AccidentType/agent/ctx6/NLH). ⚠️ haz:Hazard는 AccidentType와 코드공유로 제외(정정·F4) | 中 | ✅(B3a+정정) |
| F3 | disjoint | agent·ctx canonical 서로소 **0** (haz만 12). 정책 불일치 | 中 | B3 |
| F4 | 빈 축 | haz:Hazard 빈·중복 클래스 → **B5로 클래스 폐지 ✅(c)**(4 range·3 allValuesFrom·SWRL → AccidentType repoint, v2.owl 선언 삭제). AccidentType RiskFeature 직속 복귀(균일). 잔여참조 0·Openllet 일관 | 中 | ✅(B5) |
| F5 | 빈 축 | ctx 6 sub축 중 **5개 비어있음**(AgentState/EnvFactor/PPEState/TemporalStage/WorkActivity). 29 canonical 전부 WorkContext 아래 | 中 | B5 |
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

별도: **fine 코드 ~330**(haz 150·ctx 109·agent 72) 한글 label 없음 + CI 미참조 = future 어휘 vs prune 정책 결정 필요(B1/B5 연계).

## batch-fix 계획 (additive 먼저, top grounding 마지막)

| 묶음 | 내용 | 위험 | 상태 |
|---|---|:--:|:--:|
| **B1** | label 보강 — F6/F7 ✅완료, F18(industry)/fine 정책 잔여 | 低 | F6·F7 ✅ |
| **B2** | broken/dead 정리 — F14 dangling·F16/F13 dead·F8 alias | 低~中 | ✅ |
| **B3** | disjointness — **F2 축간 ✅(B3a, 9축 — haz:Hazard 정정 제외)**, F3 agent/ctx 잔여(B3b) | 中 | B3a ✅ |
| **B4** | property domain/range — F10/F15 ✅(25 보강), F17 오탐(by-design) | 中 | ✅ |
| **B5** | 빈 축 — **F4 haz:Hazard 클래스 폐지 ✅(c)**, F5 ctx 5 sub축 잔여 | 中 | F4 ✅ |
| **B6** | BFO grounding 재설계 — F1/F11/F12/F9 (top, 맨 마지막) | 高 | 대기 |

## 확인된 양호
- floating 0 ✅(Fix A) · haz canonical label 100% · thin/dead canonical 0 ✅(Fix B)
- agent/ctx canonical 축 연결 ✅ · dangling 1개뿐(core:Relation) · industry 80중 73 label 정상
