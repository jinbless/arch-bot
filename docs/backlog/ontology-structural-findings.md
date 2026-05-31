# 온톨로지 구조 findings (top-down audit)

> 2026-05-31 top-down 구조 audit 산출. risk→haz/agent/ctx→she + guide/core/industry/bridge/actor 전수.
> **pen/law/app/sr은 별도 세션** 진행(미포함). 도구: `scripts/inspect_node.py`, `scripts/gen_catalog.py`(→CATALOG.md).
> 원칙: 생성물 손수정 금지(생성기 수정), 단일변수+게이트(compare_graphs/graph_diff·리즈너·verify-manifest/prefixes).

## 이미 수정 완료 (이 세션)
- ✅ **Fix A** (`ba11895`): canonical⊑axis 연결 — floating 480→0. (gen_facet_taxonomy.py)
- ✅ **Fix B** (`ac327a8`): haz:Hazard UPPER_SNAKE 레거시 개체 12 제거 (live 참조 0).
- ✅ 도구: inspect_node(`8670c6a`) · catalog(`d99da77`).
- ✅ **B1** (F6/F7): ctx 16 + agent:UnknownAgent 한글 라벨 보강. 신규 `shared/reference/facet-ko-labels.json` SSOT + gen_kosha22_vocab_patch.py @ko emit 확장. graph-diff +17 @ko only, 3축 label없음 0.
- ✅ **B2** (F14/F8/F13/F16): v2.owl에서 11 제거(8 haz alias 축-레벨 개체+core:Worker+guide:DocumentRequirement/DomainTerm, 전부 ref=0) + core:Relation owl:Class 선언(dangling 0). graph-diff −36(11×triple) +2(Relation). **주의**: 8 alias는 facet-taxonomy에 fine 클래스(haz:Cut⊑CutLaceration, haz:FallingObject⊑StruckBy 등)로 보존됨 — 제거된 건 중복 축-레벨 개체뿐. 부작용: 이 8 fine 클래스가 개체 라벨을 잃어 무명 fine 집단 합류(fine-label 정책에서 커버).
- ✅ **B3a** (F2): `kosha-facet-axis-disjoint.ttl` 신규 — risk:RiskFeature 10축 owl:AllDisjointClasses. manifest 등록(SRV/CON/MAT/FAC). pre-check 0충돌 → Fuseki Openllet 재적재 healthy(KB 일관성 OK, 비일관시 prepare throw). ABox 충돌 0(facet은 property-linked).

## findings 목록

| # | 범주 | 이슈 | 심각 | batch |
|---|---|---|:--:|:--:|
| F1 | grounding | risk:RiskFeature=BFO:Quality인데 자식 mixed(agent=Object, ctx=Process/Occurrent). BFO 본문 미로드라 리즈너 미검출. 490 facet이 모순 grounding 상속 | 高 | B6 |
| F2 | disjoint | risk 3축(+sub) 45쌍 중 서로소 선언 **0**. accident≠agent≠ctx 미보장 | 中 | B3 |
| F3 | disjoint | agent·ctx canonical 서로소 **0** (haz만 12). 정책 불일치 | 中 | B3 |
| F4 | 빈 축 | haz:Hazard: Fix B 후 canonical **0=빈 축**, property range로만 ref 9. AccidentType와 통합 or 목적 재정의 | 中 | B5 |
| F5 | 빈 축 | ctx 6 sub축 중 **5개 비어있음**(AgentState/EnvFactor/PPEState/TemporalStage/WorkActivity). 29 canonical 전부 WorkContext 아래 | 中 | B5 |
| F6 | label | **ctx canonical 16/29 한글 label 없음** — ctx:ChemicalWork(ref 6160!)·ElectricalWork·Demolition 등 다용 | 中 | B1 |
| F7 | label | agent:UnknownAgent 무명 | 低 | B1 |
| F8 | alias | haz:AccidentType 개체 31 vs canonical class 23 → **8 alias**: Cut/Slip/Crush/Ergonomic(중복)+Burn/ColdExposure/FoodContamination(무명)+FallingObject(누락 정식유형?) | 中 | B2 |
| F9 | 배치 | she:VisualTrigger가 risk 아래 아닌 BFO-only standalone | 低 | B6 |
| F10 | dom/rng | guide 속성 **25/56 누락**(hasChecklistItem/hasWorkProcess 등 핵심관계 dom·rng 둘다 X) | 中 | B4 |
| F11 | grounding | guide:ChecklistItem 이중 grounding(Quality+lkif:Norm) | 低 | B6 |
| F12 | grounding | guide:GuideUsageProfile 무 grounding(⊑ 없음) | 低 | B6 |
| F13 | dead | guide:DocumentRequirement·DomainTerm ref=0 (미사용 클래스) | 低 | B2 |
| F14 | **broken** | **core:Relation dangling** — core:Incompatibility ⊑ 선언 안 된 core:Relation(triple 0). 프로젝트 유일 dangling | 中 | B2 |
| F15 | dom/rng | core 속성 6/16 누락 (coApplicable/exemptedBy/hasViolation 등) | 中 | B4 |
| F16 | dead | core:Worker 개체 **ref=0**(ProtectedPerson placeholder 미사용). actor:Worker(class)와 의도적 분리지만 placeholder는 죽음 | 低 | B2 |
| F17 | dom/rng | bridge 속성 2/3 누락 (appliesTo/observedIn) | 中 | B4 |
| F18 | label | industry 7건 — Industry_GENERAL `"general"@ko`(영문 오태깅) + 언더스코어 leak 6(`"자동차_정비소"@ko` 등). 라벨은 **생성물 kosha-disjoint-axioms.ttl**(build_disjoint_axioms.py)에 있고 upstream industry 라벨 소스(Layer 4)에서 옴 → **손수정 불가, upstream 소스 수정 필요(일부 data-team 세션 영역)**. (+명과학 등 의미 오타 수동검토) | 低 | B1→deferred |

별도: **fine 코드 ~330**(haz 150·ctx 109·agent 72) 한글 label 없음 + CI 미참조 = future 어휘 vs prune 정책 결정 필요(B1/B5 연계).

## batch-fix 계획 (additive 먼저, top grounding 마지막)

| 묶음 | 내용 | 위험 | 상태 |
|---|---|:--:|:--:|
| **B1** | label 보강 — F6/F7 ✅완료, F18(industry)/fine 정책 잔여 | 低 | F6·F7 ✅ |
| **B2** | broken/dead 정리 — F14 dangling·F16/F13 dead·F8 alias | 低~中 | ✅ |
| **B3** | disjointness — **F2 축간 ✅(B3a)**, F3 agent/ctx 잔여(B3b, 도메인) | 中 | B3a ✅ |
| **B4** | property domain/range — F10/F15/F17 | 中 | 대기 |
| **B5** | 빈 축 결정 — F4 haz:Hazard·F5 ctx 5축 | 中 | 대기 |
| **B6** | BFO grounding 재설계 — F1/F11/F12/F9 (top, 맨 마지막) | 高 | 대기 |

## 확인된 양호
- floating 0 ✅(Fix A) · haz canonical label 100% · thin/dead canonical 0 ✅(Fix B)
- agent/ctx canonical 축 연결 ✅ · dangling 1개뿐(core:Relation) · industry 80중 73 label 정상
