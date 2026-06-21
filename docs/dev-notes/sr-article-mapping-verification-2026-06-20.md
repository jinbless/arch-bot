# SR→조 매핑 검증 (정확도 향상 1단계) — 2026-06-20

> compact 후 재개용 핸드오프. 목적: "GPT가 인식한 사진 위험 → 산업안전보건규칙 몇 조 위반" 매핑이 잘 되는지 전수 검증.

## 방법 (확정된 접근)

세 축:
1. **시스템 예측** — `scripts/dump_synthetic_sr_articles.py`: 2,360 합성 케이스(`expected_features` 주입, Vision 우회)를 실 파이프라인(`analysis_pipeline.run`, **PG 기반**)에 통과 → 케이스별 **focused**(`situation_matches[].applies_sr_ids`)·**broad**(`findings.sr_ids`) SR + `sr_article_mapping`(1:1)로 조. 산출 `synthetic_sr_article_dump.jsonl`.
2. **독립 gold (장章 기반 LLM 태깅)** — scene → 관련 **장 multi-label**(32장, `articles.section`에서 추출) → 그 장 조문 **full-text** → `gold_codes`(직접)/`maybe_codes`(정황). 시스템 출력과 독립.
   - **Claude** (Workflow 에이전트, **$0**, 권장 **batch 4**): `claude_gold_v2.jsonl` (2,360). ⚠️ batch 10은 under-tagging(case당 토큰↓) — batch 4가 품질 좋음.
   - **gpt-5.4** (Batch API 2-round, `scripts/build_gpt_chapter_gold.py`): S1 장분류 → S2 조문 태깅 → `gpt_gold.jsonl` (1,292 positive).
3. **채점** — `scripts/score_sr_article_mapping.py --gold <gold>`: dump vs gold → focused/broad **precision/recall/F1**, case_type 슬라이스.

> ⚠️ **시스템은 온톨로지(Fuseki/OWL)가 아니라 PG 물질화 경로를 통과** — she_catalog(JSONB @>)·safety_requirements facet. 온톨로지는 그 PG의 상류 SoT.

## 핵심 발견 (전수 2,360, 2개 독립 LLM 교차검증)

| 기준 | focused P/R | broad P/R |
|---|---|---|
| Claude gold v2 (positive 1,377) | **2.5% / 5.6%** | 1.0% / 48% |
| **Consensus gold**(Claude∩gpt, 722) | **3.4% / 6.0%** | 1.4% / 51.5% |

- **시스템 조-매핑이 심하게 오정렬** — consensus gold(두 전문가-LLM 동의)에서도 focused 6%·broad 51%(정밀도 1.4%)만 맞춤 → gold 결함 아님, 실재.
- Claude↔gpt 평균 **Jaccard 0.45**, **disagreement 59%(770/1,292)** → gold는 **사람 adjudication 필요**(WS-EVAL-2 미확정). negative 100%·ambiguous 94% zero(둘 다 정상 abstain).
- **근본원인** (`scripts/diagnose_focused_mismatch.py`로 추적):
  1. **자석 SR** — generic-facet SR이 도메인 무관하게 다수 케이스에 박힘: 제312(전기) 12%·제87(회전축) 11%·제421/422(유해물질)·제390(하역) 7%.
  2. **facet-collision SHE→SR 큐레이션** — `FALL` 한 축으로 로프작업↔하역장(제390) 연결(she_sr_mapping).
  3. **느슨한 2축 SHE 매칭** — `CONFINED_SPACE+COLLAPSE`(score 0.38)가 잠함굴착 패턴 매칭(밀폐≠굴착).
  - ※ 2026-05의 `지게차→항만하역` guide facet 과태깅과 **같은 병**(거친 facet 충돌), 단 이번엔 SHE→SR 레이어.

## 산출물 경로 (data-team/05-enrichment/runtime-artifacts/)

- **추적**: `claude_gold_v2.jsonl`(2,360 최종 Claude gold) · `gpt_gold.jsonl`(1,292 gpt gold).
- **미추적(gitignore, 재생성 가능/로컬)**: `synthetic_sr_article_dump.jsonl`(시스템 예측, dump 재실행 ~30분) · `claude_gold_batches/`·`claude_gold_pos_batches/`(중간) · `gpt_gold_s1/s2_*`·`gpt_gold_batch_meta.json` · `articles_by_chapter.tsv`·`chapters.tsv`·`articles_rule*`(PG에서 재생성) · `gold_cases_*.jsonl`(`export_case_scenes.py`) · `score_sr_article_mapping.*`·`judge_*`(리포트).

## 신규/수정 코드 (serving-team/08-app/backend/scripts/)

신규: `dump_synthetic_sr_articles.py` · `score_sr_article_mapping.py` · `export_case_scenes.py` · `build_gpt_chapter_gold.py` · `diagnose_focused_mismatch.py` · `build_gold_articles.py`(구 title-shortlist gpt 방식, 장 기반에 superseded) · `judge_sr_article_mapping.py`(구 closed-judge, batch infra 재사용원).
수정: `_mapping_review_common.py`(`_sr_articles` + SR_COLS "산업안전보건규칙 조" 컬럼 — HITL export에 조 표면화).
Workflow 스크립트(`claude-chapter-gold-*.js`)는 `~/.claude/.../workflows/scripts/`에 세션 로컬 보존(재실행 시 `scriptPath`로).

