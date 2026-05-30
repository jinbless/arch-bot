#!/usr/bin/env python3
"""그래프 동치 비교기 — prefix 표준화의 '무변경 증명' 오라클.

각 .ttl을 git HEAD(변경 전)와 작업본(변경 후)으로 파싱해, 트리플 집합이
동치(blank node 포함 isomorphic)인지 검사. 짧은 이름만 바꾼 cosmetic 변경은
그래프가 100% 동일해야 하므로 ISO=동치. 데이터가 바뀐 파일은 diff를 출력.

사용:
  python .../compare_graphs.py <repo-relative-path.ttl> [<path2.ttl> ...]
  # 인자 없으면 git이 보고하는 변경된 *.ttl 전체 자동 비교
종료코드: 비교 대상 중 하나라도 파싱 실패 시 2. (동치 여부는 보고만)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from rdflib import Graph
from rdflib.compare import graph_diff, to_isomorphic

REPO = Path(__file__).resolve().parents[4]  # …/arch-bot


def _git(args: list[str]) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, text=True, encoding="utf-8").stdout


def _rel(path: str) -> str:
    p = Path(path)
    if p.is_absolute():
        p = p.relative_to(REPO)
    return p.as_posix()


def load(text: str) -> Graph:
    g = Graph()
    g.parse(data=text, format="turtle")
    return g


def compare(rel: str) -> bool:
    """True=동치(무변경), False=차이/오류."""
    before_txt = _git(["show", f"HEAD:{rel}"])
    after_path = REPO / rel
    if not before_txt.strip():
        print(f"  [신규] {rel} (HEAD에 없음 — 비교 생략)")
        return True
    if not after_path.exists():
        print(f"  [삭제] {rel} (작업본 없음)")
        return False
    try:
        gb = to_isomorphic(load(before_txt))
        ga = to_isomorphic(load(after_path.read_text(encoding="utf-8")))
    except Exception as e:  # noqa: BLE001
        print(f"  [파싱오류] {rel}: {e}")
        return False
    if gb == ga:
        print(f"  [동치] {rel}  ({len(ga)} triples — 무변경 확인)")
        return True
    _, only_before, only_after = graph_diff(gb, ga)
    print(f"  [차이] {rel}  -{len(only_before)} / +{len(only_after)} triples")
    for t in list(only_before)[:6]:
        print(f"      - {t[0]} {t[1]} {t[2]}")
    for t in list(only_after)[:6]:
        print(f"      + {t[0]} {t[1]} {t[2]}")
    return False


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = sys.argv[1:]
    if args:
        rels = [_rel(a) for a in args]
    else:  # git이 보고하는 변경된 .ttl 전체
        out = _git(["status", "--porcelain"])
        rels = [ln[3:].strip() for ln in out.splitlines()
                if ln.strip().endswith(".ttl")]
    if not rels:
        print("비교할 .ttl 변경 없음")
        return 0
    print(f"=== 그래프 동치 비교 ({len(rels)} 파일) ===")
    equiv = 0
    for rel in sorted(rels):
        if compare(rel):
            equiv += 1
    print(f"\n동치(무변경) {equiv}/{len(rels)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
