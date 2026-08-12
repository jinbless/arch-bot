"""화기 그룹 '지금 당장' 스모크 — 실DB(SR 순위 신호)로 정렬·urgency를 눈으로 확인 (LLM 0).

용법: cd serving-team/08-app/backend && .venv/bin/python scripts/smoke_fire_actnow.py
전제: kosha PG 접속(backend/.env의 DATABASE_URL). 코드셋 3종으로 prod 5222 시나리오를 재현한다:
  ["FALL"]                        — 수정 전 5222의 canonical 경로 그대로(화재 미포함)
  ["FALL","FIRE_AND_EXPLOSION"]  — hazard-직결 경로 합류 후(수정 후 실제 입력)
  ["TRASH_BIN_FIRE"]             — 쓰레기통 화재 fine 코드(canonical FIRE_INJURY 경로)
"""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

for line in (BACKEND / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from app.services import flow_service  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402

GK = "절2 화기 등의 관리"
CODESETS = [["FALL"], ["FALL", "FIRE_AND_EXPLOSION"], ["TRASH_BIN_FIRE"]]

wf = flow_service.by_group_key(GK)
assert wf is not None, "화기 흐름 없음 — trackA 동기화 확인"
db = SessionLocal()

sohwagigu = next(((it.ref, it.text) for s in wf.slots if s.key == "PRECHECK"
                  for it in s.items if "소화기구" in it.text), None)
print(f"[모집단] 별표 소화기구 항목 = {sohwagigu!r}")

for codes in CODESETS:
    rows = flow_service.statute_actions(wf, list(codes), db)
    print(f"\n=== codes={codes} ===")
    for i, r in enumerate(rows, 1):
        flag = "APX" if r.get("appendix") else "   "
        print(f" {i}. {flag} hit={str(r['hazard_hit'])[:1]} act={str(r['actable'])[:1]} "
              f"[{r['ref'][:24]}] {r['title'][:36]}")

# matched 부스트 재현 — GPT가 '소화기 비치'를 냈고 align이 별표 항목과 matched된 상황.
# (ref, text) 쌍 — 별표 항목들은 ref 문자열을 공유하므로 ref 단독이면 5건이 한꺼번에 부스트된다.
if sohwagigu:
    rows = flow_service.statute_actions(wf, ["FALL"], db, matched_refs={sohwagigu})
    print(f"\n=== codes=['FALL'] + matched(소화기구) ===")
    for i, r in enumerate(rows, 1):
        print(f" {i}. m={str(r['matched'])[:1]} [{r['ref'][:24]}] {r['title'][:36]}")
print("\nSMOKE DONE")
