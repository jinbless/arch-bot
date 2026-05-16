"""V2: JSON 스키마 자체 검증 (15 케이스)."""
import json
import pytest
from jsonschema import Draft7Validator, validate, ValidationError
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import load_schema, SCHEMA_DIR


# ── V2-1: 스키마 메타 검증 ──

SCHEMA_FILES = [
    "guide-inventory.schema.json",
    "guide-text-v2.schema.json",
    "ci-file.schema.json",
]


@pytest.mark.parametrize("schema_file", SCHEMA_FILES)
def test_schema_is_valid_draft7(schema_file):
    schema = load_schema(schema_file)
    Draft7Validator.check_schema(schema)


def _check_additional_properties(obj, path=""):
    """재귀적으로 additionalProperties: false 확인."""
    issues = []
    if isinstance(obj, dict):
        if obj.get("type") == "object" and "properties" in obj:
            if obj.get("additionalProperties") is not False:
                issues.append(path or "root")
        for k, v in obj.items():
            if k in ("properties", "definitions", "$defs", "items", "patternProperties"):
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        issues.extend(_check_additional_properties(vv, f"{path}.{k}.{kk}"))
            elif isinstance(v, dict):
                issues.extend(_check_additional_properties(v, f"{path}.{k}"))
    return issues


@pytest.mark.parametrize("schema_file", SCHEMA_FILES)
def test_additional_properties_false(schema_file):
    schema = load_schema(schema_file)
    issues = _check_additional_properties(schema)
    assert issues == [], f"additionalProperties not false at: {issues}"


# ── V2-2: 최소 유효 문서 통과 ──

def test_minimal_inventory_passes():
    schema = load_schema("guide-inventory.schema.json")
    doc = {
        "metadata": {
            "generatedAt": "2026-04-12T00:00:00Z",
            "totalGuides": 1,
            "domainCounts": {"A": 1, "B": 0, "C": 0, "D": 0, "E": 0},
            "processingOrder": ["D", "A", "B", "C", "E"],
            "duplicateShortCodes": [],
        },
        "guides": [{
            "guideCode": "A-G-4-2025",
            "shortCode": "AG4",
            "title": "테스트",
            "domain": "A",
            "year": 2025,
            "pdfPath": "A/test.pdf",
        }],
    }
    validate(doc, schema)


def test_minimal_guide_text_passes():
    schema = load_schema("guide-text-v2.schema.json")
    doc = {
        "metadata": {
            "guideCode": "A-G-4-2025",
            "shortCode": "AG4",
            "title": "테스트",
            "totalPages": 1,
            "pdfPath": "data-team/01-parsing/kosha-guides/rawPDF/A/test.pdf",
            "parsedAt": "2026-04-12T00:00:00Z",
            "parsedBy": "step2-text-extraction v2.0",
            "tocSections": [
                {"sectionNumber": "1", "title": "목적", "startPage": 1}
            ],
        },
        "sections": [{
            "sectionNumber": "1",
            "sectionTitle": "목적",
            "pages": [1, 2],
            "text": "이 지침은...",
            "tables": [],
            "images": [],
        }],
    }
    validate(doc, schema)


def test_minimal_ci_file_passes():
    schema = load_schema("ci-file.schema.json")
    doc = {
        "metadata": {
            "guideCode": "A-G-4-2025",
            "shortCode": "AG4",
            "domain": "A",
            "extractedAt": "2026-04-12T00:00:00Z",
            "extractedBy": "test",
            "batchId": None,
        },
        "checklistItems": [],
        "domainTerms": [],
        "workProcesses": [],
        "equipmentSpecs": [],
        "documentRequirements": [],
    }
    validate(doc, schema)


# ── V2-3: 의도적 무효 문서 거부 ──

def test_inventory_empty_title_fails():
    schema = load_schema("guide-inventory.schema.json")
    doc = {
        "metadata": {
            "generatedAt": "2026-04-12T00:00:00Z",
            "totalGuides": 1,
            "domainCounts": {"A": 1, "B": 0, "C": 0, "D": 0, "E": 0},
            "processingOrder": ["D", "A", "B", "C", "E"],
            "duplicateShortCodes": [],
        },
        "guides": [{
            "guideCode": "A-G-4-2025",
            "shortCode": "AG4",
            "title": "",
            "domain": "A",
            "year": 2025,
            "pdfPath": "A/test.pdf",
        }],
    }
    with pytest.raises(ValidationError):
        validate(doc, schema)


def test_inventory_extra_field_fails():
    schema = load_schema("guide-inventory.schema.json")
    doc = {
        "metadata": {
            "generatedAt": "2026-04-12T00:00:00Z",
            "totalGuides": 0,
            "domainCounts": {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0},
            "processingOrder": ["D", "A", "B", "C", "E"],
            "duplicateShortCodes": [],
            "extraField": True,
        },
        "guides": [],
    }
    with pytest.raises(ValidationError):
        validate(doc, schema)


