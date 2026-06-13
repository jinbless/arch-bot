#!/usr/bin/env python3
"""CAT-4 Stage 3 온라인 검증 — full ABox(1675) Openllet owl:Nothing=CONSISTENT.

kosha-fuseki 재시작 후 Openllet이 manifest serving 프로파일(이제 abox-she-full)을
재분류한다(~17-30분). 재분류 중엔 연결 reset/거부가 나므로 owl:Nothing ASK를 reset을
관통해 최대 ~40분 재시도하고, 0행/HTTP200이면 CONSISTENT, HTTP500이면 INCONSISTENT.

(일회성 검증 스크립트 — 결과만 stdout. CI 영구 게이트는 make consistency-gate.)
"""
from __future__ import annotations
import subprocess
import sys
import time

import httpx

ENDPOINT = "http://localhost:3030/kosha/sparql"
NOTHING_Q = "SELECT (COUNT(*) AS ?n) WHERE { ?s a <http://www.w3.org/2002/07/owl#Nothing> }"
COUNT_Q = ("PREFIX she: <https://cashtoss.info/ontology/risk/situation#> "
           "SELECT (COUNT(?s) AS ?n) WHERE { ?s a she:SituationalHazardPattern }")
MAX_WAIT_S = 2700  # 45분 상한
POLL_S = 20


def query(q: str, timeout: float = 30.0):
    r = httpx.post(ENDPOINT, data={"query": q},
                   headers={"Accept": "application/sparql-results+json"}, timeout=timeout)
    return r.status_code, r.text


def main() -> int:
    print("[1/3] kosha-fuseki 재시작 (manifest serving = full ABox 재적재)...", flush=True)
    subprocess.run(["docker", "restart", "kosha-fuseki"], check=True,
                   capture_output=True, text=True)
    print("[2/3] Openllet 재분류 대기 (reset 관통 재시도)...", flush=True)
    t0 = time.monotonic()
    verdict = None
    while time.monotonic() - t0 < MAX_WAIT_S:
        elapsed = int(time.monotonic() - t0)
        try:
            code, body = query(NOTHING_Q)
            if code == 200:
                # 0행이면 일관. COUNT(*)=0 확인.
                import json
                n = json.loads(body)["results"]["bindings"][0]["n"]["value"]
                verdict = ("CONSISTENT" if n == "0" else f"owl:Nothing={n}(INCONSISTENT)", 200)
                print(f"  [{elapsed}s] owl:Nothing count={n} HTTP200", flush=True)
                break
            elif code == 500:
                verdict = ("INCONSISTENT", 500)
                print(f"  [{elapsed}s] HTTP500 — 비일관", flush=True)
                break
            else:
                print(f"  [{elapsed}s] HTTP{code} (재분류 중?) 재시도", flush=True)
        except Exception as e:
            print(f"  [{elapsed}s] {type(e).__name__} (Openllet 준비 중) 재시도", flush=True)
        time.sleep(POLL_S)

    if verdict is None:
        print(f"[3/3] TIMEOUT {MAX_WAIT_S}s — 재분류 미완 또는 응답 없음", flush=True)
        return 2
    print(f"[3/3] owl:Nothing verdict: {verdict}", flush=True)
    # 보너스: SHE 패턴 수 (1675 기대) — 타임아웃 가능성 있어 best-effort.
    try:
        code, body = query(COUNT_Q, timeout=120.0)
        if code == 200:
            import json
            n = json.loads(body)["results"]["bindings"][0]["n"]["value"]
            print(f"  she:SituationalHazardPattern count = {n} (기대 1675)", flush=True)
    except Exception as e:
        print(f"  (SHE count 조회 skip: {type(e).__name__})", flush=True)
    print("FULL_ABOX_VERIFY_DONE", flush=True)
    return 0 if verdict[1] == 200 and verdict[0] == "CONSISTENT" else 1


if __name__ == "__main__":
    sys.exit(main())
