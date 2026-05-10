# Monorepo Transition Plan

Latest updated: 2026-05-10

## Purpose

This document records the completed snapshot-import transition from the previous multi-repo workspace to root `arch-bot/main` monorepo operations.

This is a snapshot import, not a history rewrite. The original child GitHub repositories preserve historical commits, and root `arch-bot` records their imported baseline SHAs.

## Current Repository Boundary

Current root layout:

```text
arch-bot/
├─ OHS/             imported service source
├─ koshaontology/   imported ontology/pipeline source
├─ legalize-kr/     external local dependency, ignored by root git
├─ kosha-guides/    parsed Guide corpus and manifests only
├─ pictures-json/   synthetic inputs and lightweight report manifests
├─ docs/            root architecture/status/workplan documents
└─ *.md             root governance and design documents
```

`OHS/.git` and `koshaontology/.git` were moved to the external backup directory during import. `legalize-kr/.git` remains in place because that repository is external and not project-owned.

## Baseline Commits

Project-owned repositories were pushed before import:

| Directory | Source repo | Imported baseline |
|---|---|---|
| `koshaontology/` | `jinbless/koshaontology` | `60d025ee873e071faf9c90cc0b1a89b05c4812bd` |
| `OHS/` | `jinbless/OHS` | `7eed7280e1ece9fa7bb32beb182017f5cfa96f5a` |
| root `arch-bot/` | `jinbless/arch-bot` | `1565a9d14e76b7e3ceb6753354621f5d043c92de` |

External dependency:

| Directory | Upstream repo | Local policy |
|---|---|---|
| `legalize-kr/` | `legalize-kr/legalize-kr` | excluded from import and push |

## Snapshot Import Rules

- Import only files that were tracked by the child repositories at the baseline commit.
- Do not bulk-add child directories, because untracked parser scratch/log files may exist.
- Keep raw KOSHA PDFs, old report bodies, caches, `.env`, `.venv`, `node_modules`, and runtime logs out of root history.
- Track `kosha-guides/parsed/**` and `kosha-guides/manifest/**`.
- Track `pictures-json/reports-manifest.json` and `docs/status/evaluation-baseline.md`, not historical `pictures-json/reports/**` bodies.
- Keep `legalize-kr/` ignored and path-compatible as an external sibling dependency.

## Import Result

The import was prepared on the historical working branch:

```text
codex/monorepo-snapshot-import
```

It was then fast-forward merged and pushed to root `main`. `main` is now the active monorepo branch; use `git rev-parse HEAD` for the moving current commit.

Snapshot import doc-alignment commit:

```text
a6552e33f944fd34a4f6eb8737b92366454c778c
```

Initial snapshot import commit inside that history:

```text
e9dcde3589cc4049973138c50550ddc889caf3a5
```

## Required Verification

Git checks:

```bash
git rev-parse --abbrev-ref HEAD
git ls-files OHS | wc -l
git ls-files koshaontology | wc -l
git ls-files kosha-guides/parsed | wc -l
git ls-files | rg '\\.env|node_modules|\\.venv|\\.dev-logs|pictures-json/reports/|kosha-guides/.+\\.pdf'
```

Expected counts:

```text
OHS tracked files: 161
koshaontology tracked files: 2268
kosha-guides parsed files: 1038
```

Path checks:

```text
OHS/backend                  -> ../../pictures-json
koshaontology/pipe-A         -> ../../legalize-kr
koshaontology/pipe-B         -> ../../kosha-guides/parsed
```

Build/checks:

```text
OHS backend Python compile: OK
OHS frontend npm run build: OK
koshaontology Python compile: OK
JSON manifests parse: OK
```

## Rollback

The pre-merge rollback path was to restore `OHS/.git` and `koshaontology/.git` from the external backup directory. That path is now historical because the import has already been merged to `main`.

Current rollback is a normal Git revert/reset decision in `arch-bot`; child repository histories remain intact on GitHub.
