# KOSHA 온톨로지 카탈로그

> AUTO-GENERATED (scripts/gen_catalog.py) — 수동편집 금지. Generated: 2026-05-31T13:52:34+00:00
> 소스: serving TBox+facet+moderate ABox (38 files, 569,051 triples; 대용량 instances 제외)
> class 627 · objectProperty 132 · dataProperty 68 · individual 234

## 1. 모듈 개요 (prefix)

| prefix | class | objProp | dataProp | individual | namespace |
|---|--:|--:|--:|--:|---|
| `risk:` | 3 | 7 | 1 | 0 | `https://cashtoss.info/ontology/risk#` |
| `haz:` | 182 | 1 | 0 | 23 | `https://cashtoss.info/ontology/risk/hazard#` |
| `agent:` | 85 | 0 | 0 | 12 | `https://cashtoss.info/ontology/risk/agent#` |
| `ctx:` | 221 | 0 | 0 | 155 | `https://cashtoss.info/ontology/risk/context#` |
| `she:` | 2 | 15 | 4 | 0 | `https://cashtoss.info/ontology/risk/situation#` |
| `sr:` | 2 | 14 | 0 | 8 | `https://cashtoss.info/ontology/sr#` |
| `pen:` | 8 | 17 | 7 | 3 | `https://cashtoss.info/ontology/penalty#` |
| `law:` | 9 | 16 | 10 | 5 | `https://cashtoss.info/ontology/law#` |
| `guide:` | 9 | 25 | 31 | 0 | `https://cashtoss.info/ontology/guide#` |
| `core:` | 9 | 8 | 8 | 20 | `https://cashtoss.info/ontology#` |
| `app:` | 15 | 26 | 7 | 8 | `https://cashtoss.info/ontology/app#` |
| `industry:` | 80 | 0 | 0 | 0 | `https://cashtoss.info/ontology/industry#` |
| `bridge:` | 1 | 3 | 0 | 0 | `https://cashtoss.info/ontology/bridge#` |
| `actor:` | 1 | 0 | 0 | 0 | `https://cashtoss.info/ontology/actor#` |

## 2. 클래스 계층 (전체 트리)

표기: `prefix:Class` "label" [⊒하위수, ←피참조수]. 상위 BFO/LKIF는 괄호로.

- `actor:Worker` "근로자" [⊒0, ←3] ⊑(obo:BFO_0000040)
- `app:ActionRecommendation` "조치 추천 항목" [⊒0, ←6] ⊑(obo:BFO_0000015, lkif:Obligation)
- `app:AssessmentReport` "사업주 안내 결과" ⊑(obo:BFO_0000003, lkif:Norm)
- `app:CorrectiveAction` "개선 조치" [⊒0, ←7] ⊑(obo:BFO_0000015, lkif:Obligation)
- `app:CorrectiveActionPlan` "조치 계획" [⊒0, ←1] ⊑(obo:BFO_0000015, lkif:Obligation)
- `app:FindingStatus` "판정 상태" [⊒0, ←9] ⊑(obo:BFO_0000019, lkif:Norm)
- `app:HazardFinding` "위험 판단" [⊒0, ←7] ⊑(obo:BFO_0000019, +제약2)
- `app:InspectionCase` "분석 건" [⊒0, ←2] ⊑(obo:BFO_0000003)
- `app:Noncompliance` "비준수" [⊒0, ←2] ⊑(obo:BFO_0000019)
- `app:PenaltyExposure` "벌칙 노출" [⊒0, ←12] ⊑(obo:BFO_0000019, lkif:Penalty, +제약3)
- `app:PenaltyExposureStatus` "벌칙 노출 상태" [⊒0, ←4] ⊑(obo:BFO_0000019, lkif:Penalty)
- `app:PenaltyLevel` "벌칙 심각도 레벨" [⊒0, ←3] ⊑(obo:BFO_0000019)
- `app:SituationMatch` "상황 매칭" [⊒0, ←8] ⊑(obo:BFO_0000019, lkif:Norm, +제약3)
- `app:UploadedPhoto` "업로드 사진" [⊒0, ←3] ⊑(obo:BFO_0000002)
- `app:VisualCue` "시각 단서" [⊒0, ←7] ⊑(obo:BFO_0000019)
- `app:VisualObservation` "관찰 사실" [⊒0, ←19] ⊑(obo:BFO_0000003, +제약3)
- `core:BindingForce` "구속력" [⊒0, ←3] ⊑(lkif:Norm)
- `core:Industry` "산업 분류" [⊒80, ←80]
  - `industry:Industry_AGRICULTURE_FORESTRY` "농업·임업" [⊒0, ←141]
  - `industry:Industry_AGRICULTURE_HORTICULTURE` "농업·원예·화훼" [⊒0, ←145]
  - `industry:Industry_ANIMAL_HOSPITAL_SHELTER` "동물병원·동물보호시설" [⊒0, ←141]
  - `industry:Industry_AUTO_REPAIR_LARGE` "자동차 정비업(대형)" [⊒0, ←167]
  - `industry:Industry_AUTO_REPAIR_SHOP` "자동차_정비소" [⊒0, ←174]
  - `industry:Industry_BAKERY_CONFECTIONERY` "제과·제빵업" [⊒0, ←155]
  - `industry:Industry_BEAUTY_SALON` "미용업" [⊒0, ←151]
  - `industry:Industry_BUILDING_FACILITY_MANAGEMENT` "빌딩 설비관리업" [⊒0, ←94]
  - `industry:Industry_BUTCHER_MEAT_RETAIL` "정육점·식육업" [⊒0, ←1]
  - `industry:Industry_CAFE` "카페" [⊒0, ←186]
  - `industry:Industry_CAR_WASH` "세차장" [⊒0, ←1]
  - `industry:Industry_CHEMICAL_INDUSTRY` "화학" [⊒0, ←146]
  - `industry:Industry_CHEMICAL_LIFE_SCIENCE_LAB` "화학·명과학 연구소" [⊒0, ←298]
  - `industry:Industry_CHEMICAL_SUBSTANCE_MANUFACTURING` "화학·물질 제조업" [⊒0, ←212]
  - `industry:Industry_CHILD_YOUTH_WELFARE` "어린이·청소년복지시설" [⊒0, ←145]
  - `industry:Industry_CLEANING_SERVICE` "청소용역업" [⊒0, ←124]
  - `industry:Industry_COMMERCIAL_KITCHEN_CATERING` "주방·급식 대형 조리" [⊒0, ←151]
  - `industry:Industry_CONCRETE_CONSTRUCTION` "콘크리트 공사" [⊒0, ←130]
  - `industry:Industry_CONSTRUCTION` "건설" [⊒0, ←77]
  - `industry:Industry_DAYCARE_KINDERGARTEN` "어린이집·유치원" [⊒0, ←154]
  - `industry:Industry_DELIVERY` "배달업" [⊒0, ←142]
  - `industry:Industry_DENTAL_ORIENTAL_MEDICINE_SMALL_CLINIC` "치과·한의원·소규모 의료" [⊒0, ←171]
  - `industry:Industry_DISABILITY_WELFARE_FACILITY` "장애인복지시설" [⊒0, ←139]
  - `industry:Industry_EARTHWORK_EXCAVATION` "토공사·굴착" [⊒0, ←135]
  - `industry:Industry_ELDERLY_CARE_FACILITY` "요양원·노인요양시설" [⊒0, ←135]
  - `industry:Industry_ELECTRICAL_CONSTRUCTION` "전기공사업" [⊒0, ←102]
  - `industry:Industry_ELECTRICAL_ELECTRONICS_COMPLEX` "전기·전자 콤플렉스" [⊒0, ←133]
  - `industry:Industry_ELECTRONICS_SEMICONDUCTOR_MANUFACTURING` "전자·반도체 제조" [⊒0, ←159]
  - `industry:Industry_FIRE_PROTECTION_INSTALLATION` "소방·방재 설비업" [⊒0, ←84]
  - `industry:Industry_FOOD_MANUFACTURING` "식품 제조업" [⊒0, ←160]
  - `industry:Industry_FUNERAL_HALL` "장례식장" [⊒0, ←2]
  - `industry:Industry_GAS_PIPING_INSTALLATION` "가스·배관 설비업" [⊒0, ←97]
  - `industry:Industry_GAS_STATION` "주유소" [⊒0, ←183]
  - `industry:Industry_GENERAL` "general" [⊒0, ←12]
  - `industry:Industry_GENERAL_SAFETY` "일반안전" [⊒0, ←3]
  - `industry:Industry_GYM_SPORTS_FACILITY` "헬스장·스포츠시설" [⊒0, ←186]
  - `industry:Industry_HIGH_STEEL_CONSTRUCTION` "고소·강구조 공사" [⊒0, ←102]
  - `industry:Industry_HOSPICE_PALLIATIVE_CARE` "호스피스·완화의료시설" [⊒0, ←181]
  - `industry:Industry_HOSPITAL_FACILITY_MANAGEMENT` "병원 시설관리" [⊒0, ←92]
  - `industry:Industry_LANDSCAPING_GREENSPACE` "조경·녹지 관리업" [⊒0, ←164]
  - … (+40 more 하위, inspect_node.py --list 로 확인)
