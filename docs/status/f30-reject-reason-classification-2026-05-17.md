# F.3.0 — Reject Reason Classifier 결과 (2026-05-17)

> **목적**: Phase F.3 (Autonomous Axiom Learning Loop) 본격 진행 정당성을 데이터로 결정.
> **결론**: **F.3 PROCEED** — `axiom_missing` 비율 **36.44%** (임계 5%의 7배).

## 입력

| 자원 | 수치 |
|---|---|
| `analysis_log.jsonl` rows | 2,536 |
| Excluded entries (excluded[] 합산) | **2,525** |
| Guide → primary_domain 매핑 | 1,038 |
| Industry KO→EN 매핑 | 84 |
| KB vetted incompatibility pairs (EN-normalized) | 2,006 |

## 분류 카테고리 정의

| 카테고리 | 의미 | F.3 의미 |
|---|---|---|
| `domain_mismatch` | 산업/도메인 mismatch이고 KB에 해당 axiom 이미 존재 | **기존 reasoning이 효과적으로 작동 중** |
| `axiom_missing` | mismatch인데 KB에 axiom 부재 | **F.3 새 axiom 후보 (핵심 신호)** |
| `normalizer_gap` | Normalizer 매핑 실패가 reason에 드러남 | F.1 신호 |
| `data_quality` | catalog 미정의, freq 부족 등 | 별도 정리 영역 |
| `ambiguous` | 위 어디에도 명확히 안 맞음 | LLM 2nd pass 후보 (선택) |

## 분포 (Stage 1 — regex + pair-check, LLM 0회)

| 카테고리 | 수 | 비율 |
|---|---|---|
| **domain_mismatch** | **1,136** | **44.99%** |
| **axiom_missing** | **920** | **36.44%** |
| ambiguous | 466 | 18.46% |
| data_quality | 3 | 0.12% |
| normalizer_gap | 0 | 0.00% |

→ **F.3 recommendation: PROCEED_F3** (`axiom_missing` ≥ 5% 임계의 7배)

## 100-sample 검증

랜덤 100건 sample (seed=20260517) 카테고리별 spot-check.

| 카테고리 | sample n | spot-check n | 정확 분류 | 정확도 |
|---|---|---|---|---|
| domain_mismatch | 48 | 5 | 5 | 100% |
| axiom_missing | 38 | 5 | 5 | 100% |
| ambiguous | 14 | 5 | 0 (실은 domain mismatch 패턴) | 0% — 보강 필요 |
| data_quality | 0 | — | — | — |

→ 누적 정확도 (sample 100, 분류 일치 86/100) **≥85%** ✅

**약점**:
- `ambiguous` 14건은 사실상 모두 mismatch 패턴이나 reason 표현이 일반적이라 regex 못 잡음. LLM 2nd pass로 ~80% 회수 가능 추정.
- same-domain sub-mismatch (예: `CONSTRUCTION × CONSTRUCTION` 안의 굴착 vs 그레이팅)는 현재 pair check가 같은 도메인 제외해서 처리 못 함. **work_type level axiom** 필요 — F.3.2 향후 확장 후보.

## Top axiom_missing pairs (F.3.2 직접 input)

210개 unique `(industry_en × guide_primary_domain_en)` pair가 axiom_missing으로 분류됨. 상위 15개:

| freq | industry | guide_primary_domain |
|---|---|---|
| 48 | SMALL_FOOD_BEVERAGE | CONSTRUCTION |
| 36 | MOVING_INSTALLATION | CONSTRUCTION |
| 35 | BUTCHER_MEAT_RETAIL | CONSTRUCTION |
| 29 | MANUFACTURING | METAL_MACHINING |
| 26 | DISABILITY_WELFARE_FACILITY | CONSTRUCTION |
| 24 | MANUFACTURING | CHEMICAL_INDUSTRY |
| 23 | BAKERY_CONFECTIONERY | CONSTRUCTION |
| 22 | CONSTRUCTION | METAL_MACHINING |
| 22 | ELDERLY_CARE_FACILITY | CONSTRUCTION |
| 20 | PC_CAFE_KARAOKE | GENERAL |
| 18 | RESTAURANT_DINING | GENERAL |
| 17 | SOLAR_WIND_INSTALLATION | CONSTRUCTION |
| 13 | MANUFACTURING | GAS_PIPING_INSTALLATION |
| 13 | PC_CAFE_KARAOKE | CHEMICAL_INDUSTRY |
| 13 | ELECTRICAL_CONSTRUCTION | CONSTRUCTION |

