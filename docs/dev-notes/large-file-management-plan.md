# Runtime-artifacts 큰 파일 관리 계획 (LFS migration)

**날짜**: 2026-05-18 (Quick wins Task 4)
**문제**: `alias_embedding_cache.json` 51MB, `catalog_label_embedding_cache.json` 45MB — GitHub 권장 50MB 초과.

## 현재 상태

| File | 크기 | 출처 | 재생성 비용 |
|---|---|---|---|
| `alias_embedding_cache.json` | **51MB** | F.1 Day 3 Gate 1 (~695 alias × 1536-dim) | ~$0.014, ~5초 |
| `catalog_label_embedding_cache.json` | **45MB** | F.1 recover Stage 2 (~310+ label × 1536-dim) | ~$0.01, ~5초 |
| `synthetic_audit_v1.json` | 5.9MB | Phase 3 일회성 audit | re-run script (~5분) |
| `guide_domain_embeddings.npz` | 3.6MB | guide embedding cache (numpy npz) | 재생성 비용 ~$0.05 |
| `replay_baseline_v*.json` | 2-2.2MB 각 | Gate 3 baseline | re-run replay (~5분) |
| `replay_post_f32.json` | 2.1MB | F.3.3 replay 결과 | re-run replay |
| `replay_active_*.json` | 2MB 각 | F.0 Phase B replay 결과 | re-run |

총 변동 크기 (>50MB): **96MB** (alias + catalog 합)

## GitHub 권장 임계
- 50MB 초과: warning (push 진행)
- 100MB 초과: block (Git LFS 권장)

현재 단일 파일 51MB로 first warning 영역. 향후 alias 추가 시 100MB 초과 가능.

## 대안 평가

### 옵션 A: Git LFS 마이그레이션
- **Pros**: 표준 솔루션, 큰 파일 자동 처리, 일반 Git 워크플로우 유지
- **Cons**: 별도 LFS 저장소 필요 (GitHub 50GB 무료 → 그 후 유료), 모든 contributor LFS 설치 필요, clone 시 LFS pull 추가 단계
- **비용**: 무료 quota 내 (현재 50GB 한참 여유)
- **마이그레이션 작업**:
  ```bash
  git lfs install
  git lfs track "*.json" --filename="alias_embedding_cache.json"
  git lfs track "*.json" --filename="catalog_label_embedding_cache.json"
  git add .gitattributes
  git rm --cached data-team/05-enrichment/runtime-artifacts/alias_embedding_cache.json
  git rm --cached data-team/05-enrichment/runtime-artifacts/catalog_label_embedding_cache.json
  git add data-team/05-enrichment/runtime-artifacts/alias_embedding_cache.json
  git add data-team/05-enrichment/runtime-artifacts/catalog_label_embedding_cache.json
  git commit -m "chore(lfs): migrate large embedding caches to Git LFS"
  ```

### 옵션 B: Numpy `.npz` 압축 변환 (권장)
- **Pros**: 무료, 추가 도구 X, 크기 ~60-80% 감소 (50MB → 10-15MB), `guide_domain_embeddings.npz` 패턴 일관성
- **Cons**: 코드 변경 필요 (JSON load → numpy load), 비-numpy 도구로 inspect 어려움
- **변환 작업**:
  - `auto_register_aliases.py`의 `load_embedding_cache` / `save_embedding_cache` 수정
  - JSON 1회성 → npz 영구
  - 1회 마이그레이션 스크립트 작성

### 옵션 C: `.gitignore` + per-machine 재생성
- **Pros**: 0 변경, 가장 단순
- **Cons**: fresh clone 시 재계산 ~$0.014 + ~5초 (저비용이지만 매번)
- **사용 상황**: 캐시 자체 가치 작을 때

### 옵션 D: 별도 저장소 (예: S3, Azure Blob)
- **Pros**: 무한 확장, dependency 명확
- **Cons**: 별도 인프라, 인증 관리

## 권장

**1순위: 옵션 B (Numpy `.npz` 변환)**
- 비용 0, 무료 도구
- 크기 ~10-15MB로 축소 (50MB → 안전 영역)
- `guide_domain_embeddings.npz` 패턴과 일관성
- 작업 시간: 2-3h (변환 스크립트 + 코드 변경)

**2순위: 옵션 C (.gitignore + 재생성)**
- 즉시 적용 가능 (5분)
- 캐시 재계산 비용 trivial ($0.014)
- LFS 도입 안 함 (간단)
- Cleanup 가치만 (저장소 size ↓)

**비추천: 옵션 A (Git LFS)**
- 추가 인프라/계정 관리
- contributor onboarding 부담
- 현재 규모에서 over-engineering

## 단기 실행 (오늘)
- 본 plan 문서화만 (실제 마이그레이션은 별도 작업)
- 현재 push 가능 상태 (50MB 약간 초과는 warning만)

## 중기 실행 (별도 sprint, 2-3h)
- 옵션 B 적용: alias_embedding_cache.json → alias_embedding_cache.npz
- `auto_register_aliases.py`, `recover_catalog_mismatch.py` 코드 수정
- 마이그레이션 1회 + 기존 .json 파일 git rm

## 모니터링
- 파일 크기 매 sprint 후 점검:
  ```bash
  ls -lh data-team/05-enrichment/runtime-artifacts/*.json | awk '$5 ~ /M/'
  ```
- 100MB 초과 임박 시 옵션 B 우선 진행
