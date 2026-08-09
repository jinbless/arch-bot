# 결과 화면 컨설팅 서사 재설계 — 진행 정본 (2026-08-09)

> 다음 세션 진입점. 목표: **UI 서사를 중심으로 알고리즘 흐름·체계도를 재편**한다.
> 1차(5단계 서사, 5cc5466·9bfc80e) → 2차(3단계 통합 + AI 제안 정렬 + 불비 원장, 이 문서).

## 1. 확정된 화면 구조 — 3단계 (2차 재설계 구현 완료)

```
① 사진에서 본 것        Vision 서술 통합. "서술이지 판정 아님" 명시
② 원래 이렇게 관리      기인물 앵커 흐름 6칸 ★주인공. 그 안에:
   ├ '지금 당장' 스트립   흐름 조문에서 선별한 즉시조치 — 클릭 시 근거 조문으로 점프·하이라이트
   ├ 6칸 타임라인         PRECHECK·EXEC의 선별 조문에 '지금' 배지
   └ 'AI 제안 대조'       GPT 자유 제안 ↔ 흐름 법정 조문 정렬 결과 (§2)
③ 직접 확인할 자료      가이드·기본수칙·안전검사
삭제: '사고가 나면'(벌칙 3경로)·'분석 상세' 접힘 — 사용자 결정 "효과성 없이 복잡".
      백엔드 응답 필드는 유지(기록 호환), 화면만 내림. 계산 자체의 옵션화는 다음 큐(§4-b).
```

통합 근거(사용자+비판 검토): 즉시조치는 흐름 조문의 **부분집합** — 별도 패널이면 같은 조문이
두 번 나와 출처가 흐려진다. 단 완전 병합(배지만)은 triage 상실이라 **스트립+배지** 형태.
앵커 정정(corrected) 시 스트립·배지·대조를 숨긴다 — 원 흐름 기준 계산값이라 정정 흐름에 얹으면 오안내.

## 2. AI 제안 ↔ 조문 정렬 + '구체 조문 불비 후보' 원장 (신규)

사용자 정책: *"연결되는 제안은 해당 조문을 보여주고, 연결 안 되는 건 폐기가 아니라
별도 저장했다가 정책적으로 사용"* — 조문이 모든 경우를 규정할 수 없으므로 무매칭이 곧 신호다.

- `flow_service.align_llm_actions()`: GPT 자유 제안(≤8) × 흐름의 **법정** 항목(≤60, 닫힌 집합)
  → LLM 1회(`FLOW_ALIGN_MODEL`, 기본 gpt-5.4), 후보를 **번호**로 답하게 함(줄 복사 실패 클래스 차단)
- status 3값: `matched`(조문 표시·점프) / `unmatched`(불비 후보 → 원장 적립) /
  `unaligned`(정렬 실패·구 기록 — **적립 금지**, 판정과 판정 실패를 섞으면 원장 오염)
- 원장 `ohs_action_statute_gaps`: (action_text, anchor_group_key) 단위 occurrence_count 누적,
  review_status=pending → 배치 검토(Sol 파이프라인)로 4분류: 진짜 불비 / 앵커 오류 /
  규칙 밖 조문에 존재(covered_elsewhere) / AI 일반론. **무매칭 ≠ 법적 불비 확정** —
  포괄 의무조항(산안법 제38·39조)이 대부분을 덮으므로 잡히는 건 '구체 조문 불비'다.
- ⚠ 후보는 **법정만**(tier=='법정') — 권고(가이드)를 넣으면 '권고에만 있고 조문에 없는'
  핵심 불비 후보가 matched로 빠져나간다(실측: 적치물 제거 제안이 가이드 13단계에 매칭됐었음)
- 'LLM은 법령을 판단하지 않는다' 원칙과의 관계: 검수로 확정된 의무 목록에 대한 **텍스트 정렬**이고
  화면 라벨 'AI 정렬 — 검수 전'으로 수위를 못박는다.
- persist=False(평가 하니스)는 적립 안 함. 흐름 폴백(CI 경로)은 종전대로 무회귀.

## 3. 알고리즘 지형 (갱신)

- 런타임 LLM: Vision(서술) + RESOLVE(기인물 그룹 선택) + **ALIGN(제안↔조문 정렬, 신규)** —
  전부 닫힌 집합 선택·추측 금지·실패 시 graceful degrade. 조문을 고르는 LLM은 여전히 없다.
- 즉시조치 순위는 3등급 SR 신호라 실행마다 흔들린다(실측: 같은 사진에서 일반조문 세트 ↔
  지게차 전용 세트). 근본 수선 = '즉시성' 태그를 빌드타임 검수로 승격(§4-a)
- 자산 등급: 1등급 원문류 / 2등급 흐름·앵커 / 3등급 SR·NS·CI·SHE / 4등급 사진→SR 매핑