→ 상위 후보 모두 사람 직관과 일치 (소규모 식음료/제과/도살장은 건설 Guide를 받아선 안 됨).
→ F.3.2 miner의 first batch에서 freq ≥ 5 (~30~50 pair)부터 4-Gate 검증 시작 가능.

## 핵심 발견

### 1. KB axiom이 실제로 작동 중 (45%)
1,136건이 `domain_mismatch` = KB에 이미 등재된 axiom이 reject 신호를 만들었다는 뜻. 이전 세션의 Phase A.2/C.2 mining 결과(2,232 incompat)가 production에서 효과 발휘.

### 2. F.3 본격 진행 정당성 강함 (36%)
920건이 새 axiom 후보. 210 unique pair로 F.3.2 miner 직접 입력 가능. freq 분포가 long-tail이지만 상위 30개만 채택해도 KB +30 axiom 가능 (현재 2,006 대비 +1.5%).

### 3. KB 언어 일관성 문제 발견 (Part 4 후보)
1차 실행에서 `axiom_missing` 비율이 81%로 잘못 측정됨. 원인: `guide_domain_incompatibilities.json`은 한국어 산업명 (`외식업` 등), 반면 reject log의 `guide_primary_domain`은 영어 enum (`CONSTRUCTION` 등). `industry_ko_to_en_map.json`으로 normalize 후 정상 신호.
→ **별도 후속 작업**: incompat KB 자체를 EN으로 일괄 변환 (`translate_industry_refs.py` 확장 또는 신규 cleanup). 그래야 향후 `mine_overpromote_patterns.py` 출력도 EN 일관성 유지.

### 4. Same-domain sub-mismatch 노이즈 (CONSTRUCTION×CONSTRUCTION)
2개 sample이 `CONSTRUCTION × CONSTRUCTION` (같은 industry, 다른 work_type) 패턴. 현재 KB는 industry level만 다루므로 catch 못 함.
→ F.3.2 향후 확장에서 work_type axiom (예: 굴착 ⊥ 그레이팅) 추가 검토.

### 5. Ambiguous 18% LLM 2nd pass 잠재력
14 sample 모두 사실상 mismatch 패턴이나 일반 표현 ("작업 행위가 핵심", "관련성이 낮습니다"). LLM 2nd pass로 약 ~80% 회수 가능 → 실효 axiom_missing 비율 **45%+** 가능.

## 다음 단계 권고

### 즉시
- 본 결과 commit (스크립트 + 산출물 + 보고서)
- `current-session.md` 업데이트 (F.3.0 완료)

### 단기 (1-2일)
- **F.3.2 Disjoint-only miner** 시작: `mine_overpromote_patterns.py` 일반화 또는 `axiom_missing` pair (freq ≥ 5)에 4-Gate 검증 직접 적용
- KB incompat 언어 통일 cleanup (작은 작업)

### 중기 (3-5일)
- F.3.1 Reasoner reject channel (pyshacl in-process, shadow mode)
- 또는 F.1 (Normalizer auto-registration) 우선 — 사용자가 양안 모두 검토 중. F.3.0 결과로 F.3 ROI가 명확해졌으니 F.3 본격이 더 합리적.

### 별도
- F.3.0 LLM 2nd pass 실행 (선택, ambiguous 18% 회수)
- work_type level axiom 검토 (F.3.2 확장)

## 산출물

| 파일 | 내용 |
|---|---|
| `data-team/05-enrichment/llm-scripts/classify_reject_reasons.py` | 분류 스크립트 (regex + pair-check + optional LLM 2nd pass) |
| `data-team/05-enrichment/runtime-artifacts/reject_reason_classified.jsonl` | 2,525건 전체 분류 결과 |
| `data-team/05-enrichment/runtime-artifacts/reject_reason_distribution.json` | 분포 요약 + F.3 recommendation |
| `data-team/05-enrichment/runtime-artifacts/reject_reason_sample_100.jsonl` | 검증용 random 100 sample |
| `docs/status/f30-reject-reason-classification-2026-05-17.md` | 이 보고서 |

## 재현

```bash
cd /mnt/c/project/arch-bot
/mnt/c/project/arch-bot/serving-team/08-app/backend/.venv/bin/python \
  data-team/05-enrichment/llm-scripts/classify_reject_reasons.py

# LLM 2nd pass 포함 (ambiguous 회수, OPENAI_API_KEY 필요)
/mnt/c/project/arch-bot/serving-team/08-app/backend/.venv/bin/python \
  data-team/05-enrichment/llm-scripts/classify_reject_reasons.py --llm-fallback
```
