# Linked Repositories

Latest updated: 2026-05-10

This repository coordinates several child repositories without vendoring their contents. Physical monorepo import has not happened yet.

Project-owned repositories are pushed before root documentation is pushed. External dependencies are recorded but not pushed by this project.

## koshaontology

- URL: <https://github.com/jinbless/koshaontology>
- Role: ontology schema, ontology instances, extraction pipeline documents, SHE pattern data, OWL/TTL export and validation scripts
- Branch: `main`
- Latest pushed baseline: `60d025ee873e071faf9c90cc0b1a89b05c4812bd`
- Push status: pushed and verified against `origin/main` on 2026-05-10
- Current purpose: Pipe-A/B/C source of truth for SR, SHE, Guide/WorkProcess extraction, manual Guide usage profiles, and ontology enrichment artifacts

## OHS

- URL: <https://github.com/jinbless/OHS>
- Role: backend/frontend service, SHE matcher, hazard normalization, penalty path response, synthetic evaluation scripts
- Branch: `main`
- Latest pushed baseline: `7eed7280e1ece9fa7bb32beb182017f5cfa96f5a`
- Push status: pushed and verified against `origin/main` on 2026-05-10
- Local doc: `OHS/README.md`
- Current purpose: OHS runtime, frontend, serving artifacts, Guide recommendation evaluator, actual/synthetic replay scripts

## legalize-kr

- URL: <https://github.com/legalize-kr/legalize-kr>
- Role: legal source dependency
- Branch: `main`
- Upstream baseline observed: `732764e9e8e116bbc40eb5278207e3a08b31297e`
- Push status: excluded from project push targets because this repository is not project-owned
- Current purpose: external legal source corpus consumed by `koshaontology/pipe-A`
- Important: do not push from this workspace unless explicitly acting as an authorized maintainer of `legalize-kr`

## arch-bot

- URL: <https://github.com/jinbless/arch-bot>
- Role: top-level design docs, current architecture, evaluation summaries, synthetic testsets, coordination notes
- Branch: `main`
- Latest pushed baseline: to be recorded after this documentation commit is pushed
- Start document: `NEXT_SESSION_INSTRUCTIONS.md`
- Current purpose: root main article, monorepo transition plan, data governance, synthetic observations, selected accepted report links

## Local Directory Layout

```text
C:\project\arch-bot
├─ OHS/             project-owned child git repository, ignored by root for now
├─ koshaontology/   project-owned child git repository, ignored by root for now
├─ legalize-kr/     external child git repository, ignored by root for now
├─ kosha-guides/    large source/parsed corpus, selective tracking target for future monorepo phase
├─ pictures-json/   synthetic observation testsets and selected aggregate reports
├─ docs/            root architecture/status/workplan indexes
└─ *.md             root governance and design documents
```

## Future Import Rule

If physical monorepo import is later approved, use snapshot import by default. Preserve historical traceability by recording the imported child commit SHA here instead of rewriting child repository history into root.
