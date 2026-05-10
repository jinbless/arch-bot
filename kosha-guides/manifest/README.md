# KOSHA Guides Manifest

This directory contains lightweight provenance manifests for the parsed KOSHA Guide corpus.

Tracked policy:

- `guides-manifest.json` records the 1,038 parsed Guide JSON files currently imported into the root monorepo branch.
- Raw KOSHA PDFs remain external or LFS candidates and are referenced by path only.
- The manifest is the operational source for future PROV-O/DCAT/SHACL provenance export.

Do not put parser scratch files or raw PDF bytes in this directory.
