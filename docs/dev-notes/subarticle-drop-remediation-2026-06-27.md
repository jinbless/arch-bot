# 의N(제N조의M) 하위조항 누락·오염 버그 — 진단 및 수정 기록

> 2026-06-27. 사진→조문(Track A) gold 작업 중 굴착기 조항 점검에서 발견.
> 데이터 baseline에 영향하는 foundational fix. 관련 코드 커밋: `93a071c`.

## 1. 증상

kosha-pg `articles` 테이블에 `제N조의M`(의N) 하위조항이 **전부 누락**, 일부 base 조문이 **오염**.

```
SELECT COUNT(*) FROM articles WHERE article_code ~ '의[0-9]';  -- 0 / 1227
-- 제221조 title = '인양작업 시 조치' (실제 제221조의5 내용; 진짜 = '가스배관 등의 손상 방지')
-- 굴착기 제3관(제221조의2 충돌위험·의3 좌석안전띠·의4 잠금장치) 전부 부재
```

## 2. 근본 원인

legalize-kr 업스트림이 **JSON → Markdown으로 포맷 전환**(현재 `.json` 0개)했으나, 구
pipe-A `scripts/lib/legalize_reader.py`(JSON 전용)가 의N suffix를 보존하지 못해 base 코드로
붕괴 → `result[article_code] = {...}` **dict silent overwrite**로 문서순 마지막 형제만 생존.
frozen `data/article-texts.json`(legalize-kr commit `d8c121b`, 2026-04-11)에 baked되어 DB +
다운스트림(signatures/gimulmul/CWA) + 배포 서빙으로 전파.

- 전 법종 의N 17~33종 누락, base **26개 오염**(RULE 11 + OSHA 7 + DECREE 5 + ENFORCE 3).
- 오염 base 10/10 샘플이 의N 내용으로 교체 확인(제목·section·full_text 모두).

## 3. 수정

### 3.1 파서 (커밋 93a071c)
- `scripts/lib/legalize_md_reader.py` — `.md`(편/장/절/관/조) 파서. 의N 보존, section을
  `'편N 이름 > … > 관N 이름'`(gimulmul 호환)으로, **중복 코드 `DuplicateArticleError`**
  (silent overwrite 결함 영구 차단), 부칙 제외.
- `config/law-sources.json` → `.md` 경로(ENFORCE=`시행규칙.md`).
- `scripts/step0_extract_articles_md.py` → `data/article-texts.json` 재생성
  (1260조, 의N 33, commit `732764e9`). 구본 `.pre-md-backup`.

### 3.2 DB (비파괴 surgical, FK 보존)
- articles UPSERT: 의N 33 INSERT + 오염 base 26 교정. `ON CONFLICT (law_type,article_code)`.
- `scripts/_regen_affected_signatures.py`: 영향 RULE 27조(의N16+base11) 관찰 시그니처
  동기 재생성 → `article_signatures.jsonl`(669).
- `build_gimulmul_index.py` → 굴착기 그룹(절12>관3) 복구, observable 550.
- `embed_article_signatures.py` → `article_sig_emb.npz`(550,3072).
- 실행: `wsl -- bash -lc "cd /mnt/c/.../backend && ./.venv/bin/python …"`.

### 3.3 NS/SR/penalty 재포인팅 (무결성)
오염 11 RULE base의 기존 NS26/SR11/penalty11은 **내용이 의N을 정확히 기술하나 base코드로
오부착**. → `article_code`를 매칭 의N으로 재포인팅(내용 동일이라 재생성 불요).
예: `NS-RULE221-0~2` → 제221조의5, `SR-CONSTRUCTION_EQUIP-021` → 제221조의5.

### 3.4 배포 서빙 재배포 (moellab.info, surgical)
droplet `ohs-postgres`(kosha DB)도 동일 오염. **델타 SQL**(59 UPSERT + 재포인팅)을
`docker exec psql`로 적용 — `update-ohs.sh`(PG wipe) 대신. 백업 선행.
검증: 제221조=가스배관, 의N 33, total 1260, **sr_inferred_relations 103,295 / kosha_guides
1038 보존**, ohs-backend 재시작, 공개 URL 200, for-ceo 무영향.

## 4. 검증 (최종 정합)

| 레이어 | 결과 |
|---|---|
| kosha-pg articles | total 1260 · 의N 33 · V3 중복 0 · 제221조=가스배관 |
| article_signatures | 669 (영향 27조 재생성) |
| gimulmul_index | 113 그룹 · observable 550 · 굴착기 그룹 복구 |
| article_sig_emb | (550, 3072) |
| 배포 서빙 | 제221조의2~5 정상 · 103,295 보존 · 공개 200 |

## 5. 남은 enhancement (선택)

재포인팅 후 **진짜 base(가스배관 등) + 미커버 의N(의2/3/4)** 은 NS/SR/penalty 미보유
(원래 미커버). 서빙 SR경로 노출하려면 pipe-A `step2_prepare_batch --articles` → step3/5
LLM 생성 필요. **Track A(사진→조문)와 무관** — Track A 채점은 현 상태로 진행 가능.

## 6. 롤백

- article-texts: `data/article-texts.json.pre-md-backup`
- 로컬 DB: scratchpad `articles_backup_*.sql`
- 배포 DB: droplet `/root/ohs_remediation_backup_*.sql` (+ 로컬 사본)
