# KOSHA 온톨로지 카탈로그

> AUTO-GENERATED (scripts/gen_catalog.py) — 수동편집 금지. Generated: 2026-05-31T10:54:18+00:00
> 소스: serving TBox+facet+moderate ABox (37 files, 518,950 triples; 대용량 instances 제외)
> class 627 · objectProperty 133 · dataProperty 68 · individual 234

## 1. 모듈 개요 (prefix)

| prefix | class | objProp | dataProp | individual | namespace |
|---|--:|--:|--:|--:|---|
| `risk:` | 3 | 7 | 1 | 0 | `https://cashtoss.info/ontology/risk#` |
| `haz:` | 182 | 1 | 0 | 23 | `https://cashtoss.info/ontology/risk/hazard#` |
| `agent:` | 85 | 0 | 0 | 12 | `https://cashtoss.info/ontology/risk/agent#` |
| `ctx:` | 221 | 0 | 0 | 155 | `https://cashtoss.info/ontology/risk/context#` |
| `she:` | 2 | 15 | 4 | 0 | `https://cashtoss.info/ontology/risk/situation#` |
| `sr:` | 2 | 15 | 0 | 8 | `https://cashtoss.info/ontology/sr#` |
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
    - `agent:Biological` "생물학적" [⊒3, ←557]
      - `agent:BloodbornePathogen`
      - `agent:InfectiousMedicalWaste`
      - `agent:LackOfVaccination`
    - `agent:Chemical` "화학물질" [⊒17, ←12603]
      - `agent:AcrylateResinSkinContact`
      - `agent:Benzene`
      - `agent:ChlorineAmmoniaReaction`
      - `agent:ConcentratedAlkali`
      - `agent:Corrosion` "부식성물질"
      - `agent:DegradedDeveloperSolution`
      - `agent:FormaldehydeSkinContact`
      - `agent:FragranceVapor`
      - `agent:GlutaraldehydeVapor`
      - `agent:LeachateHazardousSubstance`
      - `agent:MercuryAmalgamVapor`
      - `agent:MislabeledDetergent`
      - `agent:MixedDetergentGas`
      - `agent:ResidualPesticide`
      - `agent:SolventVapor`
      - `agent:StrongAcidDescaler`
      - `agent:WaterBasedPaintMist`
    - `agent:Dust` "분진" [⊒4, ←1574]
      - `agent:AsbestosDust`
      - `agent:ContaminatedFilterParticulateMold`
      - `agent:HighPressureAirDust`
      - `agent:LeadPaintDust`
    - `agent:Electricity` "전기" [⊒8, ←8649]
      - `agent:ArcFlash` "아크"
      - `agent:CapacitorResidualVoltage`
      - `agent:DistributionBoard`
      - `agent:ElectricalOverload`
      - `agent:ElectricityWaterContact`
      - `agent:ExposedOutlet`
      - `agent:StaticElectricity`
      - `agent:TwistedWire`
    - `agent:Fire` "화재·폭발" [⊒0, ←9359]
    - `agent:HeatCold` "온도" [⊒17, ←2500]
      - `agent:ColdFloor`
      - `agent:CryogenicAgent`
      - `agent:ExtremeColdEnvironment`
      - `agent:ExtremeColdSurface`
      - `agent:HighHeat`
      - `agent:HighTemperatureEnvironment`
      - `agent:HighTemperatureSteam`
      - `agent:HotEquipment`
      - `agent:HotParts`
      - `agent:HotSurface`
      - `agent:HotTray`
      - `agent:HotWater`
      - `agent:ProlongedColdExposure`
      - `agent:ProlongedExposureToColdEnvironment`
      - `agent:RadiantHeat`
      - `agent:RepeatedExtremeColdExposure`
      - `agent:UvLampResidualHeat`
    - `agent:Noise` "소음·진동" [⊒4, ←1258]
      - `agent:EarphoneNoise`
      - `agent:KaraokeNoise`
      - `agent:KaraokeRoomNoise`
      - `agent:Noise105Db`
    - `agent:Radiation` "방사선" [⊒7, ←422]
      - `agent:DentalXRay`
      - `agent:DentalXrayRepeatedExposure`
      - `agent:RadiationExposure`
      - `agent:RadiationExposureDuringPregnancy`
      - `agent:RepeatedRadiationExposure`
      - `agent:ScatteredRadiation`
      - `agent:UltravioletRadiation`
    - `agent:Toxic` "독성물질" [⊒8, ←2992]
      - `agent:BiogasMethane`
      - `agent:ElevatorPitToxicGas`
      - `agent:FuelSaturatedAbsorbent`
      - `agent:GasolineMicroLeakage`
      - `agent:GasolineVapor`
      - `agent:ResidualCombustionGas`
      - `agent:SmallQuantityGasoline`
      - `agent:TobaccoSmoke`
    - `agent:UnknownAgent` "미상 유해인자" [⊒6, ←8]
      - `agent:AirlessResidualPressure`
      - `agent:DefectiveHandle`
      - `agent:DefectiveSterilePackaging`
      - `agent:FemaleExposureLimitExceeded`
      - `agent:ResidualRotation`
      - `agent:RopeKink`
  - `ctx:AgentState` "작업자 상태 (agent_state)" [⊒0, ←7] ⊑(obo:BFO_0000019)
  - `ctx:EnvironmentalFactor` "환경 요인 (environmental)" [⊒0, ←12] ⊑(obo:BFO_0000019)
  - `ctx:PPEState` "보호구 상태 (ppe_state)" [⊒0, ←20] ⊑(obo:BFO_0000019)
  - `ctx:TemporalStage` "시간 단계 (temporal_stage)" [⊒0, ←12] ⊑(obo:BFO_0000003)
  - `ctx:WorkActivity` "작업 활동 (work_activity)" [⊒0, ←13] ⊑(obo:BFO_0000015)
  - `ctx:WorkContext` "작업 맥락" [⊒29, ←145] ⊑(obo:BFO_0000015)
    - `ctx:ChemicalWork` "화학물질 취급작업" [⊒22, ←6160]
      - `ctx:AirlessSprayer`
      - `ctx:ChemicalApplication` "Chemical Application"
      - `ctx:ChemicalCleaning`
      - `ctx:ChemicalDisinfection`
      - `ctx:ChemicalMixing`
      - `ctx:ChemicalSpotting` "Chemical Spotting"
      - `ctx:ChemicalWaste`
      - `ctx:DryCleaningSolvent` "Dry Cleaning Solvent"
      - `ctx:FuelDispensing` "Fuel Dispensing"
      - `ctx:FuelSpill` "Fuel Spill"
      - `ctx:GasAppliance` "Gas Appliance"
      - `ctx:HairChemical` "Hair Chemical"
      - `ctx:InkSolvent`
      - `ctx:NailChemical` "Nail Chemical"
      - `ctx:OilDrain` "Oil Drain"
      - `ctx:Painting` "Painting"
      - `ctx:PaintingWoodwork` "Painting Woodwork"
      - `ctx:PesticideSpray` "Pesticide Spray"
      - `ctx:RestroomChemical`
      - `ctx:SolventHandling`
      - `ctx:SprayPainting`
      - `ctx:VaporExposure` "Vapor Exposure"
    - `ctx:CollapsePrevention` "붕괴방지 작업" [⊒0, ←1002]
    - `ctx:ConfinedSpace` "밀폐공간" [⊒5, ←1656]
      - `ctx:AquacultureTank`
      - `ctx:ConfinedCoating`
      - `ctx:ConfinedSpaceCleaning`
      - `ctx:UndergroundTank` "Underground Tank"
      - `ctx:WetConfinedSpace`
    - `ctx:ConstructionEquip` "건설장비" [⊒0, ←841]
    - `ctx:Conveyor` "컨베이어" [⊒2, ←525]
      - `ctx:ConveyorBelt` "Conveyor Belt"
      - `ctx:ConveyorWash` "Conveyor Wash"
    - `ctx:Crane` "양중기" [⊒0, ←1644]
    - `ctx:Demolition` "해체작업" [⊒0, ←1418]
    - `ctx:DustWork` "분진작업" [⊒0, ←397]
    - `ctx:ElectricalWork` "전기작업" [⊒5, ←3608]
      - `ctx:ElectricPolishingRoller`
      - `ctx:ElectricalHazard`
      - `ctx:ElectricalOverload` "Electrical Overload"
      - `ctx:LivePowerRepair`
      - `ctx:StaticElectricity` "Static Electricity"
    - `ctx:ErgonomicWork` "근골격계부담 작업" [⊒2, ←4]
      - `ctx:AwkwardPostureWork`
      - `ctx:ExcessiveMotionRange`
    - `ctx:Excavation` "굴착" [⊒0, ←1058]
    - `ctx:FallProtection` "추락방지 작업" [⊒0, ←384]
    - `ctx:FireExplosionWork` "화재·폭발 위험작업" [⊒4, ←1601]
      - `ctx:FireDetectionFailure`
      - `ctx:FireDetectorDisabled`
      - `ctx:FireEvacuation` "Fire Evacuation"
      - `ctx:FireExtinguisherDefective`
    - `ctx:HeatColdWork` "고온·저온 작업" [⊒11, ←340]
      - `ctx:ColdDisplay` "Cold Display"
      - `ctx:ColdRoomAccess`
      - `ctx:ColdRoomMortuary`
      - `ctx:DeepFrying` "Deep Frying"
      - `ctx:DryerOperation` "Dryer Operation"
      - `ctx:FoodPrep` "Food Prep"
      - `ctx:FreezerWork`
      - `ctx:HotBeverage` "Hot Beverage"
      - `ctx:HotTool` "Hot Tool"
      - `ctx:HotTrayTransport`
      - `ctx:KitchenCooking` "Kitchen Cooking"
    - `ctx:Logging` "벌목작업" [⊒0, ←153]
    - `ctx:Machine` "기계" [⊒24, ←4606]
      - `ctx:BandSaw`
      - `ctx:BreadSlicer`
      - `ctx:CompressionDeviceRestart`
      - `ctx:DoughMachine`
      - `ctx:FarmMachinery` "Farm Machinery"
      - `ctx:FloorMachine`
      - `ctx:FoldingMachine`
      - `ctx:Grinding` "Grinding"
      - `ctx:GuillotineCutter`
      - `ctx:HighPressureWash` "High Pressure Wash"
      - `ctx:HopperBladeWork`
      - `ctx:LaminatingRoller`
      - `ctx:MeatGrinding`
      - `ctx:MeatSlicer`
      - `ctx:NailGun` "Nail Gun"
      - `ctx:PressMachine` "Press Machine"
      - `ctx:PrintingPress`
      - `ctx:RollerMachine`
      - `ctx:Sanding` "Sanding"
      - `ctx:Sawing` "Sawing"
      - `ctx:ScrewGrinder`
      - `ctx:WashingMachine` "Washing Machine"
      - `ctx:Welding` "Welding"
      - `ctx:WeldingRepair` "Welding Repair"
    - `ctx:MaterialHandling` "하역·운반" [⊒19, ←3281]
      - `ctx:BoxHandling` "Box Handling"
      - `ctx:CatHandling` "Cat Handling"
      - `ctx:ColdStorage` "Cold Storage"
      - `ctx:FertilizerHandling` "Fertilizer Handling"
      - `ctx:FlourHandling`
      - `ctx:GarmentSorting` "Garment Sorting"
      - `ctx:HeavyFishBox`
      - `ctx:HeavyFurniture`
      - `ctx:HeavyLifting` "Heavy Lifting"
      - `ctx:HeavyMeatHandling`
      - `ctx:HighShelfWork` "High Shelf Work"
      - `ctx:IceHandling`
      - `ctx:LiftWork` "Lift Work"
      - `ctx:LoadingDock` "Loading Dock"
      - `ctx:MedicationHandling`
      - `ctx:OverloadedHandcart`
      - `ctx:PackageSorting` "Package Sorting"
      - `ctx:ShelfStocking` "Shelf Stocking"
      - `ctx:StorageShelf` "Storage Shelf"
    - `ctx:NoiseWork` "소음작업" [⊒1, ←585]
      - `ctx:NoiseExposure` "Noise Exposure"
    - `ctx:Passage` "통로" [⊒2, ←1113]
      - `ctx:AisleObstruction`
      - `ctx:WalkwayObstruction`
    - `ctx:PathogenWork` "병원체 취급작업" [⊒8, ←10]
      - `ctx:AcupunctureWork`
      - `ctx:AutoclaveSterilization`
      - `ctx:BiomedicalWaste`
      - `ctx:BodyTransport`
      - `ctx:CremationFurnace`
      - `ctx:DentalProcedure`
      - `ctx:Embalming`
      - `ctx:FuneralHallSetup`
    - `ctx:PressureVessel` "압력용기" [⊒0, ←1729]
    - `ctx:RadiationWork` "방사선작업" [⊒0, ←12]
    - `ctx:Rail` "철도" [⊒0, ←111]
    - `ctx:Robot` "로봇" [⊒0, ←101]
    - `ctx:Scaffold` "비계" [⊒7, ←460]
      - `ctx:ClimbingWall`
      - `ctx:ExteriorRope`
      - `ctx:HighRiseWindow`
      - `ctx:Ladder` "Ladder"
      - `ctx:LadderInterior` "Ladder Interior"
      - `ctx:RopeAccess` "Rope Access"
      - `ctx:ScaffoldWork`
    - `ctx:Steelwork` "철골작업" [⊒0, ←336]
    - `ctx:UnknownContext` "미상 작업맥락" [⊒71, ←73]
      - `ctx:AcrophobiaWork`
      - `ctx:AnimalFeeding` "Animal Feeding"
      - `ctx:BracketDefect`
      - `ctx:BystanderWorkerExposure`
      - `ctx:CageCleaning` "Cage Cleaning"
      - `ctx:CardioEquipment`
      - `ctx:CashierArea` "Cashier Area"
      - `ctx:CleaningNight` "Cleaning Night"
      - `ctx:CleaningWet` "Cleaning Wet"
      - `ctx:CommunicationFailure`
      - `ctx:CrowdManagement` "Crowd Management"
      - `ctx:DisplaySetup`
      - `ctx:DogGrooming` "Dog Grooming"
      - `ctx:EvBattery` "Ev Battery"
      - `ctx:ExerciseClass`
      - `ctx:ExpiredMedicationUse`
      - `ctx:FilterMaintenance`
      - `ctx:FirstAidFailure`
      - `ctx:FishCutting`
      - `ctx:FloralArrangement`
      - `ctx:FreeWeightZone`
      - `ctx:GreenhouseWork` "Greenhouse Work"
      - `ctx:HairWash` "Hair Wash"
      - `ctx:HandrailDefect`
      - `ctx:HarvestWork` "Harvest Work"
      - `ctx:InteriorCleaning` "Interior Cleaning"
      - `ctx:InterlockBypass`
      - `ctx:Irrigation` "Irrigation"
      - `ctx:KnifeWork`
      - `ctx:LandfillOperation`
      - `ctx:LooseSafetyCover`
      - `ctx:LotoNotApplied`
      - `ctx:NearbyWorkerProximity`
      - `ctx:NightSolo` "Night Solo"
      - `ctx:NightSoloWork` "Night Solo Work"
      - `ctx:ObstructedViewCarrying`
      - `ctx:OutdoorPlayEquipment`
      - `ctx:OvenOperation`
      - `ctx:OverloadedContainer`
      - `ctx:PetBathing` "Pet Bathing"
      - … (+31 more 하위, inspect_node.py --list 로 확인)
    - `ctx:Vehicle` "차량" [⊒2, ←1517]
      - `ctx:DeliveryRider` "Delivery Rider"
      - `ctx:ForkliftOperation` "Forklift Operation"
    - `ctx:Ventilation` "환기작업" [⊒1, ←1769]
      - `ctx:VentilationPoor` "Ventilation Poor"
  - `haz:AccidentType` "사고 유형" [⊒23, ←59] ⊑(obo:BFO_0000019)
    - `haz:AnimalInjury` "동물상해" [⊒1, ←3]
      - `haz:AnimalBite`
    - `haz:CaughtIn` "끼임" [⊒9, ←2516]
      - `haz:CaughtInConfinedSpace`
      - `haz:CompressionInjury`
      - `haz:Crush`
      - `haz:DriverEntanglement`
      - `haz:Entanglement`
      - `haz:FootCrushInjury`
      - `haz:PtoEntanglement`
      - `haz:RotatingHookEntanglement`
      - `haz:RotatingPartInjury`
    - `haz:ChemicalExposure` "화학물질누출접촉" [⊒39, ←44]
      - `haz:ChemicalAbsorptionThroughSkin`
      - `haz:ChemicalAccidentDueToImproperDetergentUse`
      - `haz:ChemicalDetergentInhalation`
      - `haz:ChemicalEyeAndAirwayInjury`
      - `haz:ChemicalIngestion`
      - `haz:ChemicalInhalation`
      - `haz:ChemicalIrritation`
      - `haz:ChemicalResidualInhalation`
      - `haz:ChemicalSkinIrritation`
      - `haz:ChemicalVaporExposure`
      - `haz:ChemicalVaporInhalation`
      - `haz:ChemicalVaporInhalationUnconsciousness`
      - `haz:ChildChemicalExposure`
      - `haz:ChloramineGasInhalationPoisoning`
      - `haz:ChlorineGasInhalationPoisoning`
      - `haz:CytotoxicExposure`
      - `haz:DetergentInhalationPoisoning`
      - `haz:EyeChemicalInjury`
      - `haz:FertilizerDustInhalation`
      - `haz:FoodContamination`
      - `haz:FuelLeakVaporInhalation`
      - `haz:GasLeak`
      - `haz:GasLeakAtNight`
      - `haz:GasPoisoning`
      - `haz:GradualMinorFuelLeakage`
      - `haz:HighPressureGasLeakage`
      - `haz:HydrocarbonVaporInhalationPoisoning`
      - `haz:InhalationOfChemicalDust`
      - `haz:MercuryPoisoning`
      - `haz:NarcoticDermalAbsorption`
      - `haz:PesticideAbsorptionThroughSkin`
      - `haz:PesticideEyeContact`
      - `haz:PesticideInhalationPoisoning`
      - `haz:ResidualCleanerExposure`
      - `haz:SkinContact`
      - `haz:SkinEyeContactChemicalInjury`
      - `haz:SkinIrritation`
      - `haz:ToxicGasInhalation`
      - `haz:ToxicGasPoisoning`
    - `haz:Collapse` "붕괴" [⊒5, ←2354]
      - `haz:LandfillSlopeCollapse`
      - `haz:LoadCollapse`
      - `haz:ScaffoldCollapse`
      - `haz:ShelfCollapse`
      - `haz:SoilCollapse`
    - `haz:Collision` "충돌" [⊒2, ←6222]
      - `haz:MachineCollisionInjury`
      - `haz:TrayContactInjury`
    - `haz:CrushedOverturned` "깔림뒤집힘" [⊒6, ←8]
      - `haz:CartTipover`
      - `haz:CrushedByMachineOrObject`
      - `haz:HandcartOverturn`
      - `haz:HeavyEquipmentOverturn`
      - `haz:LockerTipover`
      - `haz:TractorTipover`
    - `haz:CutLaceration` "절단베임찔림" [⊒18, ←1924]
      - `haz:BladeLaceration`
      - `haz:ChildCut`
      - `haz:ChildStabbing`
      - `haz:Cut`
      - `haz:CutDueToGloveFailure`
      - `haz:CuttingBladeContactWhileOperating`
      - `haz:ElectricalAccidentDueToPowerInstability`
      - `haz:FingerAmputation`
      - `haz:FingerInjury`
      - `haz:GlassLaceration`
      - `haz:Laceration`
      - `haz:PalmLaceration`
      - `haz:PruningShearLaceration`
      - `haz:Puncture`
      - `haz:Scratch`
      - `haz:SharpObjectInjury`
      - `haz:SkinPenetration`
      - `haz:ThresherBladeCut`
    - `haz:Drowning` "빠짐익사" [⊒0, ←2]
    - `haz:ElectricShock` "감전" [⊒2, ←8]
      - `haz:ChildElectricShock`
      - `haz:ElectricShockDueToInsulationDamage`
    - `haz:ErgonomicStrain` "불균형및무리한동작" [⊒5, ←688]
      - `haz:Ergonomic`
      - `haz:HeavyLifting`
      - `haz:LossOfBalance`
      - `haz:Posture`
      - `haz:Repetitive`
    - `haz:Explosion` "폭발파열" [⊒8, ←10]
      - `haz:ChemicalExplosion`
      - `haz:ChemicalReactionExplosion`
      - `haz:DustExplosion`
      - `haz:FireAndExplosion`
      - `haz:FuelGasExplosion`
      - `haz:FuelIgnitionExplosion`
      - `haz:HighPressureRelease`
      - `haz:PressureVesselExplosion`
    - `haz:Fall` "추락" [⊒13, ←3552]
      - `haz:ChairTipoverFall`
      - `haz:FallDueToStrongWind`
      - `haz:FallFromAnkerFailure`
      - `haz:FallFromHeight`
      - `haz:FallFromLadder`
      - `haz:FallFromLossOfBalance`
      - `haz:FallFromRopeFrictionBreakage`
      - `haz:FallOnGround`
      - `haz:GondolaOverturnFall`
      - `haz:HotObjectMultipleFalling`
      - `haz:PatientFall`
      - `haz:RopeBreakFall`
      - `haz:UserFall`
    - `haz:FireInjury` "화재" [⊒9, ←14]
      - `haz:FireFromOutletOverload`
      - `haz:FireSpread`
      - `haz:FuelFire`
      - `haz:FuelTankFire`
      - `haz:FuelVaporIgnitionByStaticDischarge`
      - `haz:IgnitionOfFlammableGas`
      - `haz:OverloadFire`
      - `haz:SpontaneousCombustionOfAbsorbentPad`
      - `haz:TrashBinFire`
    - `haz:OffSiteTraffic` "사업장외교통사고" [⊒0, ←2]
    - `haz:OtherAccident` "기타" [⊒0, ←2]
    - `haz:OxygenDeficiency` "산소결핍" [⊒1, ←3]
      - `haz:ConfinedSpaceAsphyxia`
    - `haz:SlipTrip` "넘어짐" [⊒5, ←1172]
      - `haz:ChildSlipAndFall`
      - `haz:FallFromKnotSlip`
      - `haz:KnifeSlipCut`
      - `haz:Slip`
      - `haz:StairTrip`
    - `haz:SportsEventInjury` "체육행사" [⊒0, ←2]
    - `haz:StruckBy` "맞음" [⊒8, ←2110]
      - `haz:BurnFromFallingHotContents`
      - `haz:FallingChemicalContainer`
      - `haz:FallingFromWires`
      - `haz:FallingObject`
      - `haz:MachineFallingCollisionInjury`
      - `haz:StruckByIceFragment`
      - `haz:StruckBySharpObject`
      - `haz:TvFalling`
    - `haz:TempExtremeContact` "이상온도물체접촉" [⊒16, ←19]
      - `haz:ArcBurn`
      - `haz:Burn`
      - `haz:BurnFromAccidentalCustomerContact`
      - `haz:ChemicalBurn`
      - `haz:ChemicalBurnFromStrongAcid`
      - `haz:ChemicalBurnFromStrongAcidToEye`
      - `haz:ChemicalSkinBurn`
      - `haz:ColdBurn`
      - `haz:ColdExposure`
      - `haz:ExtremeColdBurn`
      - `haz:HandBurn`
      - `haz:HighTemperatureBurn`
      - `haz:HotSteamBurn`
      - `haz:ResidualHeatBurn`
      - `haz:SkinBurn`
      - `haz:SteamBurn`
    - `haz:Unclassified` "분류불능" [⊒10, ←12]
      - `haz:ContainerBreakageDuringCollection`
      - `haz:EyeForeignBody`
      - `haz:EyeVisionDamage`
      - `haz:Fracture`
      - `haz:InfantSafetyAccident`
      - `haz:Infection`
      - `haz:LabelMisidentificationAccident`
      - `haz:LossOfControlPolisher`
      - `haz:MedicalEmergency`
      - `haz:OvercrowdingEvacuationDelay`
    - `haz:Violence` "폭력행위" [⊒0, ←2]
    - `haz:WorkplaceTraffic` "사업장내교통사고" [⊒1, ←3]
      - `haz:TrafficAccident`
  - `risk:NaturalLanguageHazardCategory` "자연어 위험요소 카테고리" [⊒0, ←24]
