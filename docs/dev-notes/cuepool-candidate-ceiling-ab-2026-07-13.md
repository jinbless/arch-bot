# cue-pool 후보천장 A/B — 실제 감독관 gold 129장 (2026-07-13)

> **결론 선요약**: 관찰단서(cue-pool) 카탈로그를 baseline 후보생성(gimulmul 기인물 앵커)에 **additive union**으로 얹으면 후보천장(cand_any)이 **84.5% → 93.0%**로 상승(plan 목표 ≥0.93 달성). cue-pool 단독은 baseline보다 낮음(대체재 아님, **상보재**). 남은 갭은 대부분 석면 표지 미부착(사진 검출 본질적 불가). **⚠️ 천장 ≠ P@1** — 다음 관문은 union에 RANK를 걸어 P@1/Hit@5를 재는 것.

## 배경
- cue-pool(`docs/knowledge/감독관-판단기준/cue-pool.json`, 115 cue, 3종=기인물83·위험장소구조25·환경7)을 P1/P2/P3 절 sweep으로 구축, RULE 669/669=100% 커버(→ [[cue-centric-architecture]] 메모리, 커밋 93c077d·2c1e2fb·ead2212·be2e284).
- 기존 검증된 최선 = **기인물 앵커**(gimulmul): 사진→기인물 RESOLVE→절/관 관찰조문 ∪ 횡단→RANK. 8장서 P@1 62.5%(→ [photo-to-article-cwa-redesign](photo-to-article-cwa-redesign-2026-06-21.md)).
- 가설: cue-pool의 3-cue 일반화(장소·구조+환경)가 기인물-only가 구조적으로 못 닿는 축(추락 클러스터·개구부·조명·분진 등)을 후보로 잡아 천장을 올린다.

## 방법 (4-arm cand_any A/B)
같은 Vision 출력에서 후보집합 4종을 만들어 실제 감독관 gold(match=y)와 조인, 랭킹 전 **천장(정답이 후보에 있나)** 측정.

| arm | 후보 |
|---|---|
| baseline(gimulmul) | RESOLVE→기인물 절/관 관찰조문 ∪ Section B 큐레이션 ∪ alias ∪ 횡단(CROSS), 관찰가능 필터 |
| cue_entry | cue-matcher 발화(Vision텍스트 substring ← alias+vision_keywords+canonical) → 진입 조문 |
| cue_entry+flow | + 조치 흐름 조문 |
| union | baseline ∪ cue_entry ∪ cue_flow |

- **지표**: recall(=포착 y-코드/전체 y-코드), photo_any(≥1 gold 포착 사진율=천장), photo_all(전 gold 포착), 평균 후보수.
- 공정성: 세 arm 모두 `article_signatures.observable ∈ {yes,partial}` 동일 필터.

### 자산 (재현)
- **실제 gold**: `real-test-photo/label_photo/label_curation_gold.csv` (match=y, **129장 · y-라벨 162**, 사람=감독관 라벨, gitignore). 원천 = `curation_viewer.html`(248 감독건 후보) 사람 큐레이션.
- **Vision(gpt-4.1) 영구 저장**: `data-team/05-enrichment/runtime-artifacts/intake_vision_gold.json` (한글 파일명 키 → gold 직접 조인. 재측정 시 `--reuse-vision`으로 재사용, Vision 재호출 불요).
  - ⚠️ 기존 `intake_vision.json`(129 **번호** 사진)은 원본 사진·매핑 유실로 gold와 조인 불가(고아). 이번엔 한글명 키로 저장해 재유실 방지.
- **측정 스크립트**: `serving-team/08-app/backend/scripts/measure_cuepool_gold.py` (Vision+RESOLVE, PG 불필요 — RANK excerpt는 signature violation_scene 사용). 실행: `.venv/bin/python scripts/measure_cuepool_gold.py [--reuse-vision]`.
- **결과 raw**: `data-team/05-enrichment/runtime-artifacts/cuepool_ab_results.json` (per-photo gold/baseline/cue_entry/cue_flow + metrics).
- baseline 인덱스: `gimulmul_index.json`(113그룹·550관찰조문)·`gimulmul_alias.json`·`case_rule_mapping.json`·`article_signatures.jsonl`(669).

## 결과 (gold 129장 · y-코드 162)

| arm | recall | photo_any(천장) | photo_all | 평균후보 |
|---|---|---|---|---|
| baseline(gimulmul) | 0.821 | **0.845** | 0.798 | 29.8 |
| cue_entry | 0.722 | 0.729 | 0.698 | 19.2 |
| cue_entry+flow | 0.765 | 0.783 | 0.752 | 26.8 |
| **union(base∪cue)** | **0.914** | **0.930** | **0.915** | 45.3 |

- baseline photo_any **0.845 = 문서화된 "후보천장 84.5%" 재현** → 하네스 신뢰성 확인.
- **union +8.5pt(0.845→0.930)** = plan P1 게이트(cand_any ≥0.93) 달성. recall +9.3pt.
- 비용: 평균후보 29.8→45.3(**+15.5**, plan 게이트 "+15 미만" 소폭 초과) → RANK 부담 증가.

## 분석

**① cue-pool이 baseline 놓친 걸 잡음 (15건/15장 — union 상승 원천)** — 정확히 기인물-only 사각:
- 환경조건: 제4조의2(분진)·제21조(통로 조도)·제4조(청결/미끄럼)
- 위험장소·구조: 제30조(계단 안전난간)×2·제68조(사다리/승강)×3·제56조
- 기인물 보강: 제87조(회전축)×2·제122조×2·제302조(전기)

**② 둘 다 놓침 (14건 — 남은 7% 갭)**: 제490·492(석면 경고표지) 각 ×3 지배 = **표지 미부착**(위반=표지의 부재, 단장면 사진 검출 본질적 불가). 도메인 한계, cue-pool 결함 아님.

**③ baseline만 잡음 (24건 — cue 약점)**: 제301/316/303(전기 감전)·제22(통로)·제13/32/42~45(추락 횡단). = gimulmul이 **횡단 일반의무(CROSS 16조)를 하드코딩**해 항상 넣는 조문. cue-pool은 cue 발화 조건부 → union엔 이미 포함(그래서 union이 높음). 개선여지: cue-pool에도 CROSS 베이스라인 추가 시 단독 recall↑.

## 판정 & 다음
- **union을 후보생성에 additive로 채택 정당** — 천장 목표 달성, 이득이 cue-pool 설계 의도(장소·구조+환경)와 정확히 일치.
- **⚠️ 천장 ≠ 최종 정확도.** plan 실제 병목은 랭킹(P@1 38%). 후보 +15.5가 천장은 올려도 distractor 증가로 P@1 손해 가능. **결정적 다음 = union에 RANK(gpt-5.4)를 걸어 P@1/Hit@5를 baseline과 A/B**(`--reuse-vision`으로 Vision 재사용, RANK만 추가 = 저렴).
- 이후(가설 성립 시): cue-pool→후보생성 정식 배선(intake/track_a에 cue arm 토글) → 서빙 통합 → ⑤ 온톨로지화.

관련: [[cue-centric-architecture]] · [[sr-article-mapping-verification]] · [photo-to-article-cwa-redesign](photo-to-article-cwa-redesign-2026-06-21.md).
