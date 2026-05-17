# Architecture

시스템 아키텍처·팀 분담·향후 repo 분리·오픈소스 공개 준비 문서 모음.

## 문서

### 🚀 시스템 아키텍처 (2026-05-17 추가)
| 파일 | 용도 |
|---|---|
| **[4-layer-architecture.md](4-layer-architecture.md)** ⭐ | Layer 0-4 전체 architecture (Vision + Normalizer + Reasoning + Materialization + Ontology Learning) |
| **[ontology-learning-layer.md](ontology-learning-layer.md)** ⭐ | Layer 4 (cross-cutting) 7-module 정밀 설계 — 학계 9 paper 기반 |
| **[llm-dependency-evolution.md](llm-dependency-evolution.md)** ⭐ | LLM 의존 단계적 폐지 path (5단계 hybrid → 6단계 reasoner → 7단계 PG materialize) |

### 팀/조직/repo 구조
| 파일 | 용도 |
|---|---|
| [team-structure.md](team-structure.md) | 3팀 분담 + 9단계 매핑 + 책임 영역 |
| [stage-mapping.md](stage-mapping.md) | 9단계 정의 + 각 단계의 코드/파일 위치 |
| [inter-stage-interfaces.md](inter-stage-interfaces.md) | 단계 간 인터페이스 — PG schema, 파일 contract, 의존 방향 |
| [repo-split-plan.md](repo-split-plan.md) | 향후 3-repo 분할 계획 + 단계별 절차 |
| [open-source-readiness.md](open-source-readiness.md) | 6단계 오픈소스 공개 체크리스트 |
| [source-provenance.md](source-provenance.md) | PROV-O 출처/근거 레이어 설계 (기존) |

## 핵심 통찰 (2026-05-17~)

> 4-Layer + cross-cutting Layer 4 architecture가 long-tail 도메인 (KOSHA 산업안전) 자율 적응의 핵심.
> Vision LLM만 영구 잔존, semantic reasoning은 reasoner로 이전, vocabulary/class/rule은 Layer 4 (Ontology Learning)가 자율 학습.
> 우리 차별점: LKIF-Core × BFO 2-layer + 한국어 + asymmetric trust + Task C SOTA + Task D 학계 미답.
