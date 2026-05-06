# 법령 레이어 상세도

법령 레이어는 조문 자체와 조문에서 추출한 규범 문장을 분리한다.

문서 기준일: 2026-05-05

```mermaid
---
config:
  layout: elk
---
flowchart TB
    %% LEGEND
    subgraph Legend["범례 (Legend)"]
      direction TB
      LawLegend["<b style='color:#4f46e5;'>법령 도메인 (law:)</b><br/>조문, 규범진술문, 법령 구조, 법령 유형"]
      CoreLegend["<b style='color:#0f766e;'>코어 도메인 (core:)</b><br/>모달리티와 주체 역할 같은 공통 추상 개념"]
      RelationLegend["<b>관계 유형:</b><br/><span style='color:#1d4ed8;'>rdfs:</span> 클래스 상속<br/><span style='color:#7c2d12;'>law:</span> 법령 구조·규범 관계<br/><span style='color:#64748b;'>점선:</span> 상속 또는 inverse/data-use 보조 관계"]
    end

    %% DOMAINS
    subgraph LawDomain["법령 도메인 (law:)"]
      direction TB
    LegalEntity["법령 엔티티<br/>(law:LegalEntity)"]
    Article["조문<br/>(law:Article)"]
      LawType["법령 유형<br/>(law:LawType)"]
      LawTypeValues["법령 유형 값<br/>(law:LawType_RULE / OSHA / DECREE / ENFORCE / SADA)"]
    NormStatement["규범 진술문<br/>(law:NormStatement)"]
    LegalStructure["법령 구조<br/>(law:LegalStructure)"]
    Part["편<br/>(law:Part)"]
    Chapter["장<br/>(law:Chapter)"]
    Section["절<br/>(law:Section)"]
    Subsection["관<br/>(law:Subsection)"]
    end

    subgraph CoreDomain["코어 도메인 (core:)"]
      direction TB
      Modality["모달리티<br/>(core:Modality)"]
      ModalityValues["모달리티 값<br/>(core:Obligation / Prohibition / Permission / Exemption / Definition)"]
      SubjectRole["주체 역할<br/>(core:SubjectRole)"]
      SubjectRoleSubtypes["역할 하위분류<br/>(core:DutyHolder / ProtectedPerson / RegulatoryAuthority)"]
    end

    %% rdfs: relationships
    Part R01@-.->|"rdfs:subClassOf"| LegalStructure
    Chapter R02@-.->|"rdfs:subClassOf"| LegalStructure
    Section R03@-.->|"rdfs:subClassOf"| LegalStructure
    Subsection R04@-.->|"rdfs:subClassOf"| LegalStructure
    Article R05@-.->|"rdfs:subClassOf"| LegalEntity
    NormStatement R06@-.->|"rdfs:subClassOf"| LegalEntity
    SubjectRoleSubtypes R07@-.->|"rdfs:subClassOf"| SubjectRole
    LawTypeValues R08@-.->|"rdf:type"| LawType
    ModalityValues R09@-.->|"rdf:type"| Modality

    %% law: relationships
    Subsection L01@==>|"law:hasParentStructure<br/>(TransitiveProperty, data-use)"| Section
    Section L02@==>|"law:hasParentStructure<br/>(TransitiveProperty, data-use)"| Chapter
    Chapter L03@==>|"law:hasParentStructure<br/>(TransitiveProperty, data-use)"| Part
    Article L04@==>|"law:hasLawType<br/>(FunctionalProperty)"| LawType
    Article L05@-.->|"law:hasNormStatement<br/>(inverseOf hasSourceArticle)"| NormStatement
    Article L06@==>|"law:belongsToPart<br/>(data-use)"| Part
    Article L07@==>|"law:belongsToChapter<br/>(data-use)"| Chapter
    Article L08@==>|"law:belongsToSection<br/>(data-use)"| Section
    Article L09@==>|"law:belongsToSubsection<br/>(data-use)"| Subsection
    NormStatement L10@==>|"law:hasSourceArticle<br/>(FunctionalProperty)"| Article
    NormStatement L11@==>|"law:hasModality<br/>(FunctionalProperty)"| Modality
    NormStatement L12@==>|"law:hasSubjectRole"| SubjectRole
    NormStatement L13@==>|"law:modifies<br/>(AsymmetricProperty)"| NormStatement

    %% STYLING
    classDef law fill:#eef2ff,stroke:#818cf8,color:#111;
    classDef core fill:#f0fdfa,stroke:#2dd4bf,color:#111;
    classDef legend fill:#fefce8,stroke:#facc15,color:#111;
    classDef rdfsedge stroke:#1d4ed8,color:#1d4ed8;
    classDef lawedge stroke:#7c2d12,color:#7c2d12;
    classDef dataedge stroke:#64748b,color:#64748b,stroke-dasharray: 5 5;

    class LegalEntity,Article,LawType,LawTypeValues,NormStatement,LegalStructure,Part,Chapter,Section,Subsection law;
    class Modality,ModalityValues,SubjectRole,SubjectRoleSubtypes core;
    class Legend,LawLegend,CoreLegend,RelationLegend legend;
    class R01,R02,R03,R04,R05,R06,R07,R08,R09 rdfsedge;
    class L01,L02,L03,L04,L06,L07,L08,L09,L10,L11,L12,L13 lawedge;
    class L05 dataedge;
```

