"""Hazard-Direct Pivot Phase 1 Day 1 — ONTOLOGY_OBSERVATION_SCHEMA 단위 테스트.

검증 범위:
- hazards[] 신규 필드 존재 + strict mode 호환
- risk_feature_candidates 기존 필드 병행 유지 (호환성/fallback)
- OpenAI strict mode invariants (additionalProperties=False, required=all properties)
- 표준 라벨 가이드가 prompt에 반영됨

실행:
  PYTHONIOENCODING=utf-8 python -m pytest serving-team/08-app/backend/tests/unit/test_ontology_schema.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _load_schema() -> dict:
    """openai_client.py에서 ONTOLOGY_OBSERVATION_SCHEMA 추출.

    httpx/openai 패키지 미설치 환경에서도 schema만 검증할 수 있도록 ast로 분리.
    """
    import json

    backend_root = Path(__file__).resolve().parents[2]
    catalog_path = backend_root / "app" / "data" / "risk_feature_catalog.json"
    src_path = backend_root / "app" / "integrations" / "openai_client.py"

    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    codes: set[str] = set()
    for _, axis_info in data.get("axes", {}).items():
        if isinstance(axis_info, dict):
            codes.update((axis_info.get("codes", {}) or {}).keys())

    src = src_path.read_text(encoding="utf-8")
    start = src.find("ONTOLOGY_OBSERVATION_SCHEMA = ")
    end = src.find("class OpenAIClient")
    snippet = "_ALL_CATALOG_CODES = " + repr(sorted(codes)) + "\n" + src[start:end]
    ns: dict = {}
    exec(snippet, ns)  # noqa: S102 — 테스트 한정, 신뢰된 소스
    return ns["ONTOLOGY_OBSERVATION_SCHEMA"]


def test_schema_top_level_has_hazards():
    schema = _load_schema()
    props = schema["schema"]["properties"]
    assert "hazards" in props, "hazards[] 필드가 schema에 추가되어야 함"
    assert "hazards" in schema["schema"]["required"], "hazards는 strict mode required"


def test_schema_keeps_risk_feature_candidates():
    """Pivot 호환성/fallback — risk_feature_candidates는 그대로 유지."""
    schema = _load_schema()
    props = schema["schema"]["properties"]
    assert "risk_feature_candidates" in props
    assert "risk_feature_candidates" in schema["schema"]["required"]


def test_hazards_items_required_full():
    """5개 필드 모두 required (OpenAI strict mode)."""
    schema = _load_schema()
    hz = schema["schema"]["properties"]["hazards"]
    assert hz["type"] == "array"
    item = hz["items"]
    expected = {"name", "risk_level", "location", "description", "preventive_measures"}
    assert set(item["required"]) == expected
    assert set(item["properties"].keys()) == expected
    assert item["additionalProperties"] is False


def test_hazards_risk_level_enum():
    schema = _load_schema()
    rl = schema["schema"]["properties"]["hazards"]["items"]["properties"]["risk_level"]
    assert set(rl["enum"]) == {"high", "medium", "low"}


def test_hazards_preventive_measures_is_string_array():
    schema = _load_schema()
    pm = schema["schema"]["properties"]["hazards"]["items"]["properties"]["preventive_measures"]
    assert pm["type"] == "array"
    assert pm["items"]["type"] == "string"


def test_schema_strict_mode_invariants():
    """모든 object scope에서 additionalProperties=False + required=all properties."""
    schema = _load_schema()
    assert schema["strict"] is True

    violations: list[str] = []

    def walk(obj, path: str) -> None:
        if isinstance(obj, dict):
            if obj.get("type") == "object" and "properties" in obj:
                if obj.get("additionalProperties") is not False:
                    violations.append(f"{path}: additionalProperties != False")
                req = set(obj.get("required", []))
                pk = set(obj["properties"].keys())
                missing = pk - req
                if missing:
                    violations.append(f"{path}: missing in required: {sorted(missing)}")
            for k, v in obj.items():
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")

    walk(schema["schema"], "ROOT")
    assert not violations, "strict mode 위반:\n" + "\n".join(violations)


def test_risk_feature_candidates_text_enum_still_constrained():
    """Tier 3.A 유지: text는 catalog code enum 강제."""
    schema = _load_schema()
    rfc = schema["schema"]["properties"]["risk_feature_candidates"]
    text = rfc["items"]["properties"]["text"]
    # enum exists and contains expected accident_type codes
    assert "enum" in text, "Tier 3.A: text enum이 유지되어야 함"
    enum_set = set(text["enum"])
    assert "FALL" in enum_set or "FALL_FROM_HEIGHT" in enum_set
    assert len(enum_set) >= 400, f"catalog code 수 ≥ 400 (실제 {len(enum_set)})"


def test_prompt_mentions_hazards_section():
    """IMAGE_ANALYSIS_PROMPT에 hazards[] 추출 지침 + 표준 라벨이 포함되어야 함."""
    backend_root = Path(__file__).resolve().parents[2]
    prompt_src = (
        backend_root / "app" / "integrations" / "prompts" / "analysis_prompts.py"
    ).read_text(encoding="utf-8")
    assert "hazards" in prompt_src
    # 표준 라벨 일부 (Phase 1 plan의 핵심 14개 중 대표 4개)
    for label in ["끼임/협착", "추락", "감전", "유해물질"]:
        assert label in prompt_src, f"표준 라벨 '{label}' 누락"
    # name 키와 preventive_measures가 prompt에 언급되어야 함
    assert "preventive_measures" in prompt_src
    assert "risk_level" in prompt_src


if __name__ == "__main__":
    # 직접 실행 시 모든 테스트 호출
    tests = [
        test_schema_top_level_has_hazards,
        test_schema_keeps_risk_feature_candidates,
        test_hazards_items_required_full,
        test_hazards_risk_level_enum,
        test_hazards_preventive_measures_is_string_array,
        test_schema_strict_mode_invariants,
        test_risk_feature_candidates_text_enum_still_constrained,
        test_prompt_mentions_hazards_section,
    ]
    failures: list[str] = []
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except AssertionError as e:  # noqa: PERF203
            failures.append(f"{t.__name__}: {e}")
            print(f"[FAIL] {t.__name__}: {e}")
    print(f"--- {len(tests) - len(failures)}/{len(tests)} PASS ---")
    sys.exit(1 if failures else 0)
