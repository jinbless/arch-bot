"""온톨로지 assembly SSOT — '무엇이 온톨로지인가'의 단일 정본.

이 파일이 유일한 hand-edit 지점이다. gen_manifest.py가 이를 읽어
assembly-manifest.json(생성물·수동편집 금지)을 emit하고, 6개 소비자가 그 JSON의
profile별 ordered file list를 로드한다. (기존 gen_canonical_code_shape.py 패턴.)

설계 원칙:
- RDF 그래프 병합은 순서 무관 → profile은 '집합'이 본질. ENTRIES의 전역 순서(base→
  vocab→disjoint→TBox patch→rules→ABox→shapes)대로 emit하되, 검증은 그래프 동치(triple
  set)로 한다(ordered-list 일치가 아니라).
- 'archive' = 어떤 소비자도 안 읽지만 dir에 존재(silent orphan 방지용 등록). git 보존.
- 'keep-loose' = 현재 active profile은 없으나 hand-authored TBox SoT(삭제 금지) 또는
  자체 생성기 보유. archive 아님 — dir에 정식 잔류, 필요 시 profile 편입.

profile 코드:
  SRV serving(Fuseki) / CON consistency(Pellet) / MAT shacl-materialize(run_shacl_rules)
  FAC facet-explorer(serve_facets) / INF inference-legacy(run_inference) / GHR guide-hazard-rules
"""
from __future__ import annotations

# 모든 cashtoss 소비자 profile (순서 = 표시용)
PROFILES = ["serving", "consistency", "shacl-materialize",
            "facet-explorer", "inference-legacy", "guide-hazard-rules"]
_CODE = {"SRV": "serving", "CON": "consistency", "MAT": "shacl-materialize",
         "FAC": "facet-explorer", "INF": "inference-legacy", "GHR": "guide-hazard-rules"}

