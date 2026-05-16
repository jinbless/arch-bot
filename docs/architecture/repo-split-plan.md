# Repo Split Plan

향후 3-repo 분할 계획. 현재는 모노레포(`arch-bot`), 별도 팀이 합류하거나 오픈소스 공개 직전에 실제 분할.

## 목표 구조

| Repo | 가시성 | 팀 | 단계 | 디렉토리 prefix |
|---|---|---|---|---|
| `kosha-data-pipeline` | private | 데이터팀 | 1~5 | `data-team/` + `shared/` mirror |
| `kosha-ontology-reasoning` | **public (오픈소스)** | 온톨로지팀 | 6 | `ontology-team/` + `shared/` mirror |
| `kosha-ohs` | private | 서빙팀 | 7~8 | `serving-team/` + `shared/` mirror |

`arch-bot`은 meta-repo로 archive 또는 향후 submodule/링크 페이지로 유지.

## 단계별 절차

### Phase A — 현재 (완료)
- ✅ 모노레포 안에서 디렉토리 재배치
- ✅ 팀별 디렉토리 구조 (`data-team/`, `ontology-team/`, `serving-team/`, `shared/`)
- ✅ 외부 의존 경로 수정 (Makefile, pipe-A/B 상대경로)
- ✅ 단계 간 인터페이스 문서화 ([inter-stage-interfaces.md](inter-stage-interfaces.md))

### Phase B — 5번 안정화 후 (다음 PR)
- 5번 작업이 활발하므로 일단 보류. 5번이 6번으로 자연 폐지될 때까지 모노레포 유지.
- 다만 5번 영역 (현재 serving-team/08-app/backend/scripts·app/data에 남은 부분)을 [data-team/05-enrichment/](../../data-team/05-enrichment/) 하위로 점진 이동.
- backend가 runtime artifact를 어떻게 받을지 (환경변수 path / 빌드 단계 mirror / 그대로 두기) 설계 결정.

### Phase C — 별도 팀 합류 시점 또는 오픈소스 공개 직전
1. **`git subtree split`로 3개 repo 추출**:
   ```bash
   # data-team subtree extract
   cd arch-bot
   git subtree split --prefix=data-team -b data-team-export
   # 별도 repo로 push
   git push <kosha-data-pipeline-remote> data-team-export:main

   # ontology-team subtree extract
   git subtree split --prefix=ontology-team -b ontology-team-export
   git push <kosha-ontology-reasoning-remote> ontology-team-export:main

   # serving-team subtree extract
   git subtree split --prefix=serving-team -b serving-team-export
   git push <kosha-ohs-remote> serving-team-export:main
   ```

2. **각 repo에 `shared/` mirror**:
   - 옵션 A: 각 repo의 root에 `shared/` 복사 (수동 동기화 부담)
   - 옵션 B: `shared/`를 별도 repo (`kosha-shared`)로 만들고 git submodule
   - 옵션 C: package distribution (npm/pip) — 너무 무거움

3. **각 repo의 CI/CD 설정**:
   - GitHub Actions workflow (test/lint/build)
   - Branch protection
   - Release automation

4. **각 repo에 README + contributor guide**:
   - 외부 의존 (다른 repo와의 인터페이스) 명세
   - PR 정책

5. **arch-bot 모노레포 archive**:
   - README에 "3 repo로 분할됨" 안내
   - 또는 archive 후 새 meta-repo 신설

### Phase D — 오픈소스 공개 (Phase C의 일부 또는 직후)
[open-source-readiness.md](open-source-readiness.md) 체크리스트 따름.

## 분리 시 주의사항

### Cross-cutting 변경의 부담
- 모노레포에서는 한 commit으로 끝나던 baseline 변경(예: SR ID schema 변경)이 3개 repo PR을 동시에 진행해야 함.
- → version pinning 필요. shared/ schema는 version 명시.

### 의존 방향
- 데이터팀 → 온톨로지팀 → 서빙팀 (단방향)
- 역방향 의존 금지. 서빙팀이 데이터팀 스크립트를 직접 호출하지 않음.

### PG schema ownership
- 데이터팀이 PG schema 1차 소유 (1~5단계)
- 서빙팀의 7단계가 PG에 추가 테이블/view 만들 수 있음
- 변경 시 데이터팀과 합의

### Worktree / 진행 작업과의 충돌
- 분리 시점에 진행 중인 5번 작업이 있다면 일단 모노레포에서 마무리 후 분리

## 진행 조건 (Phase B → C 트리거)

다음 중 하나 만족 시 Phase C 실행:
1. 별도 팀이 실제 합류 (예: 온톨로지팀이 별도 인원으로 합류)
2. 오픈소스 공개 결정 (kosha-ontology-reasoning을 public으로 전환)
3. release cycle 분리 필요 (예: OHS는 매주 배포, ontology는 분기 배포)

지금은 위 어느 것도 임박하지 않았으므로 Phase A 완료 후 Phase B (5번 정리)에 집중.