- `core:Modality` "모달리티" [⊒0, ←6] ⊑(lkif:Norm)
- `core:Relation` "관계" [⊒1, ←1]
  - `core:Incompatibility` "산업 간 부적합성 관계" [⊒0, ←7]
- `core:SubjectRole` "의무 주체" [⊒3, ←5] ⊑(lkif:Role)
  - `core:DutyHolder` "의무이행주체" [⊒0, ←7] ⊑(lkif:Role)
  - `core:ProtectedPerson` "보호대상" [⊒0, ←5] ⊑(lkif:Role)
  - `core:RegulatoryAuthority` "규제기관" [⊒0, ←1] ⊑(lkif:Role)
- `guide:ChecklistItem` "점검항목" [⊒1, ←17] ⊑(obo:BFO_0000019, lkif:Norm)
  - `guide:CanonicalChecklistItem` "고유 점검항목(control)" [⊒0, ←51269]
- `guide:DocumentRequirement` "문서 요구사항" [⊒0, ←3] ⊑(lkif:Obligation)
- `guide:DomainTerm` "도메인 용어" [⊒0, ←4] ⊑(lkif:NormStatement)
- `guide:Equipment` "장비" [⊒0, ←7] ⊑(obo:BFO_0000040, +제약1)
- `guide:EquipmentSpec` "장비 규격" [⊒0, ←8] ⊑(obo:BFO_0000019)
- `guide:GuideUsageProfile` "Guide 사용 프로필" [⊒0, ←17] ⊑(+제약4)
- `guide:KoshaGuide` "KOSHA 가이드" [⊒0, ←25] ⊑(lkif:LegalDocument)
- `guide:WorkProcess` "작업 프로세스" [⊒0, ←11] ⊑(obo:BFO_0000015)
- `law:LawType` "법령 유형" [⊒0, ←6] ⊑(lkif:LegalDocument)
- `law:LegalEntity` "법령 엔티티" [⊒3, ←3] ⊑(lkif:Role)
  - `law:Article` "조문" [⊒0, ←12] ⊑(lkif:Norm)
  - `law:NormStatement` "규범 진술문" [⊒1, ←32] ⊑(lkif:Norm, +제약2)
    - `bridge:ViolationCandidate` "위반 후보 NormStatement" [⊒0, ←1] ⊑(+제약2)
  - `pen:PenaltyRule` "벌칙 적용 규칙" [⊒0, ←23] ⊑(lkif:Norm, +제약4)
- `law:LegalStructure` "법령 구조" [⊒4, ←4] ⊑(lkif:LegalDocument)
  - `law:Chapter` "장" ⊑(lkif:LegalDocument)
  - `law:Part` "편" ⊑(lkif:LegalDocument)
  - `law:Section` "절" ⊑(lkif:LegalDocument)
  - `law:Subsection` "관" ⊑(lkif:LegalDocument)
- `pen:AccidentOutcome` "사고 결과" [⊒0, ←4] ⊑(lkif:NormStatement)
- `pen:PenaltyCondition` "벌칙 선택 조건" [⊒0, ←3] ⊑(lkif:Obligation)
- `pen:PenaltyResult` "벌칙 결과" [⊒0, ←5] ⊑(obo:BFO_0000019)
- `pen:SanctionType` "제재 유형" [⊒3, ←6] ⊑(lkif:LegalDocument)
  - `pen:AdministrativeFine` "과태료" ⊑(lkif:Prohibition)
  - `pen:CriminalSanction` "형사벌" [⊒0, ←1] ⊑(lkif:Prohibition)
  - `pen:HighSeverityPenalty` "고위험 제재" [⊒0, ←1]