## 4. 다음 작업 큐

a. **'즉시성' 태그 빌드타임 승격** ⭐ — 런타임 SR 휴리스틱(3등급) 대신 흐름 2,463항목에
   "현장에서 즉시 실행 가능한 행위인가" 1패스(Sol 파이프라인 재사용). 스트립이 2등급이 된다
b. **legacy 갈래 계산 옵션화** — 벌칙·SHE·facet CI·표준절차·조문후보가 화면 소비자를 잃었다.
   플래그/lazy로 내려 파이프라인을 3단계 산출 중심으로 단순화 (근거가 1차 때보다 강해짐)
c. **불비 원장 배치 검토 파이프라인** — pending 누적분을 Sol로 4분류, 반복 상위부터
d. 앵커 정정 로그를 gold로 적립 · 체계도 문서 갱신
e. ~~⑤ 벌칙 조인~~ 폐기 — 벌칙 화면 삭제로 무의미해짐 (2026-08-09 사용자 결정)
f. ~~moellab 재배포~~ 완료(2026-08-09, 코드 전용 경로: update-ohs-code.sh — PG 보존).
   ⚠ **다음 데이터 버전업 전 필수**: update-ohs.sh는 PG 볼륨 wipe라 prod에 쌓이는 불비 원장
   (ohs_action_statute_gaps)·분석 기록이 소실된다 — 운영 테이블 보존 단계를 먼저 추가할 것

## 5. 운영/참조 데이터 분리 설계 (2026-08-09 설계 확정, 구현 전)

**왜**: prod PG에 성격이 다른 두 데이터가 한 DB에 산다. 참조(로컬 생성→dump 배포, 지워도 복원
가능)와 운영(프로덕션에서만 생성 — 불비 원장의 occurrence_count는 실사용 시간의 축적이라 재생성
불가). 데이터 버전업 `update-ohs.sh`가 볼륨 wipe라 운영이 같이 죽는다. 절차(선 dump·후 재주입)로
막는 건 사람이 지켜야만 안전 — 구조로 보장한다.

**경계 규칙 (테이블 출생지 기준)**:
- 참조 = `public` 스키마: 로컬 파이프라인 산출(kosha_guides·articles·SR·CI·sr_inferred…)
- 운영 = `ops` 스키마: 프로덕션 요청 처리 중 생성 — 현재 3종(ohs_analysis_records·
  ohs_hazard_code_gaps·ohs_action_statute_gaps) + **앞으로 프로덕션에서 태어나는 모든 테이블**
  (예정: 앵커 정정 로그). `ohs_safety_videos`는 코드 참조 없는 legacy 잔재 — 이사 대상 아님, 정리 후보.

**채택안 = 같은 DB 안 `ops` 스키마** (같은 볼륨·SQLAlchemy 엔진 1개 유지):
- 기각 ①절차만: 구조 보장 없음 ②별도 DB: 엔진·세션 이중화 — 문제 대비 과함 ③별도 컨테이너: 인프라 복잡성.

**구현 체크리스트** (코드 변경 극소):
1. backend: 운영 모델 3종에 `__table_args__ = {"schema": "ops"}` + `create_tables()`에서
   `CREATE SCHEMA IF NOT EXISTS ops` **선행** (스키마 없으면 create_all이 실패한다)
2. 1회 마이그레이션(로컬+prod): `ALTER TABLE public.ohs_* SET SCHEMA ops` — 메타데이터만, 데이터 무이동
3. build_bundle.sh: pg_dump에 `--schema=public` 명시 — 없으면 이사 전 옛 dump 형상이 restore 때
   public에 유령 ohs_* 테이블로 되살아난다
4. update-ohs.sh: 볼륨 wipe **폐지** → `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` + pg_restore.
   ops는 손대지 않음 — 원장 생존이 스크립트가 아니라 구조로 보장된다
5. verify-ohs.sh에 ops 카운트(원장 행수·분석 기록 수) 추가 — 배포 후 생존을 눈으로 확인
6. 적용 순서: 로컬 적용·검증 → 코드 배포(update-ohs-code.sh) → prod ALTER 1회 → 다음 데이터
   버전업부터 새 update-ohs.sh 사용

## 6. 검증 방법

- 테스트 사진: `/tmp/forklift.jpg` → `cd /tmp && curl -X POST .../analysis/image -F "image=@forklift.jpg" -H "Expect:"`
- 검증된 analysis_id: 25864c1e-b719-408a-a360-bd874670ce03 (조문 즉시조치 6 + matched 2·unmatched 2)
- 원장 확인: `docker exec kosha-pg sh -c 'psql -U "$POSTGRES_USER" -d kosha -c "select * from ohs_action_statute_gaps"'`
- 서버: ohs-backend-dev(8001, **--reload 없음 — 코드 변경 시 재시작**)·ohs-frontend(5173, /ohs/)