- `risk:RiskPattern` "위험 패턴" [⊒1, ←2] ⊑(obo:BFO_0000019)
  - `she:SituationalHazardPattern` "위험상황 패턴" [⊒0, ←22] ⊑(obo:BFO_0000019, +제약4)
- `she:VisualTrigger` "시각 트리거" [⊒0, ←4] ⊑(obo:BFO_0000019)
- `sr:RequirementType` "요구사항 유형" [⊒0, ←8] ⊑(lkif:Norm)
- `sr:SafetyRequirement` "안전요구사항" [⊒0, ←47] ⊑(lkif:Obligation, +제약5)

## 3. 속성 (predicate)

### Object Properties (133)

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
| `sr:addressesHazard` | 대응 위험 | sr:SafetyRequirement | haz:AccidentType |
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
| `she:triggerText` | 시각 트리거 문구 | she:VisualTrigger | http://www.w3.org/2001/XMLSchema#string |
| `she:validFrom` | 유효 시작일 (법령 시행일) | she:SituationalHazardPattern | http://www.w3.org/2001/XMLSchema#date |
| `she:validUntil` | 유효 종료일 (deprecate 시점) | she:SituationalHazardPattern | http://www.w3.org/2001/XMLSchema#date |

## 4. ⚠️ 자동 이상징후 점검

