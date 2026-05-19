# T4 #2 Decision — AdministrativeFine TTL "Enrichment" Scope (2026-05-19)

## Background

Phase G.3 (penalty_rule_index PG materialization) 보고서에 다음 미해결 항목 명시:
> "AdministrativeFine instances TTL enrichment — G.3에서 발견한 데이터 갭 (TTL에 criminal만, admin 0건)"

## Investigation Result

**결론: 데이터 갭이 아니라 design intent.**

### 증거 1: penalty-routes.json metadata
```json
{
  "metadata": {
    "totalRoutes": 656,
    "withPenalty": 638,
    "withAdministrativeFine": 0,
    "withoutAdministrativeFine": 656
  }
}
```
명시적으로 0 카운트 + "withoutAdministrativeFine": 656 (모든 routes).

### 증거 2: pipe-A CLAUDE.md 설계 문서
> "RULE 조문은 제38조/제39조를 통해 위임되며, 이 두 조문은 과태료 대상이 아니므로 대부분의 RULE 조문에는 형사벌만 적용된다."

### 증거 3: 한국 산업안전 법령 구조
- **RULE** (산업안전보건기준에 관한 규칙): 위반 시 OSHA 제38/39 위임 → 제167~169 형사벌
- **OSHA 제175조**: administrative fines 6단계 (5천만원 ~ 300만원)
- RULE → OSHA 38/39 위임 경로는 형사벌만, OSHA 제175조의 admin penalty는 별도 위반 행위 대상

## Re-scope

T4 #2를 "TTL enrichment"가 아닌 "OSHA admin penalty 별도 추출" 작업으로 재정의:

- **Phase G 범위 외**: pipe-A 확장 필요 (`step1_extract_penalties.py`가 OSHA 제175조 별도 처리)
- 별도 sprint 필요: "Pipe-A OSHA admin penalty 확장"
- 예상 소요: 4-6시간 (Step 1 스크립트 + schema + 검증)
- 영향: penalty_rule_index에 sanction_type='AdministrativeFine' rows 추가

## Action

- T4 #2 closed (design clarification, not a gap)
- 별도 sprint 후보 등록: "Pipe-A OSHA admin penalty extraction"
- Phase G 최종 결과에 영향 없음

## Related

- [phase-g.3-penalty-rule-index-pg.md](phase-g.3-penalty-rule-index-pg.md)
- `data-team/02-extraction/pipe-A/CLAUDE.md` (제재 구조 섹션)
- `data-team/02-extraction/pipe-A/data/penalty-routes.json` (metadata.withAdministrativeFine)
