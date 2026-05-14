# Source Provenance Architecture

Latest updated: 2026-05-14

## Summary

The project adds a source metadata layer beside the domain ontology. This layer explains where a Guide, parsed artifact, candidate, and serving profile came from.

It does not replace the current runtime ontology flow:

```text
risk:RiskFeature
→ she:SituationalHazardPattern
→ sr:SafetyRequirement
→ guide:KoshaGuide / guide:WorkProcess / guide:ChecklistItem
```

Instead, it answers audit questions:

- Which PDF produced this parsed Guide JSON?
- Which parser run produced this CI/entity JSON?
- Which checksum identifies the source PDF?
- Which parsed artifact has a filename or guide-code mismatch?
- Which generated serving artifact is derived from which manual candidate batch?
- Which serving baseline produced the current Guide usage profile and validation snapshot?
- Which validation run found a structural warning or hard violation?

## Standards

Use W3C standards:

- PROV-O for entities, activities, agents, derivation, and generation.
- DCAT for datasets and distributions.
- DCTERMS for identifiers, titles, sources, and modified dates.
- SHACL for validation rules.

## Graph Files

Keep this layer separate from the main domain ontology:

```text
koshaontology/ontology/source-provenance.ttl
koshaontology/ontology/source-catalog.ttl
koshaontology/ontology/source-shapes.ttl
koshaontology/ontology/serving-policy.ttl
koshaontology/ontology/serving-snapshot-corpus_gap_guard1.ttl
koshaontology/ontology/serving-validation-shapes.ttl
```

The main ontology stays focused on legal/risk/guide semantics.

## Core Resources

Recommended resource types:

- `SourceDocument`: a raw KOSHA PDF or legal source file.
- `ParsedArtifact`: parsed Guide, CI, entity, or manifest JSON.
- `ParseRun`: a parser or extraction activity.
- `ValidationRun`: a schema, semantic, or SHACL validation activity.
- `ServingArtifact`: an exported runtime artifact such as `guide_domain_profiles.json`.
- `ServingSnapshot`: a validation-only TTL snapshot generated from serving artifacts.
- `ValidationReport`: hard-violation and warning report generated from SPARQL/SHACL-style checks.

Map them to W3C terms:

```text
SourceDocument       -> prov:Entity, dcat:Distribution
ParsedArtifact       -> prov:Entity, dcat:Distribution
ParseRun             -> prov:Activity
ValidationRun        -> prov:Activity
ServingArtifact      -> prov:Entity
ServingSnapshot      -> prov:Entity
ValidationReport     -> prov:Entity
parser/script/human  -> prov:Agent
```

## Serving Snapshot

The accepted runtime baseline is `corpus_gap_guard1`. Runtime still reads PostgreSQL and OHS JSON artifacts, but the following files are exported for machine validation:

```text
OHS/backend/app/data/guide_domain_profiles.json
OHS/backend/app/data/guide_photo_matchability.v1.json
OHS/backend/app/data/broad_sr_policy.json
OHS/backend/app/data/situation_context_taxonomy.v20.json
OHS/backend/app/data/guide_support_candidates.v20.jsonl
pictures-json/reports/pipeline_quality_v1_v10_corpus_gap_guard1.json
```

The export script writes:

```text
koshaontology/ontology/serving-policy.ttl
koshaontology/ontology/serving-snapshot-corpus_gap_guard1.ttl
koshaontology/ontology/serving-validation-shapes.ttl
```

The validator writes:

```text
koshaontology/ontology/serving-validation-report-corpus_gap_guard1.json
koshaontology/ontology/serving-validation-report-corpus_gap_guard1.md
koshaontology/ontology/serving-validation-report-corpus_gap_guard1.csv
koshaontology/ontology/serving-workprocess-alignment-corpus_gap_guard1.json
koshaontology/ontology/serving-workprocess-alignment-corpus_gap_guard1.md
koshaontology/ontology/serving-workprocess-alignment-corpus_gap_guard1.csv
```

Current validation result:

```text
GuideUsageProfile: 1,038
photo_actionable / conditional / unmatchable: 637 / 36 / 365
broad SRs: 12
evaluation cases: 2,360
hard violations: 0
warnings: 16
```

The core Guide A-Box was regenerated from PostgreSQL on 2026-05-14, bringing `kosha-instances.ttl` to 1,038 Guides, 54,631 ChecklistItems, and 9,316 WorkProcesses. The previous stale base-TTL WorkProcess warnings dropped from 1,220 to 0. Remaining warnings are not runtime blockers; they are the next anomaly queue for role/matchability conflicts, one broad-SR overreach attention case, and repeated evaluation failures by Guide.

## Example: C73

The C73 correction showed why this layer is needed. The source metadata should make this chain explicit:

```text
source PDF C-73-2012
→ parsed guide-C73.json
→ parsed ci-C73.json
→ guide usage profile C-73-2012
→ OHS guide_domain_profiles.json
```

The old C73/CC73 confusion should be detectable as a source/parsed mismatch before it affects Guide recommendation.

## Minimum SHACL Rules

Start with these checks:

- every `guide:KoshaGuide` has one source document reference
- every `ParsedArtifact` has `prov:wasDerivedFrom`
- every source document has a checksum
- every parsed Guide artifact has guide code, short code, and title
- `guideCode`, `shortCode`, and parsed filename agree
- `pdfPath` points to a known source document in the manifest
- C/CC-style short-code collisions are reported as review items

## Runtime Rule

The OHS recommendation score must not use provenance directly. Provenance is for audit, debug, rebuild, and explanation of data lineage.

The serving snapshot follows the same rule. OHS does not query `serving-snapshot-corpus_gap_guard1.ttl` in the request path; the snapshot is regenerated from serving artifacts and reports whenever a new accepted baseline is created.