- `risk:RiskFeature` "위험 특징" [⊒9, ←45] ⊑(obo:BFO_0000019, +제약4)
  - `agent:HazardousAgent` "유해 인자" [⊒10, ←30] ⊑(obo:BFO_0000030)
    - `agent:Biological` "생물학적" [⊒3, ←605]
      - `agent:BloodbornePathogen` "혈액 매개 감염"
      - `agent:InfectiousMedicalWaste` "감염성 의료 폐기물"
      - `agent:LackOfVaccination` "예방접종 미이행"
    - `agent:Chemical` "화학물질" [⊒17, ←12919]
      - `agent:AcrylateResinSkinContact` "아크릴레이트 수지 피부 접촉"
      - `agent:Benzene` "벤젠"
      - `agent:ChlorineAmmoniaReaction` "염소+암모니아 반응"
      - `agent:ConcentratedAlkali` "농축된 알칼리"
      - `agent:Corrosion` "부식성 물질"
      - `agent:DegradedDeveloperSolution` "변질된 현상액"
      - `agent:FormaldehydeSkinContact` "포름알데히드 피부 접촉"
      - `agent:FragranceVapor` "방향제 증기"
      - `agent:GlutaraldehydeVapor` "글루타르알데히드 증기"
      - `agent:LeachateHazardousSubstance` "침출수 유해물질"
      - `agent:MercuryAmalgamVapor` "아말감 수은 증기"
      - `agent:MislabeledDetergent` "라벨 불일치 세제"
      - `agent:MixedDetergentGas` "혼합 세제 가스"
      - `agent:ResidualPesticide` "잔류 살충제"
      - `agent:SolventVapor` "용제 증기 누설"
      - `agent:StrongAcidDescaler` "강산성 스케일 제거제 원액"
      - `agent:WaterBasedPaintMist` "수성 도료 미스트"
    - `agent:Dust` "분진" [⊒4, ←1634]
      - `agent:AsbestosDust` "석면 분진"
      - `agent:ContaminatedFilterParticulateMold` "오염 필터 미세먼지·곰팡이"
      - `agent:HighPressureAirDust` "고압 에어 비산 먼지"
      - `agent:LeadPaintDust` "납 함유 도료 분진"
    - `agent:Electricity` "전기" [⊒8, ←8803]
      - `agent:ArcFlash` "아크 섬광"
      - `agent:CapacitorResidualVoltage` "트레드밀 커패시터 잔류 전압"
      - `agent:DistributionBoard` "분전반"
      - `agent:ElectricalOverload` "전기 과부하"
      - `agent:ElectricityWaterContact` "전기 물 접촉"
      - `agent:ExposedOutlet` "콘센트 노출"
      - `agent:StaticElectricity` "정전기"
      - `agent:TwistedWire` "꼬인 와이어"
    - `agent:Fire` "화재·폭발" [⊒0, ←9535]
    - `agent:HeatCold` "온도" [⊒17, ←2618]
      - `agent:ColdFloor` "저온 바닥"
      - `agent:CryogenicAgent` "극저온"
      - `agent:ExtremeColdEnvironment` "극저온 환경"
      - `agent:ExtremeColdSurface` "극저온 표면"
      - `agent:HighHeat` "고열"
      - `agent:HighTemperatureEnvironment` "고온 환경"
      - `agent:HighTemperatureSteam` "고온 증기"
      - `agent:HotEquipment` "고온 기구"
      - `agent:HotParts` "고온 부품"
      - `agent:HotSurface` "고열 표면"
      - `agent:HotTray` "고온 트레이"
      - `agent:HotWater` "고온 온수"
      - `agent:ProlongedColdExposure` "저온 장기 노출"
      - `agent:ProlongedExposureToColdEnvironment` "저온 환경 장기 노출"
      - `agent:RadiantHeat` "고온 복사열"
      - `agent:RepeatedExtremeColdExposure` "극저온 반복 노출"
      - `agent:UvLampResidualHeat` "UV 램프 잔열"
    - `agent:Noise` "소음·진동" [⊒4, ←1276]
      - `agent:EarphoneNoise` "이어폰 소음"
      - `agent:KaraokeNoise` "노래방 소음"
      - `agent:KaraokeRoomNoise` "노래방 고소음"
      - `agent:Noise105Db` "합산 105dB 소음"
    - `agent:Radiation` "방사선" [⊒7, ←446]
      - `agent:DentalXRay` "치과 방사선"
      - `agent:DentalXrayRepeatedExposure` "치과 X선 반복 노출"
      - `agent:RadiationExposure` "방사선 노출"
      - `agent:RadiationExposureDuringPregnancy` "임신 중 방사선 노출"
      - `agent:RepeatedRadiationExposure` "방사선 반복 노출"
      - `agent:ScatteredRadiation` "산란 방사선"
      - `agent:UltravioletRadiation` "자외선"
    - `agent:Toxic` "독성물질" [⊒8, ←3100]
      - `agent:BiogasMethane` "바이오가스(메탄)"
      - `agent:ElevatorPitToxicGas` "엘리베이터 피트 유해가스"
      - `agent:FuelSaturatedAbsorbent` "연료 포화 흡착포"
      - `agent:GasolineMicroLeakage` "휘발유 미세 누출"
      - `agent:GasolineVapor` "휘발유 증기"
      - `agent:ResidualCombustionGas` "잔류물 연소 가스"
      - `agent:SmallQuantityGasoline` "소량 휘발유"
      - `agent:TobaccoSmoke` "담배 연기"
    - `agent:UnknownAgent` "미상 유해인자" [⊒6, ←8]
      - `agent:AirlessResidualPressure` "에어리스 잔압"
      - `agent:DefectiveHandle` "불량 손잡이"
      - `agent:DefectiveSterilePackaging` "포장 불량 기구"
      - `agent:FemaleExposureLimitExceeded` "여성 기준 초과"
      - `agent:ResidualRotation` "잔류 회전"
      - `agent:RopeKink` "로프 킹크"
  - `ctx:AgentState` "작업자 상태 (agent_state)" [⊒0, ←7] ⊑(obo:BFO_0000019)
  - `ctx:EnvironmentalFactor` "환경 요인 (environmental)" [⊒0, ←12] ⊑(obo:BFO_0000019)
  - `ctx:PPEState` "보호구 상태 (ppe_state)" [⊒0, ←20] ⊑(obo:BFO_0000019)
  - `ctx:TemporalStage` "시간 단계 (temporal_stage)" [⊒0, ←12] ⊑(obo:BFO_0000003)
  - `ctx:WorkActivity` "작업 활동 (work_activity)" [⊒0, ←13] ⊑(obo:BFO_0000015)
  - `ctx:WorkContext` "작업 맥락" [⊒29, ←145] ⊑(obo:BFO_0000015)
    - `ctx:ChemicalWork` "화학물질 취급작업" [⊒22, ←6166]
      - `ctx:AirlessSprayer` "airless sprayer"
      - `ctx:ChemicalApplication` "세차 화학약품 도포" [⊒0, ←6]
      - `ctx:ChemicalCleaning` "chemical cleaning"
      - `ctx:ChemicalDisinfection` "chemical disinfection"
      - `ctx:ChemicalMixing` "chemical mixing"
      - `ctx:ChemicalSpotting` "얼룩 제거 화학작업" [⊒0, ←6]
      - `ctx:ChemicalWaste` "chemical waste"
      - `ctx:DryCleaningSolvent` "드라이클리닝 용제 작업" [⊒0, ←4]
      - `ctx:FuelDispensing` "주유 작업" [⊒0, ←6]
      - `ctx:FuelSpill` "연료 유출 작업" [⊒0, ←4]
      - `ctx:GasAppliance` "가스기기" [⊒0, ←2]
      - `ctx:HairChemical` "미용 화학약품 작업" [⊒0, ←8]
      - `ctx:InkSolvent` "ink solvent"
      - `ctx:NailChemical` "네일 화학약품 작업" [⊒0, ←8]
      - `ctx:OilDrain` "오일 교환·폐오일 취급" [⊒0, ←8]
      - `ctx:Painting` "painting" [⊒0, ←6]
      - `ctx:PaintingWoodwork` "목공 도장 작업" [⊒0, ←8]
      - `ctx:PesticideSpray` "농약 살포" [⊒0, ←10]
      - `ctx:RestroomChemical` "restroom chemical"
      - `ctx:SolventHandling` "solvent handling"
      - `ctx:SprayPainting` "spray painting"
      - `ctx:VaporExposure` "유증기 노출" [⊒0, ←6]
    - `ctx:CollapsePrevention` "붕괴방지 작업" [⊒0, ←1002]
    - `ctx:ConfinedSpace` "밀폐공간" [⊒5, ←1826]
      - `ctx:AquacultureTank` "aquaculture tank"
      - `ctx:ConfinedCoating` "confined coating"
      - `ctx:ConfinedSpaceCleaning` "confined space cleaning"
      - `ctx:UndergroundTank` "지하 탱크 작업" [⊒0, ←4]
      - `ctx:WetConfinedSpace` "습윤 밀폐 공간"
    - `ctx:ConstructionEquip` "건설장비" [⊒0, ←951]
    - `ctx:Conveyor` "컨베이어" [⊒2, ←537]
      - `ctx:ConveyorBelt` "컨베이어 벨트" [⊒0, ←4]
      - `ctx:ConveyorWash` "컨베이어 세차" [⊒0, ←6]
    - `ctx:Crane` "양중기" [⊒0, ←1706]
    - `ctx:Demolition` "해체작업" [⊒0, ←1428]
    - `ctx:DustWork` "분진작업" [⊒0, ←397]
    - `ctx:ElectricalWork` "전기작업" [⊒5, ←3622]
      - `ctx:ElectricPolishingRoller` "전기 연마 롤러"
      - `ctx:ElectricalHazard` "electrical hazard"
      - `ctx:ElectricalOverload` "전기 과부하" [⊒0, ←10]
      - `ctx:LivePowerRepair` "전원 ON 수리"
      - `ctx:StaticElectricity` "정전기 위험 작업" [⊒0, ←2]
    - `ctx:ErgonomicWork` "근골격계부담 작업" [⊒2, ←4]
      - `ctx:AwkwardPostureWork` "부적절한 작업 자세"
      - `ctx:ExcessiveMotionRange` "과도한 동작 반경"
    - `ctx:Excavation` "굴착" [⊒0, ←1126]
    - `ctx:FallProtection` "추락방지 작업" [⊒0, ←384]
    - `ctx:FireExplosionWork` "화재·폭발 위험작업" [⊒4, ←1601]
      - `ctx:FireDetectionFailure` "화재 감지 실패"
      - `ctx:FireDetectorDisabled` "화재 감지기 무력화"
      - `ctx:FireEvacuation` "화재 대피" [⊒0, ←4]
      - `ctx:FireExtinguisherDefective` "불량 소화기"
    - `ctx:HeatColdWork` "고온·저온 작업" [⊒11, ←340]
      - `ctx:ColdDisplay` "냉장 진열대 작업" [⊒0, ←8]
      - `ctx:ColdRoomAccess` "cold room access"
      - `ctx:ColdRoomMortuary` "cold room mortuary"
      - `ctx:DeepFrying` "튀김 조리" [⊒0, ←10]
      - `ctx:DryerOperation` "건조기 작업" [⊒0, ←4]
      - `ctx:FoodPrep` "식재료 전처리" [⊒0, ←14]
      - `ctx:FreezerWork` "freezer work"
      - `ctx:HotBeverage` "고온 음료" [⊒0, ←16]
      - `ctx:HotTool` "고온 미용기구 작업" [⊒0, ←8]
      - `ctx:HotTrayTransport` "hot tray transport"
      - `ctx:KitchenCooking` "주방 조리" [⊒0, ←20]
    - `ctx:Logging` "벌목작업" [⊒0, ←153]
    - `ctx:Machine` "기계" [⊒24, ←4758]
      - `ctx:BandSaw` "band saw"
      - `ctx:BreadSlicer` "bread slicer"
      - `ctx:CompressionDeviceRestart` "압축 장치 재작동"
      - `ctx:DoughMachine` "dough machine"
      - `ctx:FarmMachinery` "농기계 작업" [⊒0, ←8]
      - `ctx:FloorMachine` "floor machine"
      - `ctx:FoldingMachine` "folding machine"
      - `ctx:Grinding` "grinding" [⊒0, ←6]
      - `ctx:GuillotineCutter` "guillotine cutter"
      - `ctx:HighPressureWash` "고압 세척" [⊒0, ←8]
      - `ctx:HopperBladeWork` "호퍼 내부 날"
      - `ctx:LaminatingRoller` "접지기 롤러"
      - `ctx:MeatGrinding` "meat grinding"
      - `ctx:MeatSlicer` "meat slicer"
      - `ctx:NailGun` "타카·네일건 작업" [⊒0, ←6]
      - `ctx:PressMachine` "프레스 기계 작업" [⊒0, ←10]
      - `ctx:PrintingPress` "printing press"
      - `ctx:RollerMachine` "회전 롤러"
      - `ctx:Sanding` "샌딩·연마 작업" [⊒0, ←6]
      - `ctx:Sawing` "톱 절단 작업" [⊒0, ←6]
      - `ctx:ScrewGrinder` "분쇄기 스크루"
      - `ctx:WashingMachine` "세탁기 작업" [⊒0, ←4]
      - `ctx:Welding` "welding" [⊒0, ←4]
      - `ctx:WeldingRepair` "차체 용접·수리" [⊒0, ←6]
    - `ctx:MaterialHandling` "하역·운반" [⊒19, ←3433]
      - `ctx:BoxHandling` "박스 운반·적재" [⊒0, ←4]
      - `ctx:CatHandling` "고양이 취급" [⊒0, ←8]
      - `ctx:ColdStorage` "냉장·냉동 창고" [⊒0, ←14]
      - `ctx:FertilizerHandling` "비료 취급" [⊒0, ←8]
      - `ctx:FlourHandling` "flour handling"
      - `ctx:GarmentSorting` "세탁물 분류" [⊒0, ←8]
      - `ctx:HeavyFishBox` "heavy fish box"
      - `ctx:HeavyFurniture` "heavy furniture"
      - `ctx:HeavyLifting` "중량물 취급" [⊒0, ←6]
      - `ctx:HeavyMeatHandling` "heavy meat handling"
      - `ctx:HighShelfWork` "높은 선반 작업" [⊒0, ←8]
      - `ctx:IceHandling` "ice handling"
      - `ctx:LiftWork` "자동차 리프트 작업" [⊒0, ←6]
      - `ctx:LoadingDock` "하역 도크" [⊒0, ←6]
      - `ctx:MedicationHandling` "medication handling"
      - `ctx:OverloadedHandcart` "과적 운반도구"
      - `ctx:PackageSorting` "택배 분류" [⊒0, ←8]
      - `ctx:ShelfStocking` "매장 선반 진열" [⊒0, ←8]
      - `ctx:StorageShelf` "선반 적재" [⊒0, ←26]
    - `ctx:NoiseWork` "소음작업" [⊒1, ←585]
      - `ctx:NoiseExposure` "소음 노출 작업" [⊒0, ←4]
    - `ctx:Passage` "통로" [⊒2, ←1113]
      - `ctx:AisleObstruction` "통로 장애물"
      - `ctx:WalkwayObstruction` "통행 경로 장애물"
    - `ctx:PathogenWork` "병원체 취급작업" [⊒8, ←10]
      - `ctx:AcupunctureWork` "acupuncture work"
      - `ctx:AutoclaveSterilization` "autoclave sterilization"
      - `ctx:BiomedicalWaste` "biomedical waste"
      - `ctx:BodyTransport` "body transport"
      - `ctx:CremationFurnace` "cremation furnace"
      - `ctx:DentalProcedure` "dental procedure"
      - `ctx:Embalming` "embalming"
      - `ctx:FuneralHallSetup` "funeral hall setup"
    - `ctx:PressureVessel` "압력용기" [⊒0, ←1825]
    - `ctx:RadiationWork` "방사선작업" [⊒0, ←12]
    - `ctx:Rail` "철도" [⊒0, ←155]
    - `ctx:Robot` "로봇" [⊒0, ←113]
    - `ctx:Scaffold` "비계" [⊒7, ←492]
      - `ctx:ClimbingWall` "climbing wall"
      - `ctx:ExteriorRope` "exterior rope"
      - `ctx:HighRiseWindow` "high rise window"
      - `ctx:Ladder` "ladder" [⊒0, ←6]
      - `ctx:LadderInterior` "실내 사다리 작업" [⊒0, ←4]
      - `ctx:RopeAccess` "rope access" [⊒0, ←6]
      - `ctx:ScaffoldWork` "scaffold work"
    - `ctx:Steelwork` "철골작업" [⊒0, ←352]
    - `ctx:UnknownContext` "미상 작업맥락" [⊒71, ←73]
      - `ctx:AcrophobiaWork` "고소 공포"
      - `ctx:AnimalFeeding` "동물 급식" [⊒0, ←8]
      - `ctx:BracketDefect` "브래킷 이상"
      - `ctx:BystanderWorkerExposure` "주변 작업자 노출"
      - `ctx:CageCleaning` "케이지 청소" [⊒0, ←6]
      - `ctx:CardioEquipment` "cardio equipment"
      - `ctx:CashierArea` "계산대 주변 작업" [⊒0, ←6]
      - `ctx:CleaningNight` "야간 청소" [⊒0, ←6]
      - `ctx:CleaningWet` "물청소" [⊒0, ←18]
      - `ctx:CommunicationFailure` "통신 단절"
      - `ctx:CrowdManagement` "과밀 인원 관리" [⊒0, ←8]
      - `ctx:DisplaySetup` "display setup"
      - `ctx:DogGrooming` "강아지 미용" [⊒0, ←8]
      - `ctx:EvBattery` "전기차 고전압 배터리 작업" [⊒0, ←4]
      - `ctx:ExerciseClass` "exercise class"
      - `ctx:ExpiredMedicationUse` "만료 에피펜 무효"
      - `ctx:FilterMaintenance` "기름때 필터"
      - `ctx:FirstAidFailure` "응급 처치 실패"
      - `ctx:FishCutting` "fish cutting"
      - `ctx:FloralArrangement` "floral arrangement"
      - `ctx:FreeWeightZone` "free weight zone"
      - `ctx:GreenhouseWork` "온실 작업" [⊒0, ←8]
      - `ctx:HairWash` "샴푸·세정 작업" [⊒0, ←4]
      - `ctx:HandrailDefect` "난간 불량"
      - `ctx:HarvestWork` "수확 작업" [⊒0, ←6]
      - `ctx:InteriorCleaning` "차량 내부 청소" [⊒0, ←4]
      - `ctx:InterlockBypass` "인터록 우회 가능성"
      - `ctx:Irrigation` "관개 작업" [⊒0, ←8]
      - `ctx:KnifeWork` "knife work"
      - `ctx:LandfillOperation` "landfill operation"
      - `ctx:LooseSafetyCover` "헐거운 안전 덮개"
      - `ctx:LotoNotApplied` "LOTO 미적용"
      - `ctx:NearbyWorkerProximity` "주변 작업자 접근"
      - `ctx:NightSolo` "야간 단독 근무" [⊒0, ←6]
      - `ctx:NightSoloWork` "야간 단독 작업" [⊒0, ←10]
      - `ctx:ObstructedViewCarrying` "시야 차단 운반"
      - `ctx:OutdoorPlayEquipment` "outdoor play equipment"
      - `ctx:OvenOperation` "oven operation"
      - `ctx:OverloadedContainer` "과적 컨테이너"
      - `ctx:PetBathing` "반려동물 목욕" [⊒0, ←10]
      - … (+31 more 하위, inspect_node.py --list 로 확인)
    - `ctx:Vehicle` "차량" [⊒2, ←1569]
      - `ctx:DeliveryRider` "배달 운행" [⊒0, ←18]
      - `ctx:ForkliftOperation` "지게차 작업" [⊒0, ←10]
    - `ctx:Ventilation` "환기작업" [⊒1, ←1769]
      - `ctx:VentilationPoor` "환기 불량 작업" [⊒0, ←10]
  - `haz:AccidentType` "사고 유형" [⊒23, ←58] ⊑(obo:BFO_0000019)
    - `haz:AnimalInjury` "동물상해" [⊒1, ←3]
      - `haz:AnimalBite` "교상"
    - `haz:CaughtIn` "끼임" [⊒9, ←2578]
      - `haz:CaughtInConfinedSpace` "밀폐 공간 끼임"
      - `haz:CompressionInjury` "압상"
      - `haz:Crush` "끼임(압착)"
      - `haz:DriverEntanglement` "드라이버 말림"
      - `haz:Entanglement` "신체 말림"
      - `haz:FootCrushInjury` "발 압상"
      - `haz:PtoEntanglement` "PTO 회전 말림 사고"
      - `haz:RotatingHookEntanglement` "회전 훅 말림"
      - `haz:RotatingPartInjury` "회전체 부상"
    - `haz:ChemicalExposure` "화학물질누출접촉" [⊒39, ←44]
      - `haz:ChemicalAbsorptionThroughSkin` "피부 화학 흡수"
      - `haz:ChemicalAccidentDueToImproperDetergentUse` "잘못된 세제 사용 화학 사고"
      - `haz:ChemicalDetergentInhalation` "화학 세제 흡입"
      - `haz:ChemicalEyeAndAirwayInjury` "눈·기도 화학 손상"
      - `haz:ChemicalIngestion` "화학 물질 경구 섭취"
      - `haz:ChemicalInhalation` "화학 흡입"
      - `haz:ChemicalIrritation` "화학 자극"
      - `haz:ChemicalResidualInhalation` "화학 잔류 흡입"
      - `haz:ChemicalSkinIrritation` "피부 화학 자극"
      - `haz:ChemicalVaporExposure` "화학 증기 노출"
      - `haz:ChemicalVaporInhalation` "화학 증기 흡입"
      - `haz:ChemicalVaporInhalationUnconsciousness` "화학 증기 흡입 의식 불명"
      - `haz:ChildChemicalExposure` "아동 화학 노출"
      - `haz:ChloramineGasInhalationPoisoning` "클로라민 가스 흡입 중독"
      - `haz:ChlorineGasInhalationPoisoning` "염소 가스 흡입 중독"
      - `haz:CytotoxicExposure` "세포독성 노출"
      - `haz:DetergentInhalationPoisoning` "세제 흡입 중독"
      - `haz:EyeChemicalInjury` "눈 화학 손상"
      - `haz:FertilizerDustInhalation` "비료 분진 흡입"
      - `haz:FoodContamination` "식품 오염"
      - `haz:FuelLeakVaporInhalation` "연료 누출 증기 흡입"
      - `haz:GasLeak` "가스 누출"
      - `haz:GasLeakAtNight` "야간 가스 누출"
      - `haz:GasPoisoning` "가스 중독"
      - `haz:GradualMinorFuelLeakage` "소량 연료 점진적 누출"
      - `haz:HighPressureGasLeakage` "고압 가스 누출"
      - `haz:HydrocarbonVaporInhalationPoisoning` "탄화수소 증기 흡입 중독"
      - `haz:InhalationOfChemicalDust` "약품 분진 흡입"
      - `haz:MercuryPoisoning` "수은 중독"
      - `haz:NarcoticDermalAbsorption` "마약 성분 피부 흡수"
      - `haz:PesticideAbsorptionThroughSkin` "잔류 농약 피부 흡수"
      - `haz:PesticideEyeContact` "농약 눈 접촉"
      - `haz:PesticideInhalationPoisoning` "농약 흡입 중독"
      - `haz:ResidualCleanerExposure` "잔류 세정제 노출"
      - `haz:SkinContact` "피부 접촉"
      - `haz:SkinEyeContactChemicalInjury` "피부·눈 접촉 화학 부상"
      - `haz:SkinIrritation` "피부 자극"
      - `haz:ToxicGasInhalation` "독성 가스 흡입"
      - `haz:ToxicGasPoisoning` "유해 가스 중독"
    - `haz:Collapse` "붕괴" [⊒5, ←2516]
      - `haz:LandfillSlopeCollapse` "매립지 사면 붕괴"
      - `haz:LoadCollapse` "적재물 붕괴"
      - `haz:ScaffoldCollapse` "비계 붕괴"
      - `haz:ShelfCollapse` "선반 붕괴"
      - `haz:SoilCollapse` "토사 붕괴"
    - `haz:Collision` "충돌" [⊒2, ←6350]
      - `haz:MachineCollisionInjury` "기계 충돌 부상"
      - `haz:TrayContactInjury` "트레이 접촉 부상"
    - `haz:CrushedOverturned` "깔림뒤집힘" [⊒6, ←8]
      - `haz:CartTipover` "카트 전복"
      - `haz:CrushedByMachineOrObject` "작업자 압사"
      - `haz:HandcartOverturn` "리어카 전복"
      - `haz:HeavyEquipmentOverturn` "중장비 전복"
      - `haz:LockerTipover` "사물함 전도"
      - `haz:TractorTipover` "농기계 전복"
    - `haz:CutLaceration` "절단베임찔림" [⊒18, ←2000]
      - `haz:BladeLaceration` "칼날 절상"
      - `haz:ChildCut` "아동 절단"
      - `haz:ChildStabbing` "아동 찔림"
      - `haz:Cut` "절단"
      - `haz:CutDueToGloveFailure` "장갑 성능 저하로 인한 절상"
      - `haz:CuttingBladeContactWhileOperating` "가동 중 칼날 절단"
      - `haz:ElectricalAccidentDueToPowerInstability` "전원 불안정으로 인한 전기 사고"
      - `haz:FingerAmputation` "손가락 절단"
      - `haz:FingerInjury` "손가락 부상"
      - `haz:GlassLaceration` "유리 절상"
      - `haz:Laceration` "베임"
      - `haz:PalmLaceration` "손바닥 열상"
      - `haz:PruningShearLaceration` "전지가위 절상"
      - `haz:Puncture` "찔림"
      - `haz:Scratch` "할큄"
      - `haz:SharpObjectInjury` "예리물 상해"
      - `haz:SkinPenetration` "피부 침투"
      - `haz:ThresherBladeCut` "탈곡 날 절단"
    - `haz:Drowning` "빠짐익사" [⊒0, ←2]
    - `haz:ElectricShock` "감전" [⊒2, ←8]
      - `haz:ChildElectricShock` "아동 감전"
      - `haz:ElectricShockDueToInsulationDamage` "피복 손상 감전"
    - `haz:ErgonomicStrain` "불균형및무리한동작" [⊒5, ←768]
      - `haz:Ergonomic` "근골격계"
      - `haz:HeavyLifting` "중량물 취급"
      - `haz:LossOfBalance` "균형 상실"
      - `haz:Posture` "부적절한 작업자세"
      - `haz:Repetitive` "반복 동작"
    - `haz:Explosion` "폭발파열" [⊒8, ←10]
      - `haz:ChemicalExplosion` "화학 폭발"
      - `haz:ChemicalReactionExplosion` "화학 반응 폭발"
      - `haz:DustExplosion` "분진 폭발"
      - `haz:FireAndExplosion` "화재·폭발"
      - `haz:FuelGasExplosion` "연료 가스 폭발"
      - `haz:FuelIgnitionExplosion` "연료 점화 폭발"
      - `haz:HighPressureRelease` "고압 분출"
      - `haz:PressureVesselExplosion` "압력 용기 폭발"
    - `haz:Fall` "추락" [⊒13, ←3752]
      - `haz:ChairTipoverFall` "의자 전도 추락"
      - `haz:FallDueToStrongWind` "강풍으로 인한 추락"
      - `haz:FallFromAnkerFailure` "앵커 파손으로 인한 추락"
      - `haz:FallFromHeight` "고소 추락"
      - `haz:FallFromLadder` "사다리 추락"
      - `haz:FallFromLossOfBalance` "균형 상실 추락"
      - `haz:FallFromRopeFrictionBreakage` "로프 마찰 파단 추락"
      - `haz:FallOnGround` "추락 시 지면 충돌"
      - `haz:GondolaOverturnFall` "곤돌라 전복 추락"
      - `haz:HotObjectMultipleFalling` "고온 트레이 다수 낙하"
      - `haz:PatientFall` "환자 낙상"
      - `haz:RopeBreakFall` "로프 파단 추락"
      - `haz:UserFall` "이용자 낙상"
    - `haz:FireInjury` "화재" [⊒9, ←14]
      - `haz:FireFromOutletOverload` "콘센트 과부하 화재"
      - `haz:FireSpread` "화재 확산"
      - `haz:FuelFire` "연료 화재"
      - `haz:FuelTankFire` "연료통 화재"
      - `haz:FuelVaporIgnitionByStaticDischarge` "정전기 방전으로 인한 연료 증기 점화"
      - `haz:IgnitionOfFlammableGas` "인화성 가스 점화"
      - `haz:OverloadFire` "과부하 화재"
      - `haz:SpontaneousCombustionOfAbsorbentPad` "흡착포 자연 발화"
      - `haz:TrashBinFire` "쓰레기통 화재"
    - `haz:OffSiteTraffic` "사업장외교통사고" [⊒0, ←2]
    - `haz:OtherAccident` "기타" [⊒0, ←6]
    - `haz:OxygenDeficiency` "산소결핍" [⊒1, ←3]
      - `haz:ConfinedSpaceAsphyxia` "밀폐 공간 질식"
    - `haz:SlipTrip` "넘어짐" [⊒5, ←1192]
      - `haz:ChildSlipAndFall` "아동 미끄러짐"
      - `haz:FallFromKnotSlip` "매듭 이탈 추락"
      - `haz:KnifeSlipCut` "칼 미끄러짐"
      - `haz:Slip` "미끄러짐"
      - `haz:StairTrip` "계단 전도"
    - `haz:SportsEventInjury` "체육행사" [⊒0, ←2]
    - `haz:StruckBy` "맞음" [⊒8, ←2186]
      - `haz:BurnFromFallingHotContents` "고온 내용물 낙하 화상"
      - `haz:FallingChemicalContainer` "화학 용기 낙하"
      - `haz:FallingFromWires` "전선 당김 낙하"
      - `haz:FallingObject` "낙하물"
      - `haz:MachineFallingCollisionInjury` "기계 낙하 충돌 부상"
      - `haz:StruckByIceFragment` "얼음 파편 충격"
      - `haz:StruckBySharpObject` "날에 의한 부상"
      - `haz:TvFalling` "TV 낙하"
    - `haz:TempExtremeContact` "이상온도물체접촉" [⊒16, ←19]
      - `haz:ArcBurn` "아크 화상"
      - `haz:Burn` "화상"
      - `haz:BurnFromAccidentalCustomerContact` "고객 우발적 접촉 화상"
      - `haz:ChemicalBurn` "화학 화상"
      - `haz:ChemicalBurnFromStrongAcid` "강산 화학 화상"
      - `haz:ChemicalBurnFromStrongAcidToEye` "강산 눈 화학 화상"
      - `haz:ChemicalSkinBurn` "화학물질 피부 화상"
      - `haz:ColdBurn` "저온 화상"
      - `haz:ColdExposure` "저온 노출"
      - `haz:ExtremeColdBurn` "극저온 화상"
      - `haz:HandBurn` "왼손 맨손 화상"
      - `haz:HighTemperatureBurn` "고온 화상"
      - `haz:HotSteamBurn` "고온 증기 화상"
      - `haz:ResidualHeatBurn` "잔열 화상"
      - `haz:SkinBurn` "피부 화상"
      - `haz:SteamBurn` "증기 화상"
    - `haz:Unclassified` "분류불능" [⊒10, ←12]
      - `haz:ContainerBreakageDuringCollection` "수거 중 컨테이너 파손"
      - `haz:EyeForeignBody` "눈 이물"
      - `haz:EyeVisionDamage` "시력 손상"
      - `haz:Fracture` "골절"
      - `haz:InfantSafetyAccident` "유아 안전사고"
      - `haz:Infection` "감염"
      - `haz:LabelMisidentificationAccident` "라벨 오인 사고"
      - `haz:LossOfControlPolisher` "제어 상실 폴리셔"
      - `haz:MedicalEmergency` "의료 응급"
      - `haz:OvercrowdingEvacuationDelay` "과밀로 인한 탈출 지연"
    - `haz:Violence` "폭력행위" [⊒0, ←2]
    - `haz:WorkplaceTraffic` "사업장내교통사고" [⊒1, ←3]
      - `haz:TrafficAccident` "교통사고"
  - `risk:NaturalLanguageHazardCategory` "자연어 위험요소 카테고리" [⊒0, ←24]
