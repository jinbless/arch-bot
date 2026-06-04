# 런타임 실데이터 흐름 — GPT 인지 문장 → PG(온톨로지) + 벡터DB → 4패널

> v5(semantic attach) 적용 후, "GPT가 인지한 실제 문장"이 어느 아키텍처 노드를 거쳐
> 4패널 결과가 되는지를 **라이브 트레이스 실제값 + 실제 동작 기준**으로 그린 흐름도. (지게차·프레스 2종)
> 노드값은 `scripts/run_forklift_panels.py` / `test_ci_grounding.py` 출력과 대조 완료.

## 읽는 법 — 두 축
GPT 위험요소 1건이 **두 축**으로 흐른다:
- **(A) 분류축**: `name` → `normalize_hazards_array()` → canonical 코드 → PG `*_canonical`.
  위험개요·SHE 매칭·facet 보조에 쓰임. (구조·분류)
- **(B) 의미축 ⭐**: `name+설명+조치` rich text → **hybrid_search** (벡터 rank ⊕ BM25 rank → RRF) →
  온톨로지 검증 → rerank. SR/GUIDE/CI 부착의 **주 경로**. 종류(SR/GUIDE/CI_raw)별 독립 호출.

**hybrid recall 실제 동작**: 벡터 rank와 BM25 rank는 **같은 ChromaDB 컬렉션의 문서**를 각각 점수화한 뒤
**RRF(k=60)** 로 융합한다. BM25는 별도 ES 서버가 아니라 **`rank_bm25`(BM25Okapi) 인메모리** 이고,
토큰화는 **공백 분리 + 조사(접미사) 제거**(`text_utils.tokenize_korean`) — *형태소 분석(kiwipiepy) 아님*.

## 노드 ↔ 실제 구현체
| 흐름도 노드 | 실제 구현 |
|---|---|
| GPT Vision | `app/integrations/openai_client.py` gpt-4.1 |
| normalize | `hazard_normalizer.normalize_hazards_array()` → PG `*_canonical` |
| 벡터 rank | 질의 `text-embedding-3-small` → ChromaDB 저장벡터 cosine (`_vector_rank`) |
| 벡터DB | ChromaDB `ohs_sr·ohs_ns·ohs_ci·ohs_guide·ohs_ci_raw` (온톨로지 원문 임베딩, `build_kb_embeddings.py`) |
| BM25 rank | **`rank_bm25` BM25Okapi 인메모리** — 토큰=공백+조사제거(`tokenize_korean`, ≠형태소), **ES 없음** |
| 융합 | **RRF k=60** (`hybrid_search.search`) — 벡터·BM25 각 rank 합성 |
| 검증 | PG `PgSafetyRequirement`·`PgKoshaGuide` 존재 / `sr_article_mapping` citable |
| rerank | `_rerank_guides_llm()` gpt-4.1-mini |
| semantic-first | `_stack_semantic_first()` (facet ↓cap) |
| 즉시조치 | `hazard_to_ci_service.match_hazards_to_ci()` → `ohs_ci_raw` → guide+section 인용 |
| 벌칙 | `get_penalty_candidates(sr_ids)` → `sr_article_mapping` → 조문 |

---

## ① 지게차 (물류창고) — 실제 트레이스

```mermaid
flowchart TD
  classDef pg fill:#e8f0fe,stroke:#4285f4,color:#000
  classDef vec fill:#fce8e6,stroke:#ea4335,color:#000
  classDef llm fill:#fef7e0,stroke:#fbbc04,color:#000
  classDef out fill:#e6f4ea,stroke:#34a853,color:#000

  GPT["GPT Vision (gpt-4.1)<br/>위험요소 「지게차 충돌」 (높음)<br/>설명: 주행 지게차와 보행자 동선 혼재<br/>조치: 보행자 통로 분리·출입통제·유도자"]:::llm

  subgraph A["(A) 분류축 — 정규화 → PG"]
    NORM["normalize_hazards_array()"]
    CODE["canonical: COLLISION·VEHICLE"]:::pg
    NORM --> CODE
  end
  subgraph B["(B) 의미축 — hybrid_search(kind): 벡터 ⊕ BM25 → RRF(k=60)"]
    Q["질의 = name+설명+조치 (rich text)"]
    VDB[("ChromaDB ohs_sr·ohs_guide·ohs_ci_raw<br/>온톨로지 원문 = 벡터 + BM25 코퍼스 공유")]:::vec
    VR["벡터 rank<br/>질의 text-embedding-3-small → 저장벡터 cosine"]
    BR["BM25 rank — rank_bm25 (인메모리)<br/>토큰=공백분리+조사제거 (≠형태소)"]
    RRF["RRF 융합 (k=60)"]
    Q --> VR
    Q --> BR
    VDB -->|"저장 임베딩"| VR
    VDB -->|"같은 문서 lazy 색인"| BR
    VR --> RRF
    BR --> RRF
  end
  subgraph V["Layer2 — 온톨로지 검증·전파 (PG=SSOT)"]
    VAL["존재·citable·도메인<br/>PgSafetyRequirement / sr_article_mapping"]:::pg
    RR["rerank (gpt-4.1-mini)"]:::llm
    ST["_stack_semantic_first (facet ↓cap)"]
    RR --> ST
  end
  subgraph O["Layer3 — 4 패널 (PG 물질화)"]
    P1["① 위험요소별 가이드<br/>B-M-11 지게차안전 · G-10 운반차량 · G-100 운전자교육"]:::out
    P2["② 표준 개선 절차 (① dedup)"]:::out
    P3["③ 즉시 조치<br/>'지게차전용구역 보행자 출입금지'<br/>근거: B-M-11 9.1절"]:::out
    P4["④ 벌칙 3경로<br/>RULE 제179조 (후진경보기·경광등)"]:::out
    P1 --> P2
  end

  GPT -->|"name '지게차 충돌'"| NORM
  GPT -->|"rich text"| Q
  RRF -->|"SR 후보 SR-VEHICLE-009"| VAL
  RRF -->|"GUIDE 후보 B-M-11"| RR
  RRF -->|"CI 후보 (ohs_ci_raw)"| P3
  VAL -->|"sr_article_mapping → 조문"| P4
  ST --> P1
  CODE -.->|"facet GF-direct (cap)"| ST
  CODE -.->|"위험개요·SHE"| P1
```