## ⚠ 2026-06-21 방향 전환 — 계획했던 "자석 prune + 게이팅"은 측정 결과 무가치, 의미 retrieval로 선회

아래 "다음 단계"의 2번(자석/게이팅)을 실제로 측정해보니 효과가 미미해 폐기하고, **의미매칭 retrieval**로 전환했다(검증 완료).

**왜 자석/게이팅이 답이 아닌가 (`sim_broad_gating.py`):**
- 자석 링크 source가 `phase3c` 아님 → `synthetic_bootstrap`(`bootstrap_she_from_synthetic.py:156 or [top1]` fallback)·`inversion`. ∴ `she_sr_exclusions.json`+`--reconcile` 메커니즘으로 못 지움.
- `query_sr_for_facets`(broad)는 1축만 겹쳐도 SR 50개 반환(`hazard_rule_engine.py:360`). **≥2축 게이팅해도 precision@1 2~6% 천장, recall만 반토막.** facet은 article 변별 불가(동일 비계+추락도 정답 조 6개 제각각, `eval_knn_generalization.py`서 동일facet→gold Jaccard 0.38).

**해법 — 의미 retrieval (검증, text-embedding-3-large):**
| 방식 | P@1 | 비고 |
|---|---|---|
| facet baseline | 1.9% | 현행 |
| ⒜ 장면↔전체 조문 | 19% | gold 불요 fallback |
| ⒞ gold-이웃 kNN 재사용 | 57% | redundancy 강건(τ0.70 cap도 52%, 최근접 median 0.69) |
| **⒞ + LLM rerank** | **76%** | retrieve→rerank 풀 파이프라인 천장(`eval_rerank_ceiling.py`) |

- 파이프라인: **장면 임베딩 → gold 장면 kNN으로 후보 8개 → gpt-5.4가 조문 전문 대조해 yes 선별.**
- 구현: `build_semantic_article_index.py`(KB 물질화 semantic_kb.npz/json) + `app/services/semantic_article_service.py`(`recommend_articles()`, PG·재임베딩 불요) + `demo_semantic_serving.py`(스모크).
- **gold = 척도가 아니라 서빙 지식베이스**가 됨 → 확정(A)+확충이 곧 정확도. CLAUDE.md Layer4 GraphRAG/Phase B rerank 자리.
- **유일 미지수: 합성→실제 사진 전이**(KB·질의 모두 합성; real-test-photo/ spot-check만 가능).
- ⚠ consensus-core gold는 교집합이라 너무 엄격(인접 정답 제42/44 미크레딧) → 현 측정치는 **하한**, gold 확정 후 상승 예상.

**진행 순서(2026-06-21):** ①rerank 천장측정 ✓ → ②recall 보강(KB 확장+⒜ union 재측정) → ③gold 확정(tiebreak `batch_6a3750093d04819087183c02c38c8664` 비동기 24h: `tiebreak_gold_gpt.py --mode collect` → `adjudicate_gold.py --mode merge`) → KB 재물질화·재측정 → ④실서빙 통합(`analysis_pipeline`/API).

---

## 다음 단계 (구안 — 2번은 위에서 폐기됨, 기록 보존)

1. **gold 확정** — disagreement 770건 사람 adjudication(또는 3rd 모델 tiebreak) → 정식 WS-EVAL-2 golden set. consensus 722는 이미 고신뢰. **(여전히 유효 — 단 의미 retrieval의 KB로서 역할 추가)**
2. ~~**정확도 개선(자석 prune + 도메인 게이팅)**~~ — 측정 결과 무가치, 위 의미 retrieval로 대체:
   - ~~자석 SR `she_sr_mapping` cross-domain 링크 정리~~
   - ~~SHE 매칭 도메인 게이팅~~ / ~~fine work_context 변별~~

### 재현 명령 (WSL venv, DATABASE_URL=postgresql://kosha:1229@localhost:5432/kosha)
```bash
cd serving-team/08-app/backend
# 시스템 예측 dump (전체 2360)
.venv/bin/python scripts/dump_synthetic_sr_articles.py --resume
# 채점
python scripts/score_sr_article_mapping.py --gold ../../../data-team/05-enrichment/runtime-artifacts/claude_gold_v2.jsonl
# 근본원인 추적
.venv/bin/python scripts/diagnose_focused_mismatch.py SYN-0053 SYN-V2-0042
# gpt gold (Batch): s1-build → s1-submit → (대기) s1-collect → s2-build → s2-submit → s2-collect
# Claude gold (Workflow): 장 기반 태깅 워크플로 재실행(batch 4 권장)
```
※ PG는 `mcp__postgres__query` 아님 — `docker exec kosha-pg`. 활성 SHE=she-full.ttl(1675). (메모리 [[ref_kosha_pg_access]])