- `risk:RiskPattern` "위험 패턴" [⊒1, ←2] ⊑(obo:BFO_0000019)
  - `she:SituationalHazardPattern` "위험상황 패턴" [⊒0, ←987] ⊑(obo:BFO_0000019, +제약4)
- `she:VisualTrigger` "시각 트리거" [⊒0, ←1627] ⊑(obo:BFO_0000019)
- `sr:RequirementType` "요구사항 유형" [⊒0, ←8] ⊑(lkif:Norm)
- `sr:SafetyRequirement` "안전요구사항" [⊒0, ←46] ⊑(lkif:Obligation, +제약5)

## 3. 속성 (predicate)

### Object Properties (132)

| property | label | domain | range |
|---|---|---|---|
| `app:basedOnObservation` | 근거 관찰 | app:HazardFinding | app:VisualObservation |
| `app:citesRequirement` | 인용 안전요구사항 | app:CorrectiveAction | sr:SafetyRequirement |
| `app:forAction` | 대상 개선 조치 | app:ActionRecommendation | app:CorrectiveAction |
| `app:guidedBy` | 개선 조치 참고 가이드 | app:CorrectiveAction | guide:KoshaGuide |
| `app:hasAction` | 조치 보유 | app:CorrectiveActionPlan | app:CorrectiveAction |
| `app:hasActionRecommendation` | 조치 추천 항목 보유 | app:CorrectiveAction | app:ActionRecommendation |
| `app:hasFinding` | 위험 판단 보유 | app:InspectionCase | app:HazardFinding |
| `app:hasFindingStatus` | 판정 상태 | app:HazardFinding | app:FindingStatus |
| `app:hasObservation` | 관찰 사실 보유 | app:UploadedPhoto | app:VisualObservation |
| `app:hasPenaltyExposure` | 벌칙 노출 보유 | app:HazardFinding | app:PenaltyExposure |
| `app:hasPenaltyExposureStatus` | 벌칙 노출 상태 | app:PenaltyExposure | app:PenaltyExposureStatus |
| `app:hasPenaltyLevel` | 벌칙 심각도 | app:PenaltyExposure | app:PenaltyLevel |
| `app:hasPenaltyResult` | 벌칙 결과 | app:PenaltyExposure | pen:PenaltyResult |
| `app:hasPhoto` | 사진 보유 | app:InspectionCase | app:UploadedPhoto |
| `app:hasSituationMatch` | 상황 매칭 보유 | app:HazardFinding | app:SituationMatch |
| `app:hasTemporalStage` | 시간 단계 보유 (상황 매칭) | app:SituationMatch | ctx:TemporalStage |
| `app:hasVisualCue` | 시각 단서 보유 | app:VisualObservation | app:VisualCue |
| `app:indicatesNoncompliance` | 비준수 지시 | app:Noncompliance | app:VisualObservation |
| `app:mappedTo` | 정규화 매핑 | app:VisualCue | risk:RiskFeature |
| `app:matchesProcess` | 프로세스 매칭 | app:SituationMatch | guide:WorkProcess |
| `app:matchesSituation` | 매칭 위험상황 | app:SituationMatch | she:SituationalHazardPattern |
| `app:possiblePenalty` | 가능 벌칙 | app:PenaltyExposure | pen:PenaltyRule |
| `app:recommendedRequirement` | 추천 안전요구사항 | app:ActionRecommendation | sr:SafetyRequirement |
| `app:recommendsAction` | 권장 개선 조치 | app:HazardFinding | app:CorrectiveAction |
| `app:temporalStageForProcess` | 프로세스 시간 단계 | guide:WorkProcess | ctx:TemporalStage |
| `app:usesChecklistCue` | 보조 체크리스트 단서 | app:CorrectiveAction | guide:ChecklistItem |
| `bridge:appliesTo` | 적용 (브리지) | sr:SafetyRequirement | — |
| `bridge:observedIn` | 관찰됨 (브리지) | — | — |
| `bridge:violatesObligation` | 의무 위반 | actor:Worker | law:NormStatement |
| `core:broaderAgent` | 상위 유해인자 (custom broader) | agent:HazardousAgent | agent:HazardousAgent |
| `core:coApplicable` | 공동 적용 | sr:SafetyRequirement | sr:SafetyRequirement |
| `core:dependsOn` | 위험 의존 | sr:SafetyRequirement | sr:SafetyRequirement |
| `core:exemptedBy` | 면제 근거 | law:NormStatement | law:NormStatement |
| `core:hasViolation` | 위반 관계 | — | — |
| `core:incompatibleDomainA` | 도메인 A | core:Incompatibility | industry:Industry |
| `core:incompatibleDomainB` | 도메인 B | core:Incompatibility | industry:Industry |
| `core:observedIn` | 관찰 문맥 | app:VisualObservation | ctx:WorkContext |
| `guide:addressesHazard` | 직접 위험 대응 (Guide) | guide:KoshaGuide | haz:AccidentType |
| `guide:basedOnSR` | SR 기반 | guide:ChecklistItem | sr:SafetyRequirement |
| `guide:bundlesControl` | control 묶음 | guide:KoshaGuide | guide:CanonicalChecklistItem |
| `guide:ciAddressesAccidentType` | CI 대응 사고유형 | guide:ChecklistItem | haz:AccidentType |
| `guide:ciAddressesAgent` | CI 대응 유해인자 | guide:ChecklistItem | agent:HazardousAgent |
| `guide:ciInWorkContext` | CI 작업맥락 | guide:ChecklistItem | ctx:WorkContext |
| `guide:controlBundledBy` | 묶은 Guide | guide:CanonicalChecklistItem | guide:KoshaGuide |
| `guide:docForSR` | SR 관련 문서 | guide:DocumentRequirement | sr:SafetyRequirement |
| `guide:equipmentHasSpec` | 장비 스펙 보유 | guide:Equipment | guide:EquipmentSpec |
| `guide:guideAddressesAgent` | 직접 유해인자 대응 (Guide) | guide:KoshaGuide | agent:HazardousAgent |
| `guide:guideAppliesToContext` | 직접 작업맥락 적용 (Guide) | guide:KoshaGuide | ctx:WorkContext |
| `guide:hasChecklistItem` | 점검항목 보유 | guide:KoshaGuide | guide:ChecklistItem |
| `guide:hasDocumentRequirement` | 문서요구사항 보유 | guide:KoshaGuide | guide:DocumentRequirement |
| `guide:hasDomainTerm` | 도메인용어 보유 | guide:KoshaGuide | guide:DomainTerm |
| `guide:hasEquipmentSpec` | 장비규격 보유 | guide:KoshaGuide | guide:EquipmentSpec |
| `guide:hasProfile` | has profile | guide:KoshaGuide | guide:GuideUsageProfile |
| `guide:hasWorkProcess` | 작업프로세스 보유 | guide:KoshaGuide | guide:WorkProcess |
| `guide:isChecklistItemOf` | 소속 가이드 | guide:ChecklistItem | guide:KoshaGuide |
| `guide:profileOfGuide` | profile of guide | guide:GuideUsageProfile | guide:KoshaGuide |
| `guide:realizesControl` | control 실현 | guide:ChecklistItem | guide:CanonicalChecklistItem |
| `guide:realizesSHE` | 실현하는 상황 | guide:ChecklistItem | she:SituationalHazardPattern |
| `guide:referencesGuide` | 가이드 상호참조 | guide:KoshaGuide | guide:KoshaGuide |
| `guide:relatedSR` | 관련 SR | guide:WorkProcess | sr:SafetyRequirement |
| `guide:specForSR` | SR용 규격 | guide:EquipmentSpec | sr:SafetyRequirement |
| `guide:termForSR` | SR 관련 용어 | guide:DomainTerm | sr:SafetyRequirement |
| `haz:hasHazard` | 위험 유형 | risk:RiskFeature | haz:AccidentType |
| `law:appliesArticle` | Article 적용 (강화) | sr:SafetyRequirement | law:Article |
| `law:belongsToChapter` | 소속 장 | — | — |
| `law:belongsToPart` | 소속 편 | — | — |
| `law:belongsToSection` | 소속 절 | — | — |
| `law:belongsToSubsection` | 소속 관 | — | — |
| `law:groundedBySR` | SR 근거 | law:NormStatement | sr:SafetyRequirement |
| `law:hasArticle` | Article 보유 (NS) | law:NormStatement | law:Article |
| `law:hasLawType` | 법령 유형 | law:Article | law:LawType |
| `law:hasModality` | 모달리티 | law:NormStatement | core:Modality |
| `law:hasNormStatement` | 규범 진술문 보유 | — | — |
| `law:hasParentStructure` | 상위 구조 | — | — |
| `law:hasSourceArticle` | 출처 조문 | law:NormStatement | law:Article |
| `law:hasSubjectRole` | 의무 주체 | law:NormStatement | core:SubjectRole |
| `law:modifiedBy` | 수정됨 | — | — |
| `law:modifies` | 수정 대상 | law:NormStatement | law:NormStatement |
| `law:modifiesAsymmetric` | 수정 (비대칭) | law:NormStatement | law:NormStatement |
| `pen:appliesPenaltyRule` | PenaltyRule 적용 (Ctx) | app:PenaltyExposure | pen:PenaltyRule |
| `pen:appliesTo` | 적용 대상 | pen:PenaltyRule | law:Article |
| `pen:appliesToExposure` | Exposure 적용 | pen:PenaltyRule | app:PenaltyExposure |
| `pen:appliesToNormStatement` | NS 적용 (벌칙) | pen:PenaltyRule | law:NormStatement |
| `pen:appliesToViaSr` | SR 통한 적용 | pen:PenaltyRule | sr:SafetyRequirement |
| `pen:delegatedFrom` | 위임 근거 | — | — |
| `pen:hasCondition` | 벌칙 선택 조건 | pen:PenaltyRule | pen:PenaltyCondition |
| `pen:hasPenaltyRule` | 벌칙 적용 규칙 | law:NormStatement | pen:PenaltyRule |
| `pen:hasSanction` | 제재 | pen:PenaltyRule | pen:SanctionType |
| `pen:penalizesNorm` | NS 제재 | pen:PenaltyRule | law:NormStatement |
| `pen:penaltyArticle` | 실제 벌칙 조문 | pen:PenaltyRule | law:Article |
| `pen:penaltyType` | 벌칙 종류 | pen:PenaltyRule | pen:SanctionType |
| `pen:requiresAccidentOutcome` | 요구 사고 결과 | pen:PenaltyCondition | pen:AccidentOutcome |
| `pen:requiresSubjectRole` | 요구 주체 역할 | pen:PenaltyCondition | core:SubjectRole |
| `pen:resultsIn` | 벌칙 결과 산출 | pen:PenaltyRule | pen:PenaltyResult |
| `pen:violatedArticle` | 위반 조문 | pen:PenaltyRule | law:Article |
| `pen:violatedNorm` | 위반 대상 규범 | pen:PenaltyRule | law:NormStatement |
| `risk:appliesToEquipment` | 장비 적용 | risk:RiskFeature | guide:Equipment |
| `risk:compatibleWithSpec` | 스펙 호환 | risk:RiskFeature | guide:EquipmentSpec |
| `risk:correspondsToHazard` | 위험 유형 대응 | risk:RiskFeature | haz:AccidentType |
| `risk:hasFeature` | 위험 특징 보유 | risk:RiskPattern | risk:RiskFeature |
| `risk:hasRiskFeature` | 위험 특징 보유 | app:VisualObservation | risk:RiskFeature |
| `risk:indicatesByCue` | 시각 단서로 지시 | risk:RiskFeature | app:VisualCue |
| `risk:mapsToCanonicalCode` | Canonical 코드 매핑 | risk:NaturalLanguageHazardCategory | risk:RiskFeature |
| `she:appliesCI` | 적용되는 체크리스트 항목 | she:SituationalHazardPattern | guide:ChecklistItem |
| `she:appliesPenalty` | 적용되는 벌칙 (PA-12 chain 결과) | she:SituationalHazardPattern | — |
| `she:appliesSR` | 적용되는 SR | she:SituationalHazardPattern | sr:SafetyRequirement |
| `she:hasAccidentType` | 사고 유형 | she:SituationalHazardPattern | haz:AccidentType |
| `she:hasAgentState` | 작업자 상태 | she:SituationalHazardPattern | ctx:AgentState |
| `she:hasEnvironmental` | 환경 요인 | she:SituationalHazardPattern | ctx:EnvironmentalFactor |
| `she:hasHazardousAgent` | 유해 인자 | she:SituationalHazardPattern | agent:HazardousAgent |
| `she:hasPPEState` | 보호구 상태 | she:SituationalHazardPattern | ctx:PPEState |
| `she:hasTemporalStage` | 시간 단계 | she:SituationalHazardPattern | ctx:TemporalStage |
| `she:hasVisualTrigger` | 시각 트리거 | she:SituationalHazardPattern | she:VisualTrigger |
| `she:hasWorkActivity` | 작업 활동 | she:SituationalHazardPattern | ctx:WorkActivity |
| `she:hasWorkContext` | 작업 맥락 | she:SituationalHazardPattern | ctx:WorkContext |
| `she:relatedChecklistCue` | 관련 체크리스트 단서 | she:SituationalHazardPattern | guide:ChecklistItem |
| `she:relatedGuide` | 관련 KOSHA 가이드 | she:SituationalHazardPattern | guide:KoshaGuide |
| `she:supersededBy` | 대체된 SHE (supersession chain) | she:SituationalHazardPattern | she:SituationalHazardPattern |
| `sr:addressesAccidentType` | 대응 사고유형 | sr:SafetyRequirement | haz:AccidentType |
| `sr:addressesAgent` | 대응 유해인자 | sr:SafetyRequirement | agent:HazardousAgent |
| `sr:addressesFeature` | 위험 특징 연결 | sr:SafetyRequirement | risk:RiskFeature |
| `sr:appliesToArticle` | 적용 조문 | sr:SafetyRequirement | law:Article |
| `sr:appliesToEquipment` | 장비 적용 (SR) | sr:SafetyRequirement | guide:Equipment |
| `sr:derivedFromNS` | NS에서 파생 | sr:SafetyRequirement | law:NormStatement |
| `sr:guidedBy` | 관련 가이드 | sr:SafetyRequirement | guide:KoshaGuide |
| `sr:hasBindingForce` | 구속력 | — | — |
| `sr:hasChecklistItem` | 점검항목 보유 | — | — |
| `sr:hasRequirementType` | 요구사항 유형 | — | — |
| `sr:hasSafetyRequirement` | 안전요구사항 보유 | — | — |
| `sr:inWorkContext` | 작업맥락 | sr:SafetyRequirement | ctx:WorkContext |
| `sr:requiresFindingStatus` | 필요 판정 상태 | sr:SafetyRequirement | app:FindingStatus |
| `sr:violatedIn` | 위반될 수 있는 상황 | sr:SafetyRequirement | she:SituationalHazardPattern |