> ⚠️ ref/dead는 **대용량 kosha-instances.ttl(코퍼스) 제외** 집계 — guide/core/app 등 코퍼스에 instance가 있는 클래스의 dead/ref는 신뢰 불가(코퍼스에서 live일 수 있음). facet(haz/agent/ctx) fine 코드는 canonical-ci 포함이라 정확. 제거 전 반드시 코퍼스 포함 재확인.

**(a) facet 클래스인데 risk:RiskFeature 미도달(floating): 0**

  ✅ 없음 (모든 facet 클래스가 risk:RiskFeature까지 연결).

**(b) rdfs:label 없는 클래스: 339**

  `agent:AcrylateResinSkinContact`, `agent:AirlessResidualPressure`, `agent:AsbestosDust`, `agent:Benzene`, `agent:BiogasMethane`, `agent:BloodbornePathogen`, `agent:CapacitorResidualVoltage`, `agent:ChlorineAmmoniaReaction`, `agent:ColdFloor`, `agent:ConcentratedAlkali`, `agent:ContaminatedFilterParticulateMold`, `agent:CryogenicAgent`, `agent:DefectiveHandle`, `agent:DefectiveSterilePackaging`, `agent:DegradedDeveloperSolution`, `agent:DentalXRay`, `agent:DentalXrayRepeatedExposure`, `agent:DistributionBoard`, `agent:EarphoneNoise`, `agent:ElectricalOverload`, `agent:ElectricityWaterContact`, `agent:ElevatorPitToxicGas`, `agent:ExposedOutlet`, `agent:ExtremeColdEnvironment`, `agent:ExtremeColdSurface`, `agent:FemaleExposureLimitExceeded`, `agent:FormaldehydeSkinContact`, `agent:FragranceVapor`, `agent:FuelSaturatedAbsorbent`, `agent:GasolineMicroLeakage`, `agent:GasolineVapor`, `agent:GlutaraldehydeVapor`, `agent:HighHeat`, `agent:HighPressureAirDust`, `agent:HighTemperatureEnvironment`, `agent:HighTemperatureSteam`, `agent:HotEquipment`, `agent:HotParts`, `agent:HotSurface`, `agent:HotTray` …

