# Linked Repositories

Latest updated: 2026-05-10

Root `arch-bot` is the monorepo target. The project-owned child repositories were pushed first, then imported into root by snapshot on branch `codex/monorepo-snapshot-import`.

`legalize-kr` is external and remains outside root git.

## Imported Project Sources

| Directory | Original repo | Baseline branch | Imported baseline | Root policy |
|---|---|---|---|---|
| `koshaontology/` | <https://github.com/jinbless/koshaontology> | `main` | `60d025ee873e071faf9c90cc0b1a89b05c4812bd` | tracked by root snapshot |
| `OHS/` | <https://github.com/jinbless/OHS> | `main` | `7eed7280e1ece9fa7bb32beb182017f5cfa96f5a` | tracked by root snapshot |

The original repositories remain the history archive for work before the snapshot import.

## External Dependency

| Directory | Upstream repo | Baseline observed | Root policy |
|---|---|---|---|
| `legalize-kr/` | <https://github.com/legalize-kr/legalize-kr> | `732764e9e8e116bbc40eb5278207e3a08b31297e` | ignored; do not push or import |

`legalize-kr` is consumed by `koshaontology/pipe-A` through the local sibling path. Do not push it from this project workspace unless separately authorized as an upstream maintainer.

## Root Repository

- URL: <https://github.com/jinbless/arch-bot>
- Main baseline before import: `1565a9d14e76b7e3ceb6753354621f5d043c92de`
- Import branch: `codex/monorepo-snapshot-import`
- Snapshot import commit: `e9dcde3589cc4049973138c50550ddc889caf3a5`
- Role: monorepo root, governance docs, imported OHS/koshaontology source, selected Guide corpus, synthetic inputs, lightweight manifests

## Data Directories

| Directory | Root policy |
|---|---|
| `kosha-guides/parsed/**` | tracked, 1,038 parsed Guide JSON files |
| `kosha-guides/manifest/**` | tracked, parsed Guide provenance manifest |
| `kosha-guides/{A,B,C,D,E}/**` | ignored raw PDF/source corpus |
| `pictures-json/synthetic_observations_v*.jsonl` | tracked synthetic evaluation inputs |
| `pictures-json/reports/**` | ignored local/external report bodies |
| `pictures-json/reports-manifest.json` | tracked report provenance and accepted baseline summary |

## Local Directory Layout

```text
C:\project\arch-bot
├─ OHS/             imported service source
├─ koshaontology/   imported ontology/pipeline source
├─ legalize-kr/     external source dependency, ignored by root
├─ kosha-guides/    parsed corpus and manifest tracked; raw PDFs ignored
├─ pictures-json/   synthetic inputs tracked; report bodies external
├─ docs/            architecture/status/workplan documents
└─ *.md             root governance and design documents
```

## Operating Rule

After the snapshot import branch is merged, normal project changes should be committed and pushed through root `arch-bot`. Only use the original child repositories to inspect pre-import history or to recover a pre-import baseline.