### Data Properties (68)

| property | label | domain | range |
|---|---|---|---|
| `app:confidence` | 관찰 신뢰도 | app:VisualObservation | http://www.w3.org/2001/XMLSchema#decimal |
| `app:fileName` | 파일명 | app:UploadedPhoto | http://www.w3.org/2001/XMLSchema#string |
| `app:matchConfidence` | 매칭 신뢰도 | app:SituationMatch | http://www.w3.org/2001/XMLSchema#decimal |
| `app:matchReason` | 추천 사유 | app:ActionRecommendation | rdf:langString |
| `app:recommendationRank` | 추천 순위 | app:ActionRecommendation | http://www.w3.org/2001/XMLSchema#integer |
| `app:recommendationSource` | 추천 출처 | app:ActionRecommendation | http://www.w3.org/2001/XMLSchema#string |
| `app:visualCueText` | 시각 단서 텍스트 | app:VisualCue | http://www.w3.org/2001/XMLSchema#string |
| `core:axiomConfidence` | 공리 신뢰도 | core:Incompatibility | http://www.w3.org/2001/XMLSchema#decimal |
| `core:axiomLevel` | 공리 단계 | core:Incompatibility | http://www.w3.org/2001/XMLSchema#string |
| `core:axiomPromotedAt` | vetted 승격 시각 | core:Incompatibility | http://www.w3.org/2001/XMLSchema#dateTime |
| `core:axiomReason` | 공리 근거 | core:Incompatibility | http://www.w3.org/2001/XMLSchema#string |
| `core:axiomSource` | 공리 출처 | core:Incompatibility | http://www.w3.org/2001/XMLSchema#string |
| `core:identifier` | 식별자 | — | http://www.w3.org/2001/XMLSchema#string |
| `core:text` | 텍스트 | — | http://www.w3.org/2001/XMLSchema#string |
| `core:title` | 제목 | — | http://www.w3.org/2001/XMLSchema#string |
| `guide:additionalDetail` | 추가 상세 | guide:ChecklistItem | http://www.w3.org/2001/XMLSchema#string |
| `guide:baselineId` | baseline id | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:ciGuideFrequency` | CI Guide 중복 빈도 | guide:ChecklistItem | http://www.w3.org/2001/XMLSchema#integer |
| `guide:definition` | 정의 | guide:DomainTerm | http://www.w3.org/2001/XMLSchema#string |
| `guide:documentType` | 문서 유형 | guide:DocumentRequirement | http://www.w3.org/2001/XMLSchema#string |
| `guide:domain` | 도메인 | guide:KoshaGuide | http://www.w3.org/2001/XMLSchema#string |
| `guide:domainFamily` | 도메인 패밀리 | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:equipmentName` | 장비명 | guide:EquipmentSpec | http://www.w3.org/2001/XMLSchema#string |
| `guide:followupPolicy` | followup policy | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:guideCode` | 가이드 코드 | guide:KoshaGuide | http://www.w3.org/2001/XMLSchema#string |
| `guide:guideContext` | 가이드 컨텍스트 | guide:ChecklistItem | http://www.w3.org/2001/XMLSchema#string |
| `guide:intendedTasks` | 의도된 작업 | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:intendedWorkplaces` | 의도된 작업장 | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:isBoilerplate` | boilerplate 여부 | guide:ChecklistItem | http://www.w3.org/2001/XMLSchema#boolean |
| `guide:negativeBoundaries` | 부정 경계 | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:observableRequiredCues` | 관찰 필수 시각단서 | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:photoMatchability` | 사진 매칭 가능성 | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:ppeType` | 보호구 유형 | guide:WorkProcess | http://www.w3.org/2001/XMLSchema#string |
| `guide:procedureRole` | 절차 역할 | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:processName` | 프로세스명 | guide:WorkProcess | http://www.w3.org/2001/XMLSchema#string |
| `guide:processOrder` | 프로세스 순서 | guide:WorkProcess | http://www.w3.org/2001/XMLSchema#integer |
| `guide:profileLevel` | 프로필 수준 | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:reviewStatus` | 검토 상태 | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:safetyMeasures` | 안전조치 | guide:WorkProcess | http://www.w3.org/2001/XMLSchema#string |
| `guide:shortCode` | 단축 코드 | guide:KoshaGuide | http://www.w3.org/2001/XMLSchema#string |
| `guide:sourceGuide` | 출처 가이드 | — | http://www.w3.org/2001/XMLSchema#string |
| `guide:sourceSection` | 출처 섹션 | — | http://www.w3.org/2001/XMLSchema#string |
| `guide:termName` | 용어 | guide:DomainTerm | http://www.w3.org/2001/XMLSchema#string |
| `guide:topProcedurePolicy` | top procedure policy | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:usageSummary` | 사용 요약 | guide:GuideUsageProfile | http://www.w3.org/2001/XMLSchema#string |
| `guide:workProcessPhase` | 작업공정 단계 | guide:ChecklistItem | http://www.w3.org/2001/XMLSchema#string |
| `law:articleCode` | 조문 코드 | — | http://www.w3.org/2001/XMLSchema#string |
| `law:conditionText` | 조건 텍스트 | — | http://www.w3.org/2001/XMLSchema#string |
| `law:conditionType` | 조건 유형 | — | http://www.w3.org/2001/XMLSchema#string |
| `law:fullText` | 전문 | — | http://www.w3.org/2001/XMLSchema#string |
| `law:hasAction` | 행위 | — | http://www.w3.org/2001/XMLSchema#string |
| `law:hasObject` | 대상 | — | http://www.w3.org/2001/XMLSchema#string |
| `law:isDeleted` | 삭제 여부 | — | http://www.w3.org/2001/XMLSchema#boolean |
| `law:paragraphCount` | 항 수 | — | http://www.w3.org/2001/XMLSchema#integer |
| `law:paragraphRef` | 항 참조 | — | http://www.w3.org/2001/XMLSchema#string |
| `law:structureLabel` | 구조 라벨 | — | http://www.w3.org/2001/XMLSchema#string |
| `pen:fineDescription` | 벌금 설명 | pen:PenaltyRule | http://www.w3.org/2001/XMLSchema#string |
| `pen:hasPenalty` | 벌칙 여부 | — | http://www.w3.org/2001/XMLSchema#boolean |
| `pen:maxFine` | 최대 벌금/과태료 | pen:PenaltyRule | http://www.w3.org/2001/XMLSchema#decimal |
| `pen:maxPrisonYears` | 최대 징역 연수 | pen:CriminalSanction | http://www.w3.org/2001/XMLSchema#decimal |
| `pen:penaltyBasisText` | 벌칙 근거 문구 | pen:PenaltyRule | http://www.w3.org/2001/XMLSchema#string |
| `pen:penaltyDescription` | 벌칙 내용 | — | http://www.w3.org/2001/XMLSchema#string |
| `pen:severityScore` | 심각도 점수 | — | http://www.w3.org/2001/XMLSchema#integer |
| `risk:catalogConfidence` | 카탈로그 매핑 신뢰도 | risk:NaturalLanguageHazardCategory | http://www.w3.org/2001/XMLSchema#decimal |
| `she:triggerPattern` | 시각 트리거 패턴 | she:VisualTrigger | http://www.w3.org/2001/XMLSchema#string |
| `she:triggerText` | 시각 트리거 문구 | she:VisualTrigger | rdfs:Literal |
| `she:validFrom` | 유효 시작일 (법령 시행일) | she:SituationalHazardPattern | http://www.w3.org/2001/XMLSchema#date |
| `she:validUntil` | 유효 종료일 (deprecate 시점) | she:SituationalHazardPattern | http://www.w3.org/2001/XMLSchema#date |

