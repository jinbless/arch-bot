"""소비자용 manifest 로더 — assembly-manifest.json의 profile별 ordered list 반환.

6개 소비자(run_shacl_rules / local_consistency_check / serve_facets / run_inference /
run_guide_hazard_rules + Fuseki Java[별도])가 하드코딩 리스트 대신 이걸 쓴다.

사용:
    import sys; sys.path.insert(0, "<ontology>/assembly"); import manifest
    for e in manifest.load_profile("shacl-materialize"):
        g.parse(str(e["path"]), format=e["format"])     # e: path/file/format/role/id
    data = manifest.paths("shacl-materialize", exclude_roles={"rules-shacl"})  # 분리 로딩
"""
from __future__ import annotations

import json
from pathlib import Path

ONT = Path(__file__).resolve().parent.parent          # ontology dir
_MANIFEST = ONT / "assembly-manifest.json"
RDFLIB_FMT = {"xml": "xml", "turtle": "turtle"}        # format → rdflib parser


def _data() -> dict:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def load_profile(profile: str) -> list[dict]:
    """profile의 ordered entry list. 각 entry: {path:Path, file, format, role, id}."""
    d = _data()
    if profile not in d["profiles"]:
        raise KeyError(f"unknown profile {profile!r}; have {sorted(d['profiles'])}")
    meta = {f["file"]: f for f in d["files"]}
    out = []
    for e in d["profiles"][profile]:
        m = meta.get(e["file"], {})
        out.append({"path": ONT / e["file"], "file": e["file"], "format": e["format"],
                    "role": m.get("role"), "id": m.get("id")})
    return out


def paths(profile: str, *, only_roles=None, exclude_roles=None) -> list[dict]:
    """role 필터링된 entry list (data/shapes/rules 분리 로딩용)."""
    out = []
    for e in load_profile(profile):
        if only_roles is not None and e["role"] not in only_roles:
            continue
        if exclude_roles is not None and e["role"] in exclude_roles:
            continue
        out.append(e)
    return out
