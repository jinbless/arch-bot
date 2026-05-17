# OntoClean Report
Generated: 2026-05-16T16:40:55.654439+00:00

## Summary
- Classes labeled: 55
- Rigidity: {'~R': 13, '-R': 15, '+R': 27}
- Identity: {'+I': 44, '-I': 11}
- **Subsumption violations: 13**

## Violations
- [identity] +I 'https://cashtoss.info/ontology/penalty#AdministrativeFine' subClassOf -I 'https://cashtoss.info/ontology/penalty#SanctionType' (identity supply mismatch)
- [identity] +I 'https://cashtoss.info/ontology/penalty#CriminalSanction' subClassOf -I 'https://cashtoss.info/ontology/penalty#SanctionType' (identity supply mismatch)
- [identity] +I 'https://cashtoss.info/ontology/risk/situation#SituationalHazardPattern' subClassOf -I 'https://cashtoss.info/ontology/risk#RiskPattern' (identity supply mismatch)
- [identity] +I 'https://cashtoss.info/ontology/risk/hazard#AccidentType' subClassOf -I 'https://cashtoss.info/ontology/risk#RiskFeature' (identity supply mismatch)
- [identity] +I 'https://cashtoss.info/ontology/risk/context#PPEState' subClassOf -I 'https://cashtoss.info/ontology/risk#RiskFeature' (identity supply mismatch)
- [identity] +I 'https://cashtoss.info/ontology/risk/hazard#Hazard' subClassOf -I 'https://cashtoss.info/ontology/risk#RiskFeature' (identity supply mismatch)
- [identity] +I 'https://cashtoss.info/ontology/risk/context#TemporalStage' subClassOf -I 'https://cashtoss.info/ontology/risk#RiskFeature' (identity supply mismatch)
- [identity] +I 'https://cashtoss.info/ontology/risk/context#WorkContext' subClassOf -I 'https://cashtoss.info/ontology/risk#RiskFeature' (identity supply mismatch)
- [rigidity] +R 'https://cashtoss.info/ontology/risk/context#WorkActivity' subClassOf ~R 'https://cashtoss.info/ontology/risk#RiskFeature' (rigid subclass of anti-rigid)
- [identity] +I 'https://cashtoss.info/ontology/risk/context#WorkActivity' subClassOf -I 'https://cashtoss.info/ontology/risk#RiskFeature' (identity supply mismatch)
- [rigidity] +R 'https://cashtoss.info/ontology/risk/agent#HazardousAgent' subClassOf ~R 'https://cashtoss.info/ontology/risk#RiskFeature' (rigid subclass of anti-rigid)
- [identity] +I 'https://cashtoss.info/ontology/risk/agent#HazardousAgent' subClassOf -I 'https://cashtoss.info/ontology/risk#RiskFeature' (identity supply mismatch)
- [identity] +I 'https://cashtoss.info/ontology#RegulatoryAuthority' subClassOf -I 'https://cashtoss.info/ontology#SubjectRole' (identity supply mismatch)