## 4. ⚠️ 자동 이상징후 점검

> ⚠️ ref/dead는 **대용량 kosha-instances.ttl(코퍼스) 제외** 집계 — guide/core/app 등 코퍼스에 instance가 있는 클래스의 dead/ref는 신뢰 불가(코퍼스에서 live일 수 있음). facet(haz/agent/ctx) fine 코드는 canonical-ci 포함이라 정확. 제거 전 반드시 코퍼스 포함 재확인.

**(a) facet 클래스인데 risk:RiskFeature 미도달(floating): 0**

  ✅ 없음 (모든 facet 클래스가 risk:RiskFeature까지 연결).

**(b) rdfs:label 없는 클래스: 0**


**(c) dead 후보(하위0·피참조0·개체아님): 345**

  `agent:AcrylateResinSkinContact`, `agent:AirlessResidualPressure`, `agent:AsbestosDust`, `agent:Benzene`, `agent:BiogasMethane`, `agent:BloodbornePathogen`, `agent:CapacitorResidualVoltage`, `agent:ChlorineAmmoniaReaction`, `agent:ColdFloor`, `agent:ConcentratedAlkali`, `agent:ContaminatedFilterParticulateMold`, `agent:CryogenicAgent`, `agent:DefectiveHandle`, `agent:DefectiveSterilePackaging`, `agent:DegradedDeveloperSolution`, `agent:DentalXRay`, `agent:DentalXrayRepeatedExposure`, `agent:DistributionBoard`, `agent:EarphoneNoise`, `agent:ElectricalOverload`, `agent:ElectricityWaterContact`, `agent:ElevatorPitToxicGas`, `agent:ExposedOutlet`, `agent:ExtremeColdEnvironment`, `agent:ExtremeColdSurface`, `agent:FemaleExposureLimitExceeded`, `agent:FormaldehydeSkinContact`, `agent:FragranceVapor`, `agent:FuelSaturatedAbsorbent`, `agent:GasolineMicroLeakage`, `agent:GasolineVapor`, `agent:GlutaraldehydeVapor`, `agent:HighHeat`, `agent:HighPressureAirDust`, `agent:HighTemperatureEnvironment`, `agent:HighTemperatureSteam`, `agent:HotEquipment`, `agent:HotParts`, `agent:HotSurface`, `agent:HotTray` …

