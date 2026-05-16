"""JSON Schema 검증 래퍼.

모든 출력 파일은 저장 전에 반드시 이 모듈을 통해 검증한다.
"""

import json
from pathlib import Path

try:
    import jsonschema
    from jsonschema import Draft202012Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


def load_schema(schema_path: str | Path) -> dict:
    """JSON Schema 파일 로드."""
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def validate(data: dict, schema: dict) -> list[str]:
    """데이터를 JSON Schema로 검증.

    Returns:
        에러 메시지 리스트 (빈 리스트 = 검증 통과)
    """
    if not HAS_JSONSCHEMA:
        print("[WARN] jsonschema 미설치 — 스키마 검증 건너뜀")
        return []

    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.path) or "(root)"
        errors.append(f"[{path}] {error.message}")
    return errors


def validate_and_write(data: dict, schema_path: str | Path, output_path: str | Path) -> list[str]:
    """검증 후 파일 저장. 검증 실패 시 저장하지 않음.

    Returns:
        에러 메시지 리스트 (빈 리스트 = 저장 성공)
    """
    schema = load_schema(schema_path)
    errors = validate(data, schema)
    if errors:
        print(f"[ERROR] 스키마 검증 실패 ({len(errors)}건) — 파일 미저장: {output_path}")
        for e in errors[:10]:
            print(f"  {e}")
        if len(errors) > 10:
            print(f"  ... 외 {len(errors) - 10}건")
        return errors

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] 저장 완료: {output_path} ({output_path.stat().st_size:,} bytes)")
    return []
