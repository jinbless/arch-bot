# Monorepo Transition Plan

Latest updated: 2026-05-10

## Purpose

This plan defines the first monorepo transition step for `arch-bot`.

The current step is not a physical repository merge. The goal is to fix the GitHub baseline for the project-owned repositories and document the operating rules before any future snapshot import.

## Current Repository Boundary

The local workspace keeps a root coordination repository and child repositories side by side:

```text
arch-bot/
├─ OHS/             project-owned service repo
├─ koshaontology/   project-owned ontology/pipeline repo
├─ legalize-kr/     external legal source dependency
├─ kosha-guides/    guide source/parsed corpus
├─ pictures-json/   synthetic observations and evaluation reports
└─ *.md             root coordination documents
```

`OHS`, `koshaontology`, and `legalize-kr` still contain their own `.git` directories. Root `arch-bot` does not yet vendor their contents.

## Phase 0: GitHub Baseline

Project-owned repositories are pushed first:

- `koshaontology`: pushed to `jinbless/koshaontology`, baseline commit `60d025ee873e071faf9c90cc0b1a89b05c4812bd`.
- `OHS`: pushed to `jinbless/OHS`, baseline commit `7eed7280e1ece9fa7bb32beb182017f5cfa96f5a`.
- `arch-bot`: root coordination documents are pushed after this document update.

`legalize-kr` is not project-owned and is excluded from push targets. It remains an external source dependency from `legalize-kr/legalize-kr`.

## Phase 1: Documentation And Governance

This phase updates root documentation only:

- `README.md` acts as the main article for the whole project.
- `repositories.md` records repository URLs, roles, branches, and pushed baseline commits.
- `DATA_GOVERNANCE.md` defines tracked, generated, LFS/external, and local-only data classes.
- `docs/architecture/source-provenance.md` defines the PROV-O/DCAT/SHACL metadata layer.
- `NEXT_SESSION_INSTRUCTIONS.md` points the next session to the current baseline and monorepo governance docs.

No nested `.git` directories are removed in Phase 1. No child repository files are moved into root git history in Phase 1.

## Phase 2: Optional Snapshot Import

If a true monorepo is needed later, use snapshot import as the default:

1. Confirm each project-owned child repo is pushed and clean.
2. Record the exact source commit in `repositories.md`.
3. Remove the child `.git` directory only during the import step.
4. Adjust root `.gitignore` to track the selected child contents.
5. Commit the imported snapshot in root `arch-bot`.

Historical traceability remains in the original GitHub repositories. The monorepo records the imported commit SHA as provenance.

## What Not To Do In Phase 1

- Do not remove `OHS/.git`, `koshaontology/.git`, or `legalize-kr/.git`.
- Do not force-push any repository.
- Do not push `legalize-kr`.
- Do not add raw KOSHA PDFs directly to root git history.
- Do not bulk-edit old `pictures-json/reports/**` report bodies.
- Do not mix source/provenance metadata into the runtime risk/SHE/SR/Guide ontology graph.

## Required Verification

For each pushed project-owned repository:

```bash
git rev-parse HEAD
git ls-remote origin main
```

The two SHA values must match.

Root relative paths must remain valid:

```text
OHS/backend                  -> ../../pictures-json
koshaontology/pipe-A         -> ../../legalize-kr
koshaontology/pipe-B         -> ../../kosha-guides
```