def test_inventory_bad_domain_fails():
    schema = load_schema("guide-inventory.schema.json")
    doc = {
        "metadata": {
            "generatedAt": "2026-04-12T00:00:00Z",
            "totalGuides": 1,
            "domainCounts": {"A": 1, "B": 0, "C": 0, "D": 0, "E": 0},
            "processingOrder": ["D", "A", "B", "C", "E"],
            "duplicateShortCodes": [],
        },
        "guides": [{
            "guideCode": "X-1-2025",
            "shortCode": "X1",
            "title": "test",
            "domain": "X",
            "year": 2025,
            "pdfPath": "X/test.pdf",
        }],
    }
    with pytest.raises(ValidationError):
        validate(doc, schema)


def test_guide_text_missing_sections_fails():
    schema = load_schema("guide-text-v2.schema.json")
    doc = {
        "metadata": {
            "guideCode": "A-G-4-2025",
            "shortCode": "AG4",
            "title": "테스트",
            "totalPages": 1,
            "pdfPath": "data-team/01-parsing/kosha-guides/rawPDF/A/test.pdf",
            "parsedAt": "2026-04-12T00:00:00Z",
            "parsedBy": "test",
            "tocSections": [
                {"sectionNumber": "1", "title": "목적", "startPage": 1}
            ],
        },
    }
    with pytest.raises(ValidationError):
        validate(doc, schema)


def test_guide_text_empty_toc_fails():
    schema = load_schema("guide-text-v2.schema.json")
    doc = {
        "metadata": {
            "guideCode": "A-G-4-2025",
            "shortCode": "AG4",
            "title": "테스트",
            "totalPages": 1,
            "pdfPath": "data-team/01-parsing/kosha-guides/rawPDF/A/test.pdf",
            "parsedAt": "2026-04-12T00:00:00Z",
            "parsedBy": "test",
            "tocSections": [],
        },
        "sections": [],
    }
    with pytest.raises(ValidationError):
        validate(doc, schema)


def test_guide_text_extra_field_fails():
    schema = load_schema("guide-text-v2.schema.json")
    doc = {
        "metadata": {
            "guideCode": "A-G-4-2025",
            "shortCode": "AG4",
            "title": "테스트",
            "totalPages": 1,
            "pdfPath": "data-team/01-parsing/kosha-guides/rawPDF/A/test.pdf",
            "parsedAt": "2026-04-12T00:00:00Z",
            "parsedBy": "test",
            "tocSections": [
                {"sectionNumber": "1", "title": "목적", "startPage": 1}
            ],
            "extra": True,
        },
        "sections": [],
    }
    with pytest.raises(ValidationError):
        validate(doc, schema)


def test_ci_file_missing_checklist_fails():
    schema = load_schema("ci-file.schema.json")
    doc = {
        "metadata": {
            "guideCode": "A-G-4-2025",
            "shortCode": "AG4",
            "domain": "A",
            "extractedAt": "2026-04-12T00:00:00Z",
            "extractedBy": "test",
            "batchId": None,
        },
        "domainTerms": [],
        "workProcesses": [],
        "equipmentSpecs": [],
        "documentRequirements": [],
    }
    with pytest.raises(ValidationError):
        validate(doc, schema)


def test_ci_file_bad_binding_force_fails():
    schema = load_schema("ci-file.schema.json")
    doc = {
        "metadata": {
            "guideCode": "A-G-4-2025",
            "shortCode": "AG4",
            "domain": "A",
            "extractedAt": "2026-04-12T00:00:00Z",
            "extractedBy": "test",
            "batchId": None,
        },
        "checklistItems": [{
            "identifier": "CI-AG4-001",
            "text": "test",
            "guideContext": None,
            "additionalDetail": None,
            "workProcessPhase": None,
            "bindingForce": "OPTIONAL",
            "requirementType": None,
            "sourceSection": "1",
            "basedOn": None,
        }],
        "domainTerms": [],
        "workProcesses": [],
        "equipmentSpecs": [],
        "documentRequirements": [],
    }
    with pytest.raises(ValidationError):
        validate(doc, schema)


def test_ci_file_bad_document_type_fails():
    schema = load_schema("ci-file.schema.json")
    doc = {
        "metadata": {
            "guideCode": "A-G-4-2025",
            "shortCode": "AG4",
            "domain": "A",
            "extractedAt": "2026-04-12T00:00:00Z",
            "extractedBy": "test",
            "batchId": None,
        },
        "checklistItems": [],
        "domainTerms": [],
        "workProcesses": [],
        "equipmentSpecs": [],
        "documentRequirements": [{
            "identifier": "DR-AG4-001",
            "documentType": "OTHER",
            "title": "test",
            "requiredSections": None,
            "sourceSection": "1",
            "relatedSR": None,
        }],
    }
    with pytest.raises(ValidationError):
        validate(doc, schema)