**(c) dead 후보(하위0·피참조0·개체아님): 345**

  `agent:AcrylateResinSkinContact`, `agent:AirlessResidualPressure`, `agent:AsbestosDust`, `agent:Benzene`, `agent:BiogasMethane`, `agent:BloodbornePathogen`, `agent:CapacitorResidualVoltage`, `agent:ChlorineAmmoniaReaction`, `agent:ColdFloor`, `agent:ConcentratedAlkali`, `agent:ContaminatedFilterParticulateMold`, `agent:CryogenicAgent`, `agent:DefectiveHandle`, `agent:DefectiveSterilePackaging`, `agent:DegradedDeveloperSolution`, `agent:DentalXRay`, `agent:DentalXrayRepeatedExposure`, `agent:DistributionBoard`, `agent:EarphoneNoise`, `agent:ElectricalOverload`, `agent:ElectricityWaterContact`, `agent:ElevatorPitToxicGas`, `agent:ExposedOutlet`, `agent:ExtremeColdEnvironment`, `agent:ExtremeColdSurface`, `agent:FemaleExposureLimitExceeded`, `agent:FormaldehydeSkinContact`, `agent:FragranceVapor`, `agent:FuelSaturatedAbsorbent`, `agent:GasolineMicroLeakage`, `agent:GasolineVapor`, `agent:GlutaraldehydeVapor`, `agent:HighHeat`, `agent:HighPressureAirDust`, `agent:HighTemperatureEnvironment`, `agent:HighTemperatureSteam`, `agent:HotEquipment`, `agent:HotParts`, `agent:HotSurface`, `agent:HotTray` …