## Sample labels (first 20)
- `SituationMatch`: ~R +I -U -D — 특정 상황에 ‘해당함’은 상황/조건에 따라 성립이 달라져(반고정), anti-rigid로 본다. 본 class에 고유한 식별(무엇이 매칭되었는지에 대한 구별 기준)을 둔다고 보고 
- `UploadedPhoto`: -R +I +U -D — 사진의 업로드 여부는 시간에 따라 달라질 수 있어(일시적 상태) -R. ‘업로드된 사진’ 자체는 식별 기준(예: 업로드 시점/대상/파일 식별 등)을 제공하는 것으로 +I. 업로드된
- `VisualCue`: ~R +I +U +D — 시각적 단서(cue)는 어떤 instance가 ‘단서로 기능한다’는 관계적 성격이 강해 결국 단서가 아닐 수도 있어 ~R. 단서는 무엇이 단서로 식별되는지(예: 출처/좌표/대상 등
- `VisualObservation`: -R +I +U +D — 시각 관찰은 특정 기간/행위로서 성립하며(관찰 이후 상태가 바뀔 수) -R. 관찰은 관찰 대상/시점/주체 등으로 구별되는 고유 식별 기준이 있어 +I. 하나의 관찰 사건은 whol
- `ChecklistItem`: ~R +I +U -D — 체크리스트 항목은 특정 체크리스트/실행 맥락에서 ‘항목’으로 기능하지만, 동일 개체가 항상 항목일 것이라고 보기 어렵고(문맥/상태 변화) ~R. 항목은 항목 자체의 고유 기준(항목
- `DocumentRequirement`: -R +I -U +D — ‘요구’는 특정 절차/사례/상황에 따라 적용 여부가 달라져 -R. 요구 자체는 어떤 문서가 필요하다는 형태의 구체적 기준이 있어 +I. 요구들은 보통 문서 집합/조건의 묶음 형태로
- `DomainTerm`: +R +I +U -D — 도메인 용어는 해당 개념 범주로서 본질적으로 고정적이어서 +R. 용어는 고유한 의미/표기 기준을 통해 식별되므로 +I. 용어는 하나의 개념 단위로 취급되며 +U. 특정 다른 cla
- `EquipmentSpec`: +R +I +U -D — 장비 스펙은 사양/명세로서 본질적으로 고정적이므로 +R. ‘스펙’은 모델명/버전/파라미터 등으로 고유 식별이 가능해 +I. 명세 자체는 단일 문서/단위로 파악되어 +U. 특정 다른
- `KoshaGuide`: +R +I +U -D — 가이드(문서/지침)는 어떤 instance가 그 지침의 역할을 항상 갖는다고 보아 +R. 지침은 고유한 명칭/버전/식별번호로 +I. 가이드는 ‘whole’이 명확한 단일 문서로 +
- `WorkProcess`: +R +I ~U +D — 업무 프로세스는 절차적 유형으로서 비교적 고정적이며 +R. 프로세스는 절차/단계 구성에 의해 고유 식별이 가능하다고 보고 +I. 다만 프로세스는 단계들의 흐름/부분들이 구성되는 ‘
- `Article`: +R +I +U -D — 조항은 법 체계 내에서 고정된 단위로 다루어지므로 +R. Article은 조항 번호/명칭 등으로 고유 식별 기준을 제공하므로 +I. 조항 자체는 단일 텍스트/단위이므로 +U. 법적
- `Chapter`: +R +I +U -D — 장(chapter)은 법 체계에서 고정된 구성 단위로 +R. 고유한 챕터 번호/식별로 +I. 챕터는 단일 whole이 비교적 명확해 +U. 다른 특정 class의 존재에의존으로 보
- `LawType`: +R +I +U -D — 법 유형은 분류로서 본질적으로 고정적이므로 +R. 유형은 고유한 기준(명칭/분류코드)으로 +I. 하나의 유형은 단일 개념 단위로 +U. 특정 다른 class에 존재 의존하지 않으므
- `LegalEntity`: +R +I +U -D — 법적 실체는 법적으로 규정된 범주/개체로서 고정적이므로 +R. 법적 실체는 고유한 식별(명칭/등록/식별코드)로 +I. 실체는 단일 whole로 +U. 특정 다른 class의 존재에
- `LegalStructure`: +R +I -U -D — 법 구조는 조직/체계(예: 계층/구성)로서 비교적 고정적이므로 +R. 고유 구조 식별(예: 체계 이름/코드)로 +I. 다만 법 구조는 여러 부분(기관/조항/챕터 등)의 모음적 성격
- `PPEState`: -R +I -U -D — PPE의 착용/상태는 시간에 따라 변할 수 있어 (일시적) 반강직(-R)으로 본다. PPE 착용 상태는 그 자체로 식별 기준을 가지는 편(+I)이며, ‘상태’는 보통 개체의 집합(
- `TemporalStage`: -R +I -U -D — TemporalStage는 특정 시점/구간에 국한되어 항상 그 클래스가 유지되지 않으므로 반강직(-R). 시점/구간 자체가 식별 기준(+I)으로 작동. 또한 ‘stage’는 집합으
- `WorkActivity`: +R +I ~U -D — WorkActivity는 활동(작업)의 유형/개념이 인스턴스의 존재 전개 내에서 그 정체성을 유지하는 경향이 강해 강강직(+R)으로 본다. ‘활동’은 활동에 고유한 식별(언제/무엇
- `WorkContext`: -R +I ~U -D — WorkContext는 작업 중/특정 조건 하에서 성립하며 상황이 바뀌면 그 맥락은 달라져 일시적 성격이 강해(-R). 맥락 인스턴스(조건 묶음)는 식별 기준(+I)을 갖는다고 본
- `AccidentType`: ~R +I -U -D — 사고 유형은 ‘특정 유형의 사고’로 규정되는 경우가 있지만, 모든 인스턴스가 항상 그 유형에 속한다고 보기 어렵고(또는 더 이상 사고 유형으로 남지 않을 수 있음) 비강직/반정합(