# Ontology & Data License — Creative Commons Attribution 4.0 International (CC BY 4.0)

SPDX-License-Identifier: `CC-BY-4.0`

The **ontology, vocabularies, and knowledge data** in this repository are licensed
under the **Creative Commons Attribution 4.0 International License (CC BY 4.0)**.

- Human-readable deed: https://creativecommons.org/licenses/by/4.0/
- Full legal code: https://creativecommons.org/licenses/by/4.0/legalcode

## Scope — what this license covers

This CC BY 4.0 license applies to the ontology/knowledge artifacts, including (non-exhaustive):

- `ontology-team/06-reasoning/ontology/**` — TBox, ABox, SWRL/SHACL rules, axioms,
  inferred-relation TTLs (`kosha-inferred-relations.ttl`, `kosha-coapplicable-chapter.ttl`,
  `kosha-dependson-hazard.ttl`), the SKOS code scheme (`kosha-codes-skos.ttl`),
  and ontology metadata (`kosha-ontology-metadata.ttl`).
- `shared/reference/canonical-code-vocabulary.json` — the canonical code vocabulary (SoT).
- `data-team/01-parsing/kosha-guides/parsed/**` — parsed KOSHA Guide JSON.

The **source code** (Python, JS/TS, SQL, Makefile, build/serving tooling) is licensed
separately under the **Apache License 2.0** — see [`LICENSE`](LICENSE).

## Attribution

When you use, share, or adapt these ontology/data artifacts, you must give appropriate
credit, provide a link to this license, and indicate if changes were made. A suggested
citation is provided in [`CITATION.cff`](CITATION.cff). Example attribution:

> "KOSHA OHS Ontology" (v2.0.0), licensed under CC BY 4.0.
> Source: https://github.com/jinbless/arch-bot

## Upstream sources

The ontology is derived from public Korean occupational-safety regulations
(산업안전보건기준에 관한 규칙 등, via the national legal information service law.go.kr)
and KOSHA technical guides. Those upstream legal texts are public-domain government works;
this license covers the **structured ontology representation and derived knowledge**, not
the underlying statutory text itself.
