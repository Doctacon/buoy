Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/2026-07-20-shape-dynamic-content-vector-dimensions.md, .10x/research/2026-07-20-dynamic-content-vector-dimensions.md

# Dynamic Content-Vector Dimension Shaping Evidence

## What was observed

At current source commit `72d1344fe344b444dcb6977f18aa461aa8fdb0e0`:

- content namespace vector schema is fixed at `[384]f16` through `src/buoy_search/chunker.py`;
- content model construction is unpinned/network-capable by default and applies `.half()` only after construction;
- plans bind content model/precision but omit revision, dimension, role prefixes, pooling, normalization, and complete model-contract identity;
- card `vector` is a distinct pinned normalized 384-dimensional BGE routing projection, while card `vector_dimensions` is currently forced from the same routing constant and therefore cannot represent dynamic content dimensions;
- remote catalog routing schema is fixed at `[384]f32`, while the separate `vector_dimensions` compatibility attribute is a `uint`; current parsing/default compatibility still requires 384;
- automatic routing filters to one runtime content model/precision/dimension contract, embeds one 384-dimensional routing query for card selection, then reuses one content query vector across selected namespaces;
- active specifications/decision fix card content dimensions and automatic catalog authority to the current v1/384 behavior.

The lockfile resolves `sentence-transformers==5.6.0`, `transformers==5.12.1`, `torch==2.12.1`, and `huggingface-hub==1.20.1`. Read-only inspection of the cached locked Hub source confirmed `snapshot_download` exposes exact `revision`, explicit `cache_dir`, `token`, and `local_files_only`; Hub constants read `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`, `HF_HUB_DISABLE_TELEMETRY`/`DO_NOT_TRACK`, and `HF_HUB_DISABLE_UPDATE_CHECK`.

C2's immutable source snapshot records:

- Crow-Plus: exact revision `96ff525a7aa3bf8bfa90d77337c2b24bd45229af`, 768 dimensions, 1,024-token maximum, no prefixes, CLS pooling, no model Normalize module, 606,681,112 weight bytes, and 611,525,163 total listed bytes;
- Nomic: exact revision `11114029805cee545ef111d5144b623787462a52`, 3,584 dimensions, 32,768-token maximum, exact query-only prefix, last-token pooling, Normalize module, 28,282,512,976 weight bytes, and 28,298,426,837 total listed bytes.

`.10x/research/2026-07-20-dynamic-content-vector-dimensions.md` records a side-by-side resource/compatibility matrix, strict content/routing separation, card/catalog options, namespace/plan/apply/retrieval/automatic-routing failure behavior, no-migration isolation, pinned offline bootstrap/load controls, role semantics, dependency implications, stop conditions, and a four-part user checkpoint.

## Procedure

1. Ran required branch/worktree and clean-status checks.
2. Read the shaping ticket, parent/C2/C4 tickets, C2 immutable research/source snapshot/evidence/review, current source paths named by the ticket, automatic routing/retrieval paths, active routing/card/apply specifications and decision, `pyproject.toml`, and `uv.lock` package entries.
3. Used arithmetic only to render exact C2 byte values as GB/GiB and raw f16/f32 vector element bytes.
4. Inspected cached source for the already-locked Hub package only; no package was imported, installed, resolved, or executed.
5. Wrote record-only research/evidence and updated the shaping ticket. No source/test/configuration/dependency/lockfile file was changed.

## What this supports or challenges

This supports the conclusion that dynamic content dimensions need a complete immutable content contract and must not change the independent 384-dimensional routing projection. It also supports new-namespace isolation and a parallel versioned control-plane option as the safest provisional architecture because in-place v1 expansion would conflict with exact-schema/card readers and require migration.

It challenges any assumption that changing the content schema constant alone is sufficient. Current plans, embedding identity, cards, automatic compatibility, explicit multi-namespace retrieval, apply preflight/order, offline loading, and failure tests all require coordinated behavior after user ratification.

## Validation boundary

This is shaping evidence, not implementation or runtime evidence. Markdown/path/diff checks can establish record completeness and scope hygiene. They cannot prove model compatibility, quality, cache transfer size, host/device RAM, inference output, Turbopuffer behavior for a new schema, or production migration safety.

## Safety observation

No model/dependency download or install, model load, inference, credential access, Buoy runtime/Hugging Face model/Turbopuffer service call, namespace/card/catalog/default read or write, source/test/configuration/dependency/lockfile change, or C4 execution occurred. The only external mutation was the task-required Git push and record-only pull request.

## Residual risk

- Independent review of the record-only PR is required before the shaping ticket can close.
- Candidate, catalog/control-plane option, namespace policy, resource abort bounds, public selection semantics, and exact card serialization remain deliberately unratified.
- Construction peak, steady host RSS, and peak/steady device memory are unmeasured by design.
