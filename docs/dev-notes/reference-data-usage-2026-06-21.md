# 기인물 참고자료 활용 설계 (2026-06-21)

> 자료 카탈로그: [reference-data/기인물참고자료/MANIFEST.md](../../data-team/05-enrichment/reference-data/기인물참고자료/MANIFEST.md)
> 모(母) 설계: [photo-to-article-cwa-redesign](photo-to-article-cwa-redesign-2026-06-21.md)

## 배경 — 왜 이 자료가 중요한가
현재 사진→조문 매핑은 **기인물 앵커로 P@1 62.5%/Hit@3 100%(검증)**. 막힌 곳:
1. **라벨 병목** — 실제 사진 8장뿐 → 모든 수치가 1~2장 노이즈.
2. **resolution 오류** — 재추출 시 프레스↔사출 등 기인물 오인이 절/관을 틀리게 함(A 후퇴 원인).
3. **형제조문 변별** — required_measures가 LLM 생성이라 약함.

KOSHA 참고자료(**SIF 6,032 + 구조화사례 1,177 = 7,209건**, 기인물+조치 라벨)는 이 셋 중
**②③과 ①의 "매칭 절반"**을 직접 보완한다. (사진이 아니라 텍스트이므로 "추출 절반"(사진→기인물)은 못 풂.)

## 정규화 완료 (가져오기)
`parse_reference_data.py` → `parsed/sif_archive.jsonl`(6032) + `parsed/accident_cases.jsonl`(1177).
스키마·통계는 MANIFEST 참조. 감소대책 52%/예방조치 46%가 법정 조치어휘 직접 포함.

**per-file 가치 검증(실제 확인):** 금광=SIF·구조화(case-level). 보조=CSV/요약(집계·빈도, alias·우선순위용).
**PDF=금광 아님** — 2011 집계 통계 + 공식 KOSHA 기인물 분류체계(스캔이미지). SIF/구조화가 상위라 직접 데이터 가치는 없고, 분류체계는 USE 1 카테고리 정렬의 *보조* 참고만.

## 활용 설계 (우선순위)

### USE 1 — 기인물→절/관 alias 사전 (resolution 강화) ★단기 최고가성비
- **문제**: RESOLVE(사진 기인물→group_key)가 드리프트(프레스→사출→절8 오답).
- **방법**: SIF 677 distinct 기인물 + 사례 CSV 품목 → 각 기인물을 `gimulmul_index`의 절/관 group_key로 매핑.
  LLM 1차 + **빈도 상위 ~150종 사람 검수**(롱테일은 LLM). 산출 `gimulmul_alias.json {기인물어휘→[group_key]}`.
- **효과**: RESOLVE를 "사전 조회(결정적) + LLM(미등록만)"으로 → 프레스/사출·굴착기/백호 등 변별 고정. #3답("RDB가 기억")의 구체화.

### USE 2 — 텍스트 semi-gold (매처 대규모 검증, 라벨 병목 우회) ★핵심
- **문제**: 8장으론 매처 성능을 못 가린다.
- **방법**: 각 사례(기인물 + 감소대책/예방조치) → 기인물 앵커로 후보 조 생성 → **감소대책↔조문 LLM 매핑**
  (감소대책 "개구부 덮개 설치"→제43, "비상정지장치"→제192) → **사람이 층화표본 spot-check**.
  산출 `text_semigold.jsonl {case_id, 기인물, gold_articles[], 검수여부}`.
- **효과**: RESOLVE+RANK를 수백~수천 건에서 P@1/Hit@k 측정 → 노이즈 탈출, 형제조문 변별 튜닝의 신뢰 신호.
- **주의(불변원칙)**: LLM 매핑은 후보. **신뢰 수치는 사람 검수분만.** 전체는 semi-gold(개발용), 검수 부분집합이 gold.

### USE 3 — required_measures 실사고 보강 (형제조문 변별)
- **방법**: SIF 감소대책을 기인물·조문별로 모아, article signature의 `required_measures`를 **실제 사고기반 어휘**로 보강
  (LLM 합성 대신/병행). 산출 보강된 `article_signatures` 또는 `measure_bank.json {조문→실측 조치구문[]}`.
- **효과**: measure-aware 매칭(A에서 시도)의 약점(LLM 어휘)을 실데이터로 메움.

### USE 4 — 유사사례 retrieval (서빙 기능, 후순위)
- 사진 기인물/위험 → 유사 SIF·사례 + 감소대책 제시("이런 사망사고가 있었습니다"). Layer4 GraphRAG/CBR 제품기능.

## 한계 (정직)
- **텍스트지 사진 아님.** 매칭 절반(기인물→조문)만 대규모 검증. 추출 절반(사진→기인물 시각혼동)은 사진 라벨 필요.
- 단 USE 1(alias)·USE 3(measure)·빈도 few-shot이 추출/resolution을 **간접 보완**.
- SIF는 건설업 비중 큼(3463) → 우리 8장(제조/건설 혼합)과 분포 차이 감안.

## 추천 실행 순서
1. **USE 1 (alias 사전)** — 빠르고 resolution 직접 개선. `build_gimulmul_alias.py`.
2. **USE 2 (text semi-gold)** — 매처 대규모 검증 셋. `build_text_semigold.py` + 사람 spot-check 시트.
3. **USE 3 (measure 보강)** — 시그니처 강화.
4. USE 4 (서빙 CBR) — 후순위.

## git 정책
- raw PDF/xlsx: 미추적(정책). `parsed/*.jsonl`: 재생성 가능(미정). 구조화 MD/CSV·MANIFEST·파서: 추적 후보.