## ② 프레스 (제조) — 실제 트레이스

```mermaid
flowchart TD
  classDef pg fill:#e8f0fe,stroke:#4285f4,color:#000
  classDef vec fill:#fce8e6,stroke:#ea4335,color:#000
  classDef llm fill:#fef7e0,stroke:#fbbc04,color:#000
  classDef out fill:#e6f4ea,stroke:#34a853,color:#000

  GPT["GPT Vision (gpt-4.1)<br/>위험요소 「프레스 끼임(압착)」 (높음)<br/>설명: 금형 사이 신체 진입 협착·절단<br/>조치: 광전자식 방호장치·양수조작"]:::llm

  subgraph A["(A) 분류축 — 정규화 → PG"]
    NORM["normalize_hazards_array()"]
    CODE["canonical: CAUGHT_IN·PRESS_MACHINE"]:::pg
    NORM --> CODE
  end
  subgraph B["(B) 의미축 — hybrid_search(kind): 벡터 ⊕ BM25 → RRF(k=60)"]
    Q["질의 = name+설명+조치 (rich text)"]
    VDB[("ChromaDB ohs_sr·ohs_guide·ohs_ci_raw<br/>온톨로지 원문 = 벡터 + BM25 코퍼스 공유")]:::vec
    VR["벡터 rank<br/>질의 text-embedding-3-small → 저장벡터 cosine"]
    BR["BM25 rank — rank_bm25 (인메모리)<br/>토큰=공백분리+조사제거 (≠형태소)"]
    RRF["RRF 융합 (k=60)"]
    Q --> VR
    Q --> BR
    VDB -->|"저장 임베딩"| VR
    VDB -->|"같은 문서 lazy 색인"| BR
    VR --> RRF
    BR --> RRF
  end
  subgraph V["Layer2 — 온톨로지 검증·전파 (PG=SSOT)"]
    VAL["존재·citable·도메인<br/>PgSafetyRequirement / sr_article_mapping"]:::pg
    RR["rerank (gpt-4.1-mini)"]:::llm
    ST["_stack_semantic_first (facet ↓cap)"]
    RR --> ST
  end
  subgraph O["Layer3 — 4 패널 (PG 물질화)"]
    P1["① 위험요소별 가이드<br/>B-M-36 프레스위험방지 · B-M-37 끼임·절단 · M-56 사출성형기"]:::out
    P2["② 표준 개선 절차 (① dedup)"]:::out
    P3["③ 즉시 조치<br/>'프레스에 안전블록 설치'<br/>근거: B-M-36 (프레스 위험방지)"]:::out
    P4["④ 벌칙 3경로<br/>RULE 제104조 (방호장치) · 중대재해 제102·103조"]:::out
    P1 --> P2
  end

  GPT -->|"name '프레스 끼임'"| NORM
  GPT -->|"rich text"| Q
  RRF -->|"SR 후보 SR-MACHINE-018"| VAL
  RRF -->|"GUIDE 후보 B-M-36"| RR
  RRF -->|"CI 후보 (ohs_ci_raw)"| P3
  VAL -->|"sr_article_mapping → 조문"| P4
  ST --> P1
  CODE -.->|"facet GF-direct (cap)"| ST
  CODE -.->|"위험개요·SHE"| P1
```

## 핵심 한 줄
GPT 자유서술 조치(`보행자 통로 분리` / `광전자식 방호장치`) → **hybrid(벡터⊕BM25) 회수** → 우리 권위
CI·GUIDE·SR에 grounding → 섹션·조문 인용까지. 분류축(코드)은 위험개요·SHE·facet 보조로만,
부착 정밀도는 의미축(벡터DB+BM25 RRF)+온톨로지 검증이 책임진다.

## 정정 이력
- BM25를 초기 흐름도에서 "kiwipiepy"로 표기했으나, 실제 토큰화는 **공백+조사제거**(`tokenize_korean`)이며
  엔진은 **`rank_bm25` 인메모리**(ES 아님). 본 문서는 실제 동작 기준으로 수정됨.
