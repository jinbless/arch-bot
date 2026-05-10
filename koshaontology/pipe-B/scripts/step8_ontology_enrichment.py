#!/usr/bin/env python3
"""Guide ontology enrichment candidate builder.

This script is the replacement path for the old one-off faceted tagging
scripts. It stores evidence-bearing candidates first, then materializes only
conservative high-confidence links into asserted mapping tables.

Default mode is deterministic and reproducible. `--use-llm` can add broader
candidate coverage, but LLM rows stay candidates unless they also satisfy the
same conservative threshold checks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json


SCRIPT_DIR = Path(__file__).resolve().parent
PIPE_B_ROOT = SCRIPT_DIR.parent
ARCH_ROOT = PIPE_B_ROOT.parent.parent
OHS_DATA_DIR = ARCH_ROOT / "OHS" / "backend" / "app" / "data"

DB_PARAMS = dict(dbname="kosha", user="kosha", password="1229", host="localhost")

ASSERT_CONFIDENCE = 0.88
SERVING_CONFIDENCE = 0.65

ENTITY_TABLES = {
    "GUIDE": {
        "table": "kosha_guides",
        "id": "guide_code",
        "guide": "guide_code",
        "fields": ["title", "sub_category"],
    },
    "CI": {
        "table": "checklist_items",
        "id": "identifier",
        "guide": "source_guide",
        "fields": ["text", "guide_context", "additional_detail", "source_section"],
    },
    "WP": {
        "table": "work_processes",
        "id": "identifier",
        "guide": "source_guide",
        "fields": ["process_name", "safety_measures", "source_section"],
    },
    "ES": {
        "table": "equipment_specs",
        "id": "identifier",
        "guide": "source_guide",
        "fields": ["equipment_name", "specifications", "source_section"],
    },
    "DR": {
        "table": "document_requirements",
        "id": "identifier",
        "guide": "source_guide",
        "fields": ["document_type", "title", "required_sections", "source_section"],
    },
    "DT": {
        "table": "domain_terms",
        "id": "identifier",
        "guide": "source_guide",
        "fields": ["term", "definition", "source_section"],
    },
}

ASSERT_MAPPING_TABLES = {
    "CI": ("ci_sr_mapping", "ci_id"),
    "WP": ("wp_sr_mapping", "wp_id"),
    "ES": ("es_sr_mapping", "es_id"),
    "DR": ("dr_sr_mapping", "dr_id"),
}

FACET_COLUMNS = {
    "CI": ("checklist_items", "identifier", {
        "accident_type": "accident_types",
        "hazardous_agent": "hazardous_agents",
        "work_context": "work_contexts",
    }),
    "WP": ("work_processes", "identifier", {
        "accident_type": "accident_types",
        "work_context": "work_contexts",
    }),
    "ES": ("equipment_specs", "identifier", {
        "work_context": "work_contexts",
    }),
    "DT": ("domain_terms", "identifier", {
        "hazardous_agent": "hazardous_agents",
        "work_context": "work_contexts",
    }),
}


@dataclass
class EntityRow:
    entity_type: str
    entity_id: str
    guide_code: str
    text: str
    source_fields: list[str]


@dataclass
class FeatureCandidate:
    entity_type: str
    entity_id: str
    guide_code: str
    axis: str
    feature_code: str
    confidence: float
    evidence: str
    source_fields: list[str]
    method: str
    non_llm_evidence_count: int = 1
    review_status: str = "candidate"


@dataclass
class SrCandidate:
    entity_type: str
    entity_id: str
    guide_code: str
    sr_id: str
    confidence: float
    evidence: str
    source_fields: list[str]
    method: str
    non_llm_evidence_count: int
    asserted: bool = False
    review_status: str = "candidate"


@dataclass
class TriggerCandidate:
    entity_type: str
    entity_id: str
    guide_code: str
    trigger_text: str
    cue_type: str
    confidence: float
    evidence: str
    source_fields: list[str]
    method: str
    review_status: str = "candidate"


@dataclass
class SrRow:
    identifier: str
    title: str
    text: str
    facets: dict[str, set[str]]


@dataclass
class RunStats:
    entities: int = 0
    feature_candidates: int = 0
    sr_candidates: int = 0
    visual_triggers: int = 0
    asserted_links: int = 0
    facet_updates: int = 0
    llm_guides: int = 0
    skipped_llm_guides: int = 0
    warnings: list[str] = field(default_factory=list)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_schema_response() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "guide_ontology_enrichment",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "feature_candidates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "entity_type": {"type": "string", "enum": ["GUIDE", "CI", "WP", "ES", "DR", "DT"]},
                                "entity_id": {"type": "string"},
                                "axis": {"type": "string", "enum": ["accident_type", "hazardous_agent", "work_context"]},
                                "feature_code": {"type": "string"},
                                "confidence": {"type": "number"},
                                "evidence": {"type": "string"},
                                "source_fields": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["entity_type", "entity_id", "axis", "feature_code", "confidence", "evidence", "source_fields"],
                            "additionalProperties": False,
                        },
                    },
                    "sr_link_candidates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "entity_type": {"type": "string", "enum": ["GUIDE", "CI", "WP", "ES", "DR", "DT"]},
                                "entity_id": {"type": "string"},
                                "sr_id": {"type": "string"},
                                "confidence": {"type": "number"},
                                "evidence": {"type": "string"},
                                "source_fields": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["entity_type", "entity_id", "sr_id", "confidence", "evidence", "source_fields"],
                            "additionalProperties": False,
                        },
                    },
                    "visual_trigger_candidates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "entity_type": {"type": "string", "enum": ["GUIDE", "CI", "WP", "ES", "DR", "DT"]},
                                "entity_id": {"type": "string"},
                                "trigger_text": {"type": "string"},
                                "cue_type": {"type": "string", "enum": ["object", "state", "absence", "environment", "activity", "other"]},
                                "confidence": {"type": "number"},
                                "evidence": {"type": "string"},
                                "source_fields": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["entity_type", "entity_id", "trigger_text", "cue_type", "confidence", "evidence", "source_fields"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["feature_candidates", "sr_link_candidates", "visual_trigger_candidates"],
                "additionalProperties": False,
            },
        },
    }


def load_taxonomy() -> dict[str, dict[str, list[str]]]:
    catalog = _read_json(OHS_DATA_DIR / "risk_feature_catalog.json")
    aliases = _read_json(OHS_DATA_DIR / "risk_feature_aliases.json")
    result: dict[str, dict[str, list[str]]] = {
        "accident_type": {},
        "hazardous_agent": {},
        "work_context": {},
    }

    for axis, axis_info in catalog.get("axes", {}).items():
        normalized_axis = axis
        if axis == "accident_type":
            normalized_axis = "accident_type"
        elif axis == "hazardous_agent":
            normalized_axis = "hazardous_agent"
        elif axis == "work_context":
            normalized_axis = "work_context"
        else:
            continue
        for code, meta in axis_info.get("codes", {}).items():
            terms = {code, str(meta.get("label") or "")}
            terms.update(str(sub) for sub in meta.get("sub", []) or [])
            result[normalized_axis].setdefault(code, [])
            result[normalized_axis][code].extend(t for t in terms if t)

    for axis, codes in aliases.get("tier1", {}).items():
        if axis not in result:
            continue
        for code, terms in codes.items():
            result[axis].setdefault(code, [])
            result[axis][code].extend(str(t) for t in terms if t)

    for axis, codes in result.items():
        for code, terms in list(codes.items()):
            deduped = sorted({t.strip() for t in terms if t and t.strip()}, key=len, reverse=True)
            result[axis][code] = deduped
    return result


def taxonomy_code_summary(taxonomy: dict[str, dict[str, list[str]]]) -> dict[str, list[str]]:
    return {axis: sorted(codes) for axis, codes in taxonomy.items()}


def compact_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def sentence_for_term(text: str, term: str) -> str:
    if not text:
        return ""
    pattern = re.compile(r"[^.。!?！？\n\r]{0,80}" + re.escape(term) + r"[^.。!?！？\n\r]{0,80}", re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return re.sub(r"\s+", " ", match.group(0)).strip()
    idx = text.lower().find(term.lower())
    if idx >= 0:
        start = max(0, idx - 60)
        end = min(len(text), idx + len(term) + 60)
        return re.sub(r"\s+", " ", text[start:end]).strip()
    return re.sub(r"\s+", " ", text[:120]).strip()


def confidence_for_match(entity_type: str, evidence_count: int, term: str) -> float:
    base = {
        "GUIDE": 0.66,
        "CI": 0.73,
        "WP": 0.76,
        "ES": 0.70,
        "DR": 0.68,
        "DT": 0.70,
    }.get(entity_type, 0.68)
    length_bonus = 0.03 if len(term) >= 4 else 0.0
    count_bonus = min(0.14, max(0, evidence_count - 1) * 0.04)
    return round(min(0.92, base + length_bonus + count_bonus), 4)


def extract_features(entity: EntityRow, taxonomy: dict[str, dict[str, list[str]]]) -> list[FeatureCandidate]:
    text = entity.text
    candidates: list[FeatureCandidate] = []
    for axis, code_terms in taxonomy.items():
        for code, terms in code_terms.items():
            matched_terms = [term for term in terms if term and term.lower() in text.lower()]
            if not matched_terms:
                continue
            best = matched_terms[0]
            evidence = sentence_for_term(text, best)
            confidence = confidence_for_match(entity.entity_type, len(matched_terms), best)
            candidates.append(FeatureCandidate(
                entity_type=entity.entity_type,
                entity_id=entity.entity_id,
                guide_code=entity.guide_code,
                axis=axis,
                feature_code=code,
                confidence=confidence,
                evidence=evidence,
                source_fields=entity.source_fields,
                method="taxonomy_alias",
                non_llm_evidence_count=min(3, len(matched_terms)),
            ))
    return candidates


def load_srs(cur) -> list[SrRow]:
    cur.execute("""
        SELECT identifier, title, text, accident_types, hazardous_agents, work_contexts
        FROM safety_requirements
        ORDER BY identifier
    """)
    rows = []
    for identifier, title, text, accidents, agents, contexts in cur.fetchall():
        rows.append(SrRow(
            identifier=identifier,
            title=title or "",
            text=text or "",
            facets={
                "accident_type": set(accidents or []),
                "hazardous_agent": set(agents or []),
                "work_context": set(contexts or []),
            },
        ))
    return rows


def build_sr_candidates(entity: EntityRow, features: list[FeatureCandidate], srs: list[SrRow]) -> list[SrCandidate]:
    by_axis: dict[str, set[str]] = {"accident_type": set(), "hazardous_agent": set(), "work_context": set()}
    evidence_bits: dict[str, list[str]] = {}
    for candidate in features:
        by_axis.setdefault(candidate.axis, set()).add(candidate.feature_code)
        evidence_bits.setdefault(candidate.axis, []).append(candidate.evidence)

    results: list[SrCandidate] = []
    if not any(by_axis.values()):
        return results

    for sr in srs:
        matched_axes = []
        matched_codes = []
        for axis, codes in by_axis.items():
            hits = sorted(codes & sr.facets.get(axis, set()))
            if hits:
                matched_axes.append(axis)
                matched_codes.extend(hits)
        if not matched_axes:
            continue

        axis_count = len(matched_axes)
        total_hits = len(set(matched_codes))
        confidence = 0.48 + axis_count * 0.13 + min(0.15, total_hits * 0.03)
        if entity.entity_type == "WP":
            confidence += 0.04
        if entity.entity_type == "CI":
            confidence += 0.02
        confidence = round(min(0.94, confidence), 4)
        if confidence < SERVING_CONFIDENCE:
            continue

        evidence = "; ".join(dict.fromkeys(
            bit for axis in matched_axes for bit in evidence_bits.get(axis, []) if bit
        ))[:700]
        non_llm = min(3, axis_count + (1 if total_hits >= 2 else 0))
        asserted = confidence >= ASSERT_CONFIDENCE and non_llm >= 2
        results.append(SrCandidate(
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            guide_code=entity.guide_code,
            sr_id=sr.identifier,
            confidence=confidence,
            evidence=evidence or entity.text[:200],
            source_fields=entity.source_fields,
            method="facet_overlap",
            non_llm_evidence_count=non_llm,
            asserted=asserted,
            review_status="asserted" if asserted else "candidate",
        ))
    results.sort(key=lambda item: (item.asserted, item.confidence), reverse=True)
    return results[:12]


TRIGGER_PATTERNS = [
    ("absence", ["없", "미설치", "미착용", "미확보", "누락", "불량", "파손"]),
    ("state", ["노출", "개방", "접촉", "누출", "과열", "적재", "협착", "끼임"]),
    ("object", ["방호", "난간", "덮개", "안전대", "보호구", "환기", "접지", "비상정지"]),
]


def build_visual_triggers(entity: EntityRow, features: list[FeatureCandidate]) -> list[TriggerCandidate]:
    if entity.entity_type not in {"CI", "WP", "ES"}:
        return []
    triggers: list[TriggerCandidate] = []
    evidence_pool = [candidate.evidence for candidate in features if candidate.evidence]
    for evidence in dict.fromkeys(evidence_pool):
        cue_type = None
        for candidate_type, terms in TRIGGER_PATTERNS:
            if any(term in evidence for term in terms):
                cue_type = candidate_type
                break
        if not cue_type:
            continue
        trigger_text = evidence
        if len(trigger_text) > 120:
            trigger_text = trigger_text[:117].rstrip() + "..."
        triggers.append(TriggerCandidate(
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            guide_code=entity.guide_code,
            trigger_text=trigger_text,
            cue_type=cue_type,
            confidence=0.72,
            evidence=evidence,
            source_fields=entity.source_fields,
            method="evidence_phrase",
        ))
    return triggers[:4]


def candidate_to_prompt(entity: EntityRow, limit: int = 900) -> dict[str, Any]:
    text = re.sub(r"\s+", " ", entity.text).strip()
    return {
        "entity_type": entity.entity_type,
        "entity_id": entity.entity_id,
        "guide_code": entity.guide_code,
        "source_fields": entity.source_fields,
        "text": text[:limit],
    }


def guide_llm_prompt(
    guide_code: str,
    entities: list[EntityRow],
    taxonomy: dict[str, dict[str, list[str]]],
    srs: list[SrRow],
    sr_limit: int = 45,
) -> str:
    guide_entities = [entity for entity in entities if entity.guide_code == guide_code]
    entity_payload = [candidate_to_prompt(entity) for entity in guide_entities[:45]]
    combined_text = " ".join(entity.text for entity in guide_entities[:80])
    sr_scores: list[tuple[int, SrRow]] = []
    lower_text = combined_text.lower()
    for sr in srs:
        hit_count = 0
        for values in sr.facets.values():
            for code in values:
                if code.lower() in lower_text:
                    hit_count += 1
        if hit_count:
            sr_scores.append((hit_count, sr))
    sr_scores.sort(key=lambda item: item[0], reverse=True)
    sr_payload = [
        {
            "sr_id": sr.identifier,
            "title": sr.title,
            "text": sr.text[:350],
            "facets": {axis: sorted(values) for axis, values in sr.facets.items()},
        }
        for _, sr in sr_scores[:sr_limit]
    ]
    return json.dumps({
        "task": (
            "Generate conservative ontology enrichment candidates. Use only the provided "
            "taxonomy codes and SR ids. Every candidate must include an evidence span copied "
            "from entity text. Do not claim legal certainty; SR links are candidates."
        ),
        "guide_code": guide_code,
        "taxonomy_codes": taxonomy_code_summary(taxonomy),
        "entities": entity_payload,
        "sr_shortlist": sr_payload,
    }, ensure_ascii=False)


def run_llm_for_guide(
    guide_code: str,
    entities: list[EntityRow],
    taxonomy: dict[str, dict[str, list[str]]],
    srs: list[SrRow],
    model: str,
) -> tuple[list[FeatureCandidate], list[SrCandidate], list[TriggerCandidate]]:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "developer",
                "content": (
                    "You enrich KOSHA Guide ontology data. Return strict JSON only. "
                    "Be conservative: evidence must be visible in the provided entity text."
                ),
            },
            {"role": "user", "content": guide_llm_prompt(guide_code, entities, taxonomy, srs)},
        ],
        response_format=_json_schema_response(),
        max_tokens=6000,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    entity_map = {
        (entity.entity_type, entity.entity_id): entity
        for entity in entities
        if entity.guide_code == guide_code
    }
    sr_ids = {sr.identifier for sr in srs}
    feature_codes = {
        axis: set(codes.keys())
        for axis, codes in taxonomy.items()
    }

    feature_rows: list[FeatureCandidate] = []
    sr_rows: list[SrCandidate] = []
    trigger_rows: list[TriggerCandidate] = []

    for item in data.get("feature_candidates", []):
        key = (item["entity_type"], item["entity_id"])
        entity = entity_map.get(key)
        if not entity or item["feature_code"] not in feature_codes.get(item["axis"], set()):
            continue
        evidence = str(item["evidence"]).strip()
        if not evidence:
            continue
        feature_rows.append(FeatureCandidate(
            entity_type=item["entity_type"],
            entity_id=item["entity_id"],
            guide_code=entity.guide_code,
            axis=item["axis"],
            feature_code=item["feature_code"],
            confidence=round(min(0.86, max(0.0, float(item["confidence"]))), 4),
            evidence=evidence,
            source_fields=list(item.get("source_fields") or entity.source_fields),
            method="llm_candidate",
            non_llm_evidence_count=0,
        ))

    for item in data.get("sr_link_candidates", []):
        key = (item["entity_type"], item["entity_id"])
        entity = entity_map.get(key)
        if not entity or item["sr_id"] not in sr_ids:
            continue
        evidence = str(item["evidence"]).strip()
        if not evidence:
            continue
        confidence = round(min(0.86, max(0.0, float(item["confidence"]))), 4)
        if confidence < SERVING_CONFIDENCE:
            continue
        sr_rows.append(SrCandidate(
            entity_type=item["entity_type"],
            entity_id=item["entity_id"],
            guide_code=entity.guide_code,
            sr_id=item["sr_id"],
            confidence=confidence,
            evidence=evidence,
            source_fields=list(item.get("source_fields") or entity.source_fields),
            method="llm_candidate",
            non_llm_evidence_count=0,
            asserted=False,
        ))

    for item in data.get("visual_trigger_candidates", []):
        key = (item["entity_type"], item["entity_id"])
        entity = entity_map.get(key)
        if not entity:
            continue
        evidence = str(item["evidence"]).strip()
        trigger = str(item["trigger_text"]).strip()
        if not evidence or not trigger:
            continue
        trigger_rows.append(TriggerCandidate(
            entity_type=item["entity_type"],
            entity_id=item["entity_id"],
            guide_code=entity.guide_code,
            trigger_text=trigger[:160],
            cue_type=item.get("cue_type") or "other",
            confidence=round(min(0.86, max(0.0, float(item["confidence"]))), 4),
            evidence=evidence,
            source_fields=list(item.get("source_fields") or entity.source_fields),
            method="llm_candidate",
        ))

    return feature_rows, sr_rows, trigger_rows


def load_entities(cur, guide_filter: list[str], entity_types: set[str], limit_guides: int | None) -> list[EntityRow]:
    guides_sql = "SELECT guide_code FROM kosha_guides"
    params: list[Any] = []
    if guide_filter:
        guides_sql += " WHERE guide_code = ANY(%s)"
        params.append(guide_filter)
    guides_sql += " ORDER BY guide_code"
    if limit_guides:
        guides_sql += " LIMIT %s"
        params.append(limit_guides)
    cur.execute(guides_sql, params)
    guide_codes = [row[0] for row in cur.fetchall()]
    if not guide_codes:
        return []

    entities: list[EntityRow] = []
    for entity_type, meta in ENTITY_TABLES.items():
        if entity_type not in entity_types:
            continue
        fields = meta["fields"]
        columns = ", ".join([meta["id"], meta["guide"], *fields])
        cur.execute(
            f"SELECT {columns} FROM {meta['table']} WHERE {meta['guide']} = ANY(%s) ORDER BY {meta['guide']}, {meta['id']}",
            (guide_codes,),
        )
        for row in cur.fetchall():
            entity_id = row[0]
            guide_code = row[1]
            field_values = row[2:]
            text_parts = []
            source_fields = []
            for field_name, value in zip(fields, field_values):
                text = compact_text(value)
                if text:
                    text_parts.append(text)
                    source_fields.append(field_name)
            if not text_parts:
                continue
            entities.append(EntityRow(
                entity_type=entity_type,
                entity_id=entity_id,
                guide_code=guide_code,
                text=" ".join(text_parts),
                source_fields=source_fields,
            ))
    return entities


def upsert_feature_candidates(cur, rows: list[FeatureCandidate]) -> None:
    for row in rows:
        cur.execute("""
            INSERT INTO guide_entity_feature_candidates
              (entity_type, entity_id, guide_code, axis, feature_code, confidence,
               evidence, source_fields, method, review_status, non_llm_evidence_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            ON CONFLICT (entity_type, entity_id, axis, feature_code, method) DO UPDATE SET
              confidence = GREATEST(guide_entity_feature_candidates.confidence, EXCLUDED.confidence),
              evidence = EXCLUDED.evidence,
              source_fields = EXCLUDED.source_fields,
              review_status = EXCLUDED.review_status,
              non_llm_evidence_count = GREATEST(
                  guide_entity_feature_candidates.non_llm_evidence_count,
                  EXCLUDED.non_llm_evidence_count
              )
        """, (
            row.entity_type, row.entity_id, row.guide_code, row.axis, row.feature_code,
            Decimal(str(row.confidence)), row.evidence, json.dumps(row.source_fields, ensure_ascii=False),
            row.method, row.review_status, row.non_llm_evidence_count,
        ))


def upsert_sr_candidates(cur, rows: list[SrCandidate], apply_asserted: bool) -> int:
    asserted_count = 0
    for row in rows:
        cur.execute("""
            INSERT INTO guide_sr_link_candidates
              (entity_type, entity_id, guide_code, sr_id, confidence, evidence,
               source_fields, method, review_status, non_llm_evidence_count, asserted)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
            ON CONFLICT (entity_type, entity_id, sr_id, method) DO UPDATE SET
              confidence = GREATEST(guide_sr_link_candidates.confidence, EXCLUDED.confidence),
              evidence = EXCLUDED.evidence,
              source_fields = EXCLUDED.source_fields,
              review_status = EXCLUDED.review_status,
              non_llm_evidence_count = GREATEST(
                  guide_sr_link_candidates.non_llm_evidence_count,
                  EXCLUDED.non_llm_evidence_count
              ),
              asserted = guide_sr_link_candidates.asserted OR EXCLUDED.asserted
        """, (
            row.entity_type, row.entity_id, row.guide_code, row.sr_id,
            Decimal(str(row.confidence)), row.evidence,
            json.dumps(row.source_fields, ensure_ascii=False), row.method,
            row.review_status, row.non_llm_evidence_count, row.asserted,
        ))
        if apply_asserted and row.asserted and row.entity_type in ASSERT_MAPPING_TABLES:
            table, id_column = ASSERT_MAPPING_TABLES[row.entity_type]
            cur.execute(
                f"INSERT INTO {table} ({id_column}, sr_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (row.entity_id, row.sr_id),
            )
            asserted_count += cur.rowcount
    return asserted_count


def upsert_visual_triggers(cur, rows: list[TriggerCandidate]) -> None:
    for row in rows:
        cur.execute("""
            INSERT INTO guide_visual_trigger_candidates
              (entity_type, entity_id, guide_code, trigger_text, cue_type, confidence,
               evidence, source_fields, method, review_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (entity_type, entity_id, trigger_text, method) DO UPDATE SET
              confidence = GREATEST(guide_visual_trigger_candidates.confidence, EXCLUDED.confidence),
              cue_type = EXCLUDED.cue_type,
              evidence = EXCLUDED.evidence,
              source_fields = EXCLUDED.source_fields,
              review_status = EXCLUDED.review_status
        """, (
            row.entity_type, row.entity_id, row.guide_code, row.trigger_text, row.cue_type,
            Decimal(str(row.confidence)), row.evidence,
            json.dumps(row.source_fields, ensure_ascii=False), row.method, row.review_status,
        ))


def apply_feature_facets(cur, entity_type: str, entity_id: str, candidates: list[FeatureCandidate]) -> bool:
    if entity_type not in FACET_COLUMNS:
        return False
    table, id_column, columns = FACET_COLUMNS[entity_type]
    values_by_column: dict[str, set[str]] = {}
    for candidate in candidates:
        if candidate.confidence < SERVING_CONFIDENCE:
            continue
        column = columns.get(candidate.axis)
        if not column:
            continue
        values_by_column.setdefault(column, set()).add(candidate.feature_code)
    if not values_by_column:
        return False

    set_parts = []
    params: list[Any] = []
    for column, values in sorted(values_by_column.items()):
        set_parts.append(f"{column} = %s::jsonb")
        params.append(json.dumps(sorted(values), ensure_ascii=False))
    params.append(entity_id)
    cur.execute(f"UPDATE {table} SET {', '.join(set_parts)} WHERE {id_column} = %s", params)
    return cur.rowcount > 0


def clear_candidate_tables(cur, guide_filter: list[str]) -> None:
    if guide_filter:
        for table in [
            "guide_visual_trigger_candidates",
            "guide_sr_link_candidates",
            "guide_entity_feature_candidates",
        ]:
            cur.execute(f"DELETE FROM {table} WHERE guide_code = ANY(%s)", (guide_filter,))
        return
    for table in [
        "guide_visual_trigger_candidates",
        "guide_sr_link_candidates",
        "guide_entity_feature_candidates",
    ]:
        cur.execute(f"TRUNCATE {table} RESTART IDENTITY")


def load_existing_asserted_candidates(cur) -> tuple[list[SrCandidate], list[FeatureCandidate]]:
    sr_candidates: list[SrCandidate] = []
    feature_candidates: list[FeatureCandidate] = []

    mapping_queries = [
        ("CI", "checklist_items", "identifier", "source_guide", "ci_sr_mapping", "ci_id"),
        ("WP", "work_processes", "identifier", "source_guide", "wp_sr_mapping", "wp_id"),
        ("ES", "equipment_specs", "identifier", "source_guide", "es_sr_mapping", "es_id"),
        ("DR", "document_requirements", "identifier", "source_guide", "dr_sr_mapping", "dr_id"),
        ("DT", "domain_terms", "identifier", "source_guide", "dt_sr_mapping", "dt_id"),
    ]
    for entity_type, table, id_col, guide_col, map_table, map_id in mapping_queries:
        cur.execute(f"""
            SELECT e.{id_col}, e.{guide_col}, m.sr_id
            FROM {table} e
            JOIN {map_table} m ON m.{map_id} = e.{id_col}
        """)
        for entity_id, guide_code, sr_id in cur.fetchall():
            sr_candidates.append(SrCandidate(
                entity_type=entity_type,
                entity_id=entity_id,
                guide_code=guide_code,
                sr_id=sr_id,
                confidence=1.0,
                evidence="existing asserted mapping",
                source_fields=["existing_mapping"],
                method="existing_mapping",
                non_llm_evidence_count=3,
                asserted=True,
                review_status="asserted",
            ))
    return sr_candidates, feature_candidates


def write_report(stats: RunStats, report_path: Path | None) -> None:
    if not report_path:
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "entities": stats.entities,
        "feature_candidates": stats.feature_candidates,
        "sr_candidates": stats.sr_candidates,
        "visual_triggers": stats.visual_triggers,
        "asserted_links": stats.asserted_links,
        "facet_updates": stats.facet_updates,
        "llm_guides": stats.llm_guides,
        "skipped_llm_guides": stats.skipped_llm_guides,
        "warnings": stats.warnings,
        "thresholds": {
            "serving_candidate": SERVING_CONFIDENCE,
            "asserted": ASSERT_CONFIDENCE,
            "asserted_non_llm_evidence_count": 2,
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipe-B ontology enrichment candidates")
    parser.add_argument("--guide", action="append", default=[], help="guide_code 필터. 여러 번 지정 가능")
    parser.add_argument("--limit-guides", type=int, help="처리할 guide 수 제한")
    parser.add_argument("--entity-types", default="GUIDE,CI,WP,ES,DR,DT", help="콤마 구분 entity type")
    parser.add_argument("--reset-candidates", action="store_true", help="대상 guide 후보 테이블 초기화")
    parser.add_argument("--apply-facets", action="store_true", help="candidate 기반 facet JSONB 컬럼 업데이트")
    parser.add_argument("--apply-asserted", action="store_true", help="고신뢰 SR 후보를 asserted mapping table에 반영")
    parser.add_argument("--include-existing", action="store_true", help="기존 mapping을 candidate table에 trace row로 저장")
    parser.add_argument("--dry-run", action="store_true", help="DB 쓰기 없이 통계만 출력")
    parser.add_argument("--report", type=Path, help="JSON report path")
    parser.add_argument("--use-llm", action="store_true", help="Guide 단위 LLM 후보 생성을 추가 수행")
    parser.add_argument("--llm-model", default="gpt-4.1-mini", help="LLM 후보 생성 모델")
    parser.add_argument("--llm-guide-limit", type=int, help="LLM 처리 guide 수 제한")
    args = parser.parse_args()

    entity_types = {item.strip().upper() for item in args.entity_types.split(",") if item.strip()}
    unknown = entity_types - set(ENTITY_TABLES)
    if unknown:
        raise SystemExit(f"Unknown entity types: {sorted(unknown)}")

    if args.use_llm:
        if not os.environ.get("OPENAI_API_KEY"):
            raise SystemExit("--use-llm requires OPENAI_API_KEY")

    taxonomy = load_taxonomy()
    stats = RunStats()

    conn = psycopg2.connect(**DB_PARAMS)
    try:
        cur = conn.cursor()
        if args.reset_candidates and not args.dry_run:
            clear_candidate_tables(cur, args.guide)
            conn.commit()

        srs = load_srs(cur)
        entities = load_entities(cur, args.guide, entity_types, args.limit_guides)
        stats.entities = len(entities)

        if args.include_existing:
            existing_sr, existing_feature = load_existing_asserted_candidates(cur)
            stats.sr_candidates += len(existing_sr)
            stats.feature_candidates += len(existing_feature)
            if not args.dry_run:
                upsert_sr_candidates(cur, existing_sr, apply_asserted=False)
                upsert_feature_candidates(cur, existing_feature)
                conn.commit()

        for idx, entity in enumerate(entities, 1):
            feature_candidates = extract_features(entity, taxonomy)
            sr_candidates = build_sr_candidates(entity, feature_candidates, srs)
            visual_triggers = build_visual_triggers(entity, feature_candidates)

            stats.feature_candidates += len(feature_candidates)
            stats.sr_candidates += len(sr_candidates)
            stats.visual_triggers += len(visual_triggers)

            if not args.dry_run:
                upsert_feature_candidates(cur, feature_candidates)
                stats.asserted_links += upsert_sr_candidates(
                    cur,
                    sr_candidates,
                    apply_asserted=args.apply_asserted,
                )
                upsert_visual_triggers(cur, visual_triggers)
                if args.apply_facets and apply_feature_facets(cur, entity.entity_type, entity.entity_id, feature_candidates):
                    stats.facet_updates += 1

            if idx % 1000 == 0 and not args.dry_run:
                conn.commit()
                print(f"  processed {idx}/{len(entities)} entities")

        if args.use_llm:
            guide_codes = sorted({entity.guide_code for entity in entities})
            if args.llm_guide_limit:
                guide_codes = guide_codes[:args.llm_guide_limit]
            for guide_idx, guide_code in enumerate(guide_codes, 1):
                try:
                    llm_features, llm_srs, llm_triggers = run_llm_for_guide(
                        guide_code=guide_code,
                        entities=entities,
                        taxonomy=taxonomy,
                        srs=srs,
                        model=args.llm_model,
                    )
                except Exception as exc:
                    stats.skipped_llm_guides += 1
                    stats.warnings.append(f"{guide_code}: LLM failed: {exc}")
                    continue

                stats.llm_guides += 1
                stats.feature_candidates += len(llm_features)
                stats.sr_candidates += len(llm_srs)
                stats.visual_triggers += len(llm_triggers)
                if not args.dry_run:
                    upsert_feature_candidates(cur, llm_features)
                    upsert_sr_candidates(cur, llm_srs, apply_asserted=False)
                    upsert_visual_triggers(cur, llm_triggers)
                    conn.commit()
                print(f"  LLM {guide_idx}/{len(guide_codes)} {guide_code}: "
                      f"features={len(llm_features)} sr={len(llm_srs)} triggers={len(llm_triggers)}")

        if not args.dry_run:
            conn.commit()
    finally:
        conn.close()

    print("=== Ontology Enrichment Summary ===")
    print(f"  entities: {stats.entities}")
    print(f"  feature candidates: {stats.feature_candidates}")
    print(f"  SR link candidates: {stats.sr_candidates}")
    print(f"  visual triggers: {stats.visual_triggers}")
    print(f"  asserted links inserted: {stats.asserted_links}")
    print(f"  facet updates: {stats.facet_updates}")
    write_report(stats, args.report)


if __name__ == "__main__":
    main()