**(d) 중복 label(같은 한글 라벨, 다른 IRI): 4쌍**

  - "근로자": `core:Worker`, `actor:Worker`
  - "기타": `ctx:OtherAgentState`, `industry:Industry_OTHER`, `haz:OtherAccident`
  - "비상대응": `ctx:EmergencyResponse`, `sr:EmergencyResponse`
  - "정비": `ctx:Maintenance`, `industry:Industry_MAINTENANCE`

**(e) domain 또는 range 누락 property: 34**

  `bridge:appliesTo`, `bridge:observedIn`, `core:hasViolation`, `core:identifier`, `core:text`, `core:title`, `guide:sourceGuide`, `guide:sourceSection`, `law:articleCode`, `law:belongsToChapter`, `law:belongsToPart`, `law:belongsToSection`, `law:belongsToSubsection`, `law:conditionText`, `law:conditionType`, `law:fullText`, `law:hasAction`, `law:hasNormStatement`, `law:hasObject`, `law:hasParentStructure`, `law:isDeleted`, `law:modifiedBy`, `law:paragraphCount`, `law:paragraphRef`, `law:structureLabel`, `pen:delegatedFrom`, `pen:hasPenalty`, `pen:penaltyDescription`, `pen:severityScore`, `she:appliesPenalty`, `sr:hasBindingForce`, `sr:hasChecklistItem`, `sr:hasRequirementType`, `sr:hasSafetyRequirement`

**(f) punned IRI(class+individual 동시, 정상이지만 참고): 141**

  141개 — facet canonical punning 설계(haz:Fall 등). 표본: `agent:ArcFlash`, `agent:Biological`, `agent:Chemical`, `agent:Corrosion`, `agent:Dust`, `agent:Electricity`, `agent:Fire`, `agent:HeatCold`, `agent:Noise`, `agent:Radiation`, `agent:Toxic`, `agent:UnknownAgent` …