## 핵심 TTL 예시

```ttl
law:RULE_제100조 a law:Article ;
    core:title "띠톱기계의 덮개 등"^^xsd:string ;
    law:articleCode "제100조"^^xsd:string ;
    law:hasLawType law:LawType_RULE .

law:NS-RULE100-0 a law:NormStatement ;
    core:identifier "NS-RULE100-0"^^xsd:string ;
    core:text "사업주는 ... 덮개 또는 울 등을 설치하여야 한다."^^xsd:string ;
    law:hasSourceArticle law:RULE_제100조 ;
    law:hasModality core:Obligation ;
    law:hasSubjectRole core:Employer ;
    law:hasAction "덮개 또는 울 등을 설치하여야 한다"^^xsd:string ;
    law:hasObject "띠톱기계 위험 톱날 부위 방호설비"^^xsd:string .
```

## Triple식 해석

- `law:RULE_제100조`는 / `law:hasLawType` 관계로 / `law:LawType_RULE`을 가진다.
- `law:NS-RULE100-0`은 / `law:hasSourceArticle` 관계로 / `law:RULE_제100조`를 가진다.
- `law:NS-RULE100-0`은 / `law:hasModality` 관계로 / `core:Obligation`을 가진다.
- `law:NS-RULE100-0`은 / `law:hasSubjectRole` 관계로 / `core:Employer`를 가진다.

## 실제 OWL 기준 주의점

- `law:Article`과 `law:NormStatement`는 `law:LegalEntity`의 하위 클래스다.
- `law:Part`, `law:Chapter`, `law:Section`, `law:Subsection`은 `law:LegalStructure`의 하위 클래스다.
- `law:hasLawType`, `law:hasSourceArticle`, `law:hasModality`는 `owl:FunctionalProperty`다. 즉 한 조문 또는 한 규범진술문에 대해 값이 하나로 제한되는 설계다.
- `law:hasNormStatement`는 `domain/range`가 직접 선언되어 있지 않고, `law:hasSourceArticle`의 `owl:inverseOf`로 정의되어 있다. 따라서 `Article -> hasNormStatement -> NormStatement`는 명시 데이터라기보다 역관계로 읽는 것이 정확하다.
- `law:belongsToPart`, `law:belongsToChapter`, `law:belongsToSection`, `law:belongsToSubsection`은 현재 OWL 스키마에 `domain/range`가 직접 선언되어 있지 않다. 다만 인스턴스 데이터에서는 `Article -> LegalStructure` 사용 패턴으로 쓰인다.
- `law:hasParentStructure`도 `domain/range`가 직접 선언되어 있지 않지만, `owl:TransitiveProperty`이며 인스턴스 데이터에서는 `Subsection -> Section -> Chapter -> Part` 방향으로 사용한다.
- `law:modifies`는 `NormStatement -> NormStatement`의 비대칭 관계(`owl:AsymmetricProperty`)다. 역관계인 `law:modifiedBy`도 OWL에 정의되어 있지만, 이 상세도에서는 핵심 방향인 `modifies`만 표시했다.
- `pen:PenaltyRule`도 실제 OWL에서는 `law:LegalEntity`의 하위 클래스지만, 벌칙 레이어 상세도에서 따로 다루므로 이 법령 레이어 그림에서는 생략했다.

## 주요 데이터 속성

- `core:title`: 사람이 읽는 제목
- `core:text`: 원문 또는 추출 문장
- `core:identifier`: 내부 식별자
- `law:articleCode`: 제100조 같은 조문 번호
- `law:hasAction`: 규범 문장의 행위
- `law:hasObject`: 행위의 대상
- `law:conditionText`: 단서/예외 조건 원문
- `law:paragraphRef`: 본문, 제1항, 단서 같은 위치 정보
