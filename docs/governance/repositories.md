# Linked Repositories

Latest updated: 2026-05-10

Root `arch-bot/main` is the monorepo. The project-owned child repositories were pushed first, then imported into root by snapshot and merged to `main`.

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

`legalize-kr` is consumed by `data-team/02-extraction/pipe-A` through the local sibling path. Do not push it from this project workspace unless separately authorized as an upstream maintainer.

## Root Repository

- URL: <https://github.com/jinbless/arch-bot>
- Main baseline before import: `1565a9d14e76b7e3ceb6753354621f5d043c92de`
- Active branch: `main`
- Snapshot import doc-alignment commit: `a6552e33f944fd34a4f6eb8737b92366454c778c`
- Historical import branch used: `codex/monorepo-snapshot-import`
- Snapshot import commit: `e9dcde3589cc4049973138c50550ddc889caf3a5`
- Role: monorepo root, governance docs, imported OHS/koshaontology source, selected Guide corpus, synthetic inputs, lightweight manifests

## Data Directories

| Directory | Root policy |
|---|---|
| `data-team/01-parsing/kosha-guides/parsed/**` | tracked, 1,038 parsed Guide JSON files |
| `data-team/01-parsing/kosha-guides/manifest/**` | tracked, parsed Guide provenance manifest |
| `data-team/01-parsing/kosha-guides/{A,B,C,D,E}/**` | ignored raw PDF/source corpus |
| `data-team/05-enrichment/eval-data/synthetic_observations_v*.jsonl` | tracked synthetic evaluation inputs |
| `data-team/05-enrichment/eval-data/reports/**` | ignored local/external report bodies |
| `data-team/05-enrichment/eval-data/reports-manifest.json` | tracked report provenance and accepted baseline summary |

## Local Directory Layout

```text
Windows: C:\project\arch-bot
WSL:     /mnt/c/project/arch-bot
├─ OHS/             imported service source
├─ koshaontology/   imported ontology/pipeline source
├─ legalize-kr/     external source dependency, ignored by root
├─ data-team/01-parsing/kosha-guides/    parsed corpus and manifest tracked; raw PDFs ignored
├─ data-team/05-enrichment/eval-data/   synthetic inputs tracked; report bodies external
├─ docs/            architecture/status/workplan documents
└─ *.md             root governance and design documents
```

## Operating Rule

Normal project changes should now be committed and pushed through root `arch-bot/main`. Only use the original child repositories to inspect pre-import history or to recover a pre-import baseline.