# (id, file, role, layer, profile-codes set, format, note)
# format: xml=.owl(RDF/XML), turtle=나머지.  profiles 비고: 2026-05-30 현재 6 로더 실측.
_E = [
    # ── BASE TBox ─────────────────────────────────────────────────────────────
    ("base-v2-owl", "kosha-ontology-v2.owl", "tbox-base", "L3-reasoning",
     {"SRV", "CON", "MAT", "INF"}, "xml", "v2 base (BFO+LKIF, sosa). SRV/CON/MAT + INF(Phase1.5 v1→v2)."),
    ("base-v2-ttl", "kosha-ontology-v2.formatted.ttl", "tbox-base", "L3-reasoning",
     {"FAC"}, "turtle", "v2 base Turtle. facet-explorer base (Phase1.5 v1→v2 정정)."),
    ("arc-v1-owl", "kosha-ontology.owl", "archive", "-",
     set(), "xml", "v1 raw base(obsolete). INF가 v2로 이전됨 → archive."),
    ("arc-v1-formatted", "kosha-ontology.formatted.ttl", "archive", "-",
     set(), "turtle", "v1 formatted base(obsolete). FAC가 v2로 이전됨 → archive."),
    # ── FACET vocabulary (KOSHA-22 라벨/정본 코드) ───────────────────────────
    ("v4-kosha22-vocab", "kosha-ontology-v4-kosha22-vocab-patch.ttl", "tbox-patch", "L2-normalizer",
     {"FAC"}, "turtle", "KOSHA-22 accident/agent/context 어휘 라벨."),
    # ── TBox patches: v3 ─────────────────────────────────────────────────────
    ("facet-taxonomy", "kosha-facet-taxonomy.ttl", "tbox-taxonomy", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle",
     "3축 facet taxonomy: canonical owl:Class punning + fine⊑canonical(vocab rollup SSOT) + ctx 계층(forklift 변별). 생성: scripts/gen_facet_taxonomy.py. 구 v3-subclass-patch 대체(P3)."),
    ("v3-incompat", "kosha-ontology-v3-incompat-patch.ttl", "tbox-patch", "L3-reasoning",
     set(), "turtle", "G.1 core:Incompatibility TBox SoT. orphan-but-keep(PG guide_domain_incompatibilities 원천)."),
    ("v3-guide-profile", "kosha-ontology-v3-guide-profile-patch.ttl", "tbox-patch", "L3-reasoning",
     set(), "turtle", "G.2 guide:GuideUsageProfile 유일 정의. orphan-but-keep."),
    ("v3-penalty-relations", "kosha-ontology-v3-penalty-relations-patch.ttl", "tbox-patch", "L3-reasoning",
     set(), "turtle", "G.3 penalty relation props TBox SoT. orphan-but-keep."),
    ("v3-restructure", "kosha-ontology-v3-restructure-patch.ttl", "tbox-patch", "L3-reasoning",
     set(), "turtle", "OntoClean 재구조화. ⚠️ 현재 파싱실패(<> 누락). Phase2에서 수리/판정."),
    # ── TBox patches: v4 chain (Axiom-100% Phase A-J) ────────────────────────
    ("v4-deps", "kosha-ontology-v4-deps-patch.ttl", "tbox-patch", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "Phase A: core:dependsOn."),
    ("v4-alethic", "kosha-ontology-v4-alethic-patch.ttl", "tbox-patch", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "Phase B: alethic chain."),
    ("v4-bridge", "kosha-ontology-v4-bridge-patch.ttl", "tbox-patch", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "Phase C: bridge:*."),
    ("v4-deontic", "kosha-ontology-v4-deontic-patch.ttl", "tbox-patch", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "Phase D: deontic chain."),
    ("v4-violation", "kosha-ontology-v4-violation-patch.ttl", "tbox-patch", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "Phase E: violation chain (actor:Worker)."),
    ("v4-penalty-extra", "kosha-ontology-v4-penalty-extra-patch.ttl", "tbox-patch", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "Phase F: penalty chain."),
    ("v4-restrictions", "kosha-ontology-v4-restrictions-patch.ttl", "tbox-patch", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "Phase G: owl:Restriction."),
    ("v4-hazard-direct", "kosha-ontology-v4-hazard-direct-patch.ttl", "tbox-patch", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "Phase H: NaturalLanguageHazardCategory."),
    ("v4-asymmetric", "kosha-ontology-v4-asymmetric-patch.ttl", "tbox-patch", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "Phase J: law:modifiesAsymmetric."),
    # ── TBox patches: Three-Worlds facet (serve_facets 전용) ──────────────────
    ("v4-guide-hazard", "kosha-ontology-v4-guide-hazard-patch.ttl", "tbox-patch", "L3-reasoning",
     {"FAC"}, "turtle", "guide:addressesHazard 등 Three-Worlds TBox."),
    ("v4-canonical-ci", "kosha-ontology-v4-canonical-ci-patch.ttl", "tbox-patch", "L3-reasoning",
     {"FAC"}, "turtle", "CanonicalChecklistItem/realizesControl TBox."),
    # ── Axioms: disjoint / restrictions ──────────────────────────────────────
    ("disjoint-axioms", "kosha-disjoint-axioms.ttl", "axioms-disjoint", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "industry disjoint. 생성: build_disjoint_axioms.py."),
    ("accident22-disjoint", "kosha-accident22-disjoint.ttl", "axioms-disjoint", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "KOSHA-22 사고유형 disjoint."),
    ("vetted-disjoint-shapes", "kosha-vetted-disjoint-shapes.ttl", "shapes-validation", "L3-reasoning",
     {"CON"}, "turtle", "vetted disjoint SHACL(sh:Info)."),
    ("kb-candidates", "kb-candidates.ttl", "candidates", "L4-learning",
     {"SRV", "CON"}, "turtle", "F.3.2 candidate axiom(sh:Info). 생성: compile_kb_to_ttl.py."),
    # ── Rules: SWRL ──────────────────────────────────────────────────────────
    ("swrl-r1-r3", "kosha-rules-r1-r3-swrl.ttl", "rules-swrl", "L3-reasoning",
     {"SRV", "CON"}, "turtle", "R-1/R-3 (Pellet native)."),
    ("swrl-r2-r4", "kosha-rules-r2-r4-swrl.ttl", "rules-swrl", "L3-reasoning",
     {"SRV", "CON"}, "turtle", "R-2/R-4."),
    ("swrl-r9-r13", "kosha-rules-r9-r13-swrl.ttl", "rules-swrl", "L3-reasoning",
     {"SRV", "CON"}, "turtle", "R-10~R-13 (R-9 skip)."),
    ("swrl-r14-r18", "kosha-rules-r14-r18-swrl.ttl", "rules-swrl", "L3-reasoning",
     {"CON"}, "turtle", "R-14~R-18. Fuseki 제외(Pellet NEXPTIME)→SHACL twin. rule_ids R14-R18."),
    ("swrl-r19-r23", "kosha-rules-r19-r23-swrl.ttl", "rules-swrl", "L3-reasoning",
     {"CON"}, "turtle", "R-19~R-23. SHACL twin 존재. rule_ids R19-R23."),
    ("swrl-r24-r26", "kosha-rules-r24-r26-swrl.ttl", "rules-swrl", "L3-reasoning",
     {"CON"}, "turtle", "R-24~R-26. SHACL twin 존재. rule_ids R24-R26."),
    ("swrl-r28-r30", "kosha-rules-r28-r30-swrl.ttl", "rules-swrl", "L3-reasoning",
     {"CON"}, "turtle", "R-28~R-30. SHACL twin 존재. rule_ids R28-R30."),
    # ── Rules: SHACL ─────────────────────────────────────────────────────────
    ("shacl-r14-r30", "kosha-rules-r14-r30-shacl-construct.ttl", "rules-shacl", "L3-reasoning",
     {"CON", "MAT"}, "turtle", "R-14~R-30 SHACL SPARQLRule (SWRL twin의 운영 경로). rule_ids R14-R30."),
    ("shacl-r27-exempted", "kosha-r27-shacl-exempted.ttl", "rules-shacl", "L3-reasoning",
     {"SRV", "CON"}, "turtle", "R-27 negation-as-failure(SHACL 전용)."),
    ("shacl-guide-hazard", "kosha-rules-guide-hazard-shacl.ttl", "rules-shacl", "L3-reasoning",
     {"GHR"}, "turtle", "Three-Worlds facet 유도 6 CONSTRUCT (matching-critical)."),
    ("shacl-k-general", "kosha-rules-k-general-shacl.ttl", "rules-shacl", "L3-reasoning",
     set(), "turtle", "SR 일반화(dependsOn/coApplicable). orphan-but-keep(on-demand materialize)."),
    # ── ABox: generated / derived / fixture ──────────────────────────────────
    ("abox-instances", "kosha-instances.ttl", "abox-generated", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC", "INF", "GHR"}, "turtle", "SR/CI/Guide/law/penalty ABox. 생성: export_owl.py(PG)."),
    ("abox-canonical-ci", "kosha-instances-canonical-ci.ttl", "abox-derived", "L3-reasoning",
     {"FAC", "GHR"}, "turtle", "canonical CI facet ABox. 생성: export_canonical_ci_abox.py."),
    ("abox-guide-hazard-derived", "kosha-instances-ci-guide-hazard-derived.ttl", "abox-derived", "L3-reasoning",
     {"FAC"}, "turtle", "Guide 유도 facet. 생성: run_guide_hazard_rules.py(gitignored)."),
    ("abox-hazard-direct", "kosha-instances-hazard-direct.ttl", "abox-generated", "L3-reasoning",
     {"SRV", "CON", "MAT", "FAC"}, "turtle", "Phase H NLH alias ABox."),
    ("abox-8photo", "kosha-instances-production-8photo.ttl", "abox-fixture", "L3-reasoning",
     {"FAC"}, "turtle", "8-photo eval ABox(VisualObservation)."),
    ("abox-demo-chain", "kosha-instances-demo-chain.ttl", "abox-fixture", "L3-reasoning",
     set(), "turtle", "데모/rule-parity fixture. keep(Phase2 parity harness용)."),
    # ── Serving shapes ───────────────────────────────────────────────────────
    ("shapes-serving-v3", "serving-validation-shapes-v3.ttl", "shapes-validation", "serving",
     {"SRV", "CON"}, "turtle", "serving SHACL shapes(현행 v3). 생성: export_serving_snapshot.py."),
    ("shape-canonical-code", "kosha-canonical-code-shape.ttl", "shapes-canonical", "L3-reasoning",
     set(), "turtle", "canonical code IRI SHACL. orphan-but-keep(자체 생성기 gen_canonical_code_shape.py)."),
    # ── ARCHIVE (어떤 소비자도 안 읽음; silent-orphan 방지 등록, Phase1.6 이동) ──
    ("arc-v3-subclass", "kosha-ontology-v3-subclass-patch.ttl", "archive", "-",
     set(), "turtle", "구 catalog sub 기반 subclass-patch(haz/agent, casing 단절). facet-taxonomy로 대체 → archive(P3)."),
    ("arc-v1-annotated", "kosha-ontology.annotated.ttl", "archive", "-",
     set(), "turtle", "v1 annotated snapshot(obsolete)."),
    ("arc-legacy-swrl1", "kosha-rules.swrl", "archive", "-",
     set(), "turtle", "legacy SWRL monolith(미사용)."),
    ("arc-legacy-swrl2", "kosha-rules-v2.swrl", "archive", "-",
     set(), "turtle", "legacy SWRL monolith v2(미사용)."),
    ("arc-old-inversion", "kosha-instances-guide-hazard.ttl", "archive", "-",
     set(), "turtle", "구 PG-inversion ABox(폐기 예정)."),
    ("arc-serving-policy", "serving-policy.ttl", "archive", "-",
     set(), "turtle", "serving policy 산출물(온톨로지 입력 아님)."),
    ("arc-shapes-v1", "serving-validation-shapes.ttl", "archive", "-",
     set(), "turtle", "serving shapes v1(superseded by v3)."),
    ("arc-shapes-v2", "serving-validation-shapes-v2.ttl", "archive", "-",
     set(), "turtle", "serving shapes v2(superseded by v3)."),
    ("arc-snap-1", "serving-snapshot-ci_broad_sr_guard4.ttl", "archive", "-", set(), "turtle", "serving snapshot 변형(PG materialize 산출)."),
    ("arc-snap-2", "serving-snapshot-ci_candidate_promotion_v1.ttl", "archive", "-", set(), "turtle", "serving snapshot 변형."),
    ("arc-snap-3", "serving-snapshot-ci_cross_guide_broad_only_guard1.ttl", "archive", "-", set(), "turtle", "serving snapshot 변형(CURRENT_POLICY 표시였음)."),
    ("arc-snap-4", "serving-snapshot-ci_preferred_guide_ci1.ttl", "archive", "-", set(), "turtle", "serving snapshot 변형."),
    ("arc-snap-5", "serving-snapshot-ci_unrelated_action_filter1.ttl", "archive", "-", set(), "turtle", "serving snapshot 변형."),
    ("arc-snap-6", "serving-snapshot-context_safe_gate1.ttl", "archive", "-", set(), "turtle", "serving snapshot 변형."),
    ("arc-snap-7", "serving-snapshot-corpus_gap_guard1.ttl", "archive", "-", set(), "turtle", "serving snapshot 변형."),
    ("arc-snap-8", "serving-snapshot-no_forced_hotwork_gate1.ttl", "archive", "-", set(), "turtle", "serving snapshot 변형."),
]

# 외부에서 쓰는 정규 구조
ENTRIES = [
    {"id": e[0], "file": e[1], "role": e[2], "layer": e[3],
     "profiles": sorted(_CODE[c] for c in e[4]), "format": e[5], "note": e[6]}
    for e in _E
]


def by_profile(profile: str) -> list[dict]:
    """해당 profile에 속한 엔트리를 ENTRIES 전역 순서대로."""
    return [e for e in ENTRIES if profile in e["profiles"]]


def archive_files() -> list[str]:
    return [e["file"] for e in ENTRIES if e["role"] == "archive"]
