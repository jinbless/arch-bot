# 조문별 만화 카드 UI (2026-08-12) — 방식1/방식2 토글 비교 배포

> 원본: `data-team/06-조문별만화/` — 고용노동부·KOSHA 「만화로 보는 산업안전보건기준에 관한 규칙」
> 조문 카드 PDF 667장(1페이지 합성물, 크기 가변) + `_목록.csv`. **raw는 미추적**(474MB, .gitignore 가드).

## 구성

- **자산**: `backend/scripts/build_cartoon_assets.py` — get_pixmap 3x → WebP q75, 667장 총 36.5MB.
  파일명 `NNN.<콘텐츠해시8>.webp`(한글 URL 인코딩 함정 회피 + immutable + 증분 + 캐시버스트).
  파일명↔CSV 전수 대조 게이트(불일치 시 abort). manifest(`frontend/src/data/cartoons.manifest.json`,
  조문키→{f,w,h,t})만 커밋 — WebP는 미추적, bind-mount 서빙(chromadb·shared/reference 패턴).
- **매핑**: `articleCartoon.tsx`의 `cartoonFor(ref)` — **선두 `/^제\d+조(의\d+)?/` 앵커**라
  법/시행령/시행규칙/고시/가이드코드/작업명 ref는 자연 탈락(다른 법 조번호 오염 차단).
  흐름 ref 66.9% 커버, basics 100%. lawLink도 이 모듈로 이관.
- **방식1(기본)**: 행 유지 + '그림으로 보기' 버튼 → 확대 모달(portal z-60, ESC/backdrop,
  출처 문구+법령 링크, hover 프리로드). **방식2**: 행 본문을 인라인 카드로 교체(lazy +
  manifest w/h aspect-ratio 예약 → CLS 0), 클릭 확대. 슬롯/목록 단위 **dedup**(제35조 카드가
  43항목에 반복되는 함정 — 첫 등장만 카드, 이후는 텍스트+버튼).
- **토글**: 우하단 고정(조문 표시: 글+그림보기/그림 카드), localStorage `ohs.cartoon_mode_v1`,
  기본 modal. **비교 실험 스캐폴딩 — 사용자 선택 후 탈락 방식+토글 철거 예정.**
- **적용 지점**: 흐름 타임라인 Item·'지금 당장' 스트립(버튼만)·AI 대조 matched(버튼만)·
  BasicsPage·ImmediateActionsPanel(rule:Article만). PenaltyPathPanel 제외(legacy off).
- **서빙**: dev=vite public/, prod=frontend nginx `location /ohs/cartoons`(immutable 1y,
  add_header 함정 준수) + `${CARTOONS_HOST_DIR}` ro bind-mount(compose 2곳). 죽은
  `/articles-pdf/` 프록시는 frontend nginx에서 제거(edge 것은 후속). 번들 산출물
  `ohs-cartoons.tar.gz` 추가(build_bundle [6/7]·load_and_up 검증).

## 배포·검증 (prod)

- 드롭릿: cartoons tar → `/home/moeldev/srv/ohs/cartoons`(667), `.env`에 CARTOONS_HOST_DIR,
  compose frontend에 볼륨 패치(원본 백업 `docker-compose.yml.bak-cartoon`), update-ohs-code.sh.
  ⚠ 드롭릿 compose는 리포 server 변형과 다름(호스트 nginx·127.0.0.1 publish) — 통째 교체 금지,
  제자리 패치. ⚠ ssh heredoc에 `${...:?}`가 들어가면 원격 셸이 확장해 깨진다 — 패치는 파일로 scp.
- 확인: `/ohs/cartoons/*.webp` 200+immutable(에지 경유), 모달(제3조 카드+법령 링크),
  인라인(카드 44/45·lazy), 흐름 패널(인라인 4+버튼 11), 출처 표기, 이미지 ID 대조.

## 남은 것

- **사용자 비교 → 최종 선택** → 탈락 방식 코드+토글 철거.
- edge conf의 죽은 /articles-pdf/ 제거(별도, edge 재시작 리스크 분리).
- 미보유 카드 2종(제227조·제4조의2)은 조용히 텍스트 유지 — 원본 수급 시 스크립트 재실행이면 끝.
- 인라인 모드는 evidence 인용을 숨긴다(카드에 원문 포함) — 비교 관찰 포인트.
