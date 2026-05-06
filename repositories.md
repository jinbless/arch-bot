# Linked Repositories

This repository coordinates several child repositories without vendoring their contents.

## koshaontology

- URL: <https://github.com/jinbless/koshaontology>
- Role: ontology schema, ontology instances, extraction pipeline documents, SHE pattern data, OWL/TTL export and validation scripts
- Latest pushed commit during setup: `4cc77bf`

## OHS

- URL: <https://github.com/jinbless/OHS>
- Role: backend/frontend service, SHE matcher, hazard normalization, penalty path response, synthetic evaluation scripts
- Latest pushed commit during setup: `c0737e2`

## legalize-kr

- URL: <https://github.com/legalize-kr/legalize-kr>
- Role: legal source dependency
- Latest checked branch: `main`
- No local changes at setup time

## arch-bot

- URL: <https://github.com/jinbless/arch-bot>
- Role: top-level design docs, current architecture, evaluation summaries, synthetic testsets, coordination notes

## Local Directory Layout

```text
C:\project\arch-bot
├─ OHS/             separate git repository, ignored here
├─ koshaontology/   separate git repository, ignored here
├─ legalize-kr/     separate git repository, ignored here
├─ kosha-guides/    large source corpus, ignored here
├─ pictures-json/   synthetic observation testsets and latest aggregate reports
└─ *.md             current design documents
```