**(d) 중복 label(같은 한글 라벨, 다른 IRI): 7쌍**

  - "근로자": `actor:Worker`, `core:Worker`
  - "기타": `ctx:OtherAgentState`, `haz:OtherAccident`, `industry:Industry_OTHER`
  - "비상대응": `ctx:EmergencyResponse`, `sr:EmergencyResponse`
  - "전기 과부하": `agent:ElectricalOverload`, `ctx:ElectricalOverload`
  - "정비": `ctx:Maintenance`, `industry:Industry_MAINTENANCE`
  - "중량물 취급": `ctx:HeavyLifting`, `haz:HeavyLifting`
  - "화재·폭발": `agent:Fire`, `haz:FireAndExplosion`

**(e) domain 또는 range 누락 property: 34**

  `bridge:appliesTo`, `bridge:observedIn`, `core:hasViolation`, `core:identifier`, `core:text`, `core:title`, `guide:sourceGuide`, `guide:sourceSection`, `law:articleCode`, `law:belongsToChapter`, `law:belongsToPart`, `law:belongsToSection`, `law:belongsToSubsection`, `law:conditionText`, `law:conditionType`, `law:fullText`, `law:hasAction`, `law:hasNormStatement`, `law:hasObject`, `law:hasParentStructure`, `law:isDeleted`, `law:modifiedBy`, `law:paragraphCount`, `law:paragraphRef`, `law:structureLabel`, `pen:delegatedFrom`, `pen:hasPenalty`, `pen:penaltyDescription`, `pen:severityScore`, `she:appliesPenalty`, `sr:hasBindingForce`, `sr:hasChecklistItem`, `sr:hasRequirementType`, `sr:hasSafetyRequirement`

**(f) punned IRI(class+individual 동시, 정상이지만 참고): 141**

  141개 — facet canonical punning 설계(haz:Fall 등). 표본: `agent:ArcFlash`, `agent:Biological`, `agent:Chemical`, `agent:Corrosion`, `agent:Dust`, `agent:Electricity`, `agent:Fire`, `agent:HeatCold`, `agent:Noise`, `agent:Radiation`, `agent:Toxic`, `agent:UnknownAgent` …

