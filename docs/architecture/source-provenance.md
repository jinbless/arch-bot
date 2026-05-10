# Source Provenance Architecture

Latest updated: 2026-05-10

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
```

The main ontology stays focused on legal/risk/guide semantics.

## Core Resources

Recommended resource types:

- `SourceDocument`: a raw KOSHA PDF or legal source file.
- `ParsedArtifact`: parsed Guide, CI, entity, or manifest JSON.
- `ParseRun`: a parser or extraction activity.
- `ValidationRun`: a schema, semantic, or SHACL validation activity.
- `ServingArtifact`: an exported runtime artifact such as `guide_domain_profiles.json`.

Map them to W3C terms:

```text
SourceDocument       -> prov:Entity, dcat:Distribution
ParsedArtifact       -> prov:Entity, dcat:Distribution
ParseRun             -> prov:Activity
ValidationRun        -> prov:Activity
ServingArtifact      -> prov:Entity
parser/script/human  -> prov:Agent
```

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
