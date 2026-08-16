Status: recorded
Created: 2026-08-16
Updated: 2026-08-16
Ticket: .10x/tickets/done/2026-08-16-implement-automatic-routing-after-apply.md
Specification: .10x/specs/automatic-routing-after-apply.md
Decision: .10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md

# Automatic Routing after Apply Evidence

## Result

The task branch implements the requested ordinary per-source workflow. A
schema-v3 `buoy plan` deterministically retains up to eight real source
passages in reviewed `delta.duckdb`; a fully successful approved `buoy apply`
embeds and registers the effective passage bank on the source's one routing
card; and an immediately following namespace-free retrieval can select the
source from its content rather than generic URL metadata. Plan/apply never uses
a generative LLM, invents questions, reacquires the source, runs MiniLM,
replays canaries, or recalibrates confidence.

Exact remote catalog schema v3 is a separately reviewed, reader-first account
prerequisite. Turbopuffer exposes no atomic create-schema-only-if-absent
operation, so first and ordinary apply never provision or migrate the catalog.
Missing or older catalog state after content/local-state commit produces
truthful nonzero partial success, no catalog schema/card write, and retains the
exact plan. The emitted `catalog repair-apply --inspect-current` command
re-verifies that plan against the committed plan/apply IDs under the namespace
lock, strongly reads exact-v3 state without model work or writes, retains the
plan, and emits an absence/revision-bound repair. A read failure uses the same
inspection after recovery. Neither command copies source excerpts into terminal
output or shell history.

Manual `routing_examples` remain operator-owned and consume the shared
eight-evidence budget first. A generated passage canonically equal to a manual
example is omitted and the next plan-ordered passage fills the remaining slot.
The remote schema-v3 card retains individual float32 evidence vectors in one
flattened hashed bank. Stage-one routing uses the best base/evidence cosine per
card before choosing twelve unique cards, so a relevant passage is not hidden
by the centroid of deliberately diverse evidence. The existing centroid
remains stored for legacy compatibility.

The active confidence artifact is schema 3. It preserves the exact seven-
namespace certified projection and prior score/margin thresholds. That exact
state retains certified singleton routing; any internally valid catalog drift
is immediately usable in provisional mode and forces descriptor-free fanout up
to three. Malformed artifacts/cards/vector state still fail before content
retrieval. Explicit namespace and exact title/alias authority are unchanged.

## Acceptance evidence

- Plan schema 3 / delta schema 2 add one exact `routing_prototypes` table and a
  bounded descriptor participating in logical and artifact identity. No-change
  plans select from the full desired manifest although unchanged content is
  absent from upserts. Duplicate source-row variants collapse to ordinal zero,
  and verification queries only the at-most-eight linked upserts rather than
  materializing the corpus. Tamper, reorder, dangling-row, stale-row,
  duplicate, and over-limit cases fail verification.
- Source-variant tests cover websites, GitHub repositories, local files, PDFs,
  DuckDB, BigQuery, and Snowflake relations. Selection is model-free,
  Turbopuffer-credential-free, stable by source order and token diversity, and
  capped at eight passages / 512 characters each.
- Apply tests prove one bounded local routing-model batch, manual field/example
  and disabled-state preservation, the combined eight-slot budget, exact
  vector-bank reuse, strong verified create/update, and complete registration
  timing. A missing/old catalog stops before route-model load and catalog write.
- Retained-plan repair tests execute read-only inspection for both an absent
  generated card and an existing manual card, prove zero model/write/cleanup,
  and then execute its exact absence/revision-bound command. Repair revalidates
  state under the namespace lock, recognizes an already-current card after an
  ambiguous create/update without a second write, and fails closed on other
  drift. Text-mode drift failures print the newly observed, opaque bound repair
  command so a non-JSON operator can progress. The repaired card matches
  intended semantic/system authority and current plan/apply lineage. Source
  passages and terminal controls never appear in repair diagnostics, and
  unsafe control-character plan/state paths are rejected.
- Catalog tests prove exact v1/v2/v3 readers, schema-only explicit v3 migration,
  legacy null-bundle normalization, float32/hash/dimension/centroid binding,
  one-card conditional mutation, generic-upsert passage preservation and flag
  rejection, normal-output passage/vector redaction, and plan-lineage 1/2/3
  compatibility.
- `tests/test_automatic_routing_after_apply.py` runs the real approved apply
  pipeline: it embeds/writes eight content rows to an in-memory provider,
  commits DuckDB applied state, performs the real strong catalog read and
  conditional schema-v3 card update, then invokes namespace-free CLI retrieval
  through a fresh catalog client and the real multi-namespace retriever. A
  manual example intentionally duplicates one selected source passage; apply
  removes the generated duplicate, preserves the manual authority, and the
  immediately following retrieval succeeds.
- In that acceptance case, generic target-card metadata lacks the specialist
  phrase and the target centroid is below twelve distractors (`0.333 < 0.4`).
  Its individual source-passage vector nevertheless nominates the target into
  the unique-card top twelve; MiniLM selects it, fanout remains three, the
  actually applied specialist row is returned, and routing output contains no
  source passage.
- Activation tests prove exact certified behavior remains unchanged, valid
  projection drift reports provisional mode with no singleton threshold and
  top-three-or-fewer fanout, named routes avoid MiniLM, unrelated missing cards
  remain diagnostics, and malformed state never falls through to content.

## Performance evidence

`uv run python -m tests.benchmark_apply_catalog_registration --iterations 40`
used the actual pinned, already-cached BGE routing model with in-memory catalog
read/write boundaries and zero provider network calls. The same harness
alternated baseline and maximum batches after three warmups:

| Path | Samples | Median | p95 |
| --- | ---: | ---: | ---: |
| Prior one-text base projection | 40 | 12.742 ms | 13.954 ms |
| Maximum base + eight evidence batch | 40 | 65.444 ms | 72.272 ms |
| Unchanged projection reuse | 40 | 10.145 ms | 10.489 ms |

The bounded worst-case batch added 52.702 ms median / 58.318 ms p95 in this
local harness. Reuse performed zero routing embeddings. Corpus size does not
enter this registration cost, and no reranker, evaluation, content query, or
extra provider request was introduced.

## Active authority and package receipts

`src/buoy_search/data/automatic_routing_confidence_calibration.json` is 3,108
bytes with raw SHA-256
`745cdb76c894ef1770f6daf3d303f2b6d0ba6905098924f1cb1a8fa40e738fea`.
The strict no-argument loader returns schema `3`, mode `active`, revision
`active-anchor-e559a8aa-v1`. It retains certified catalog projection
`e559a8aac5a4f7fb808f137b1c6a3710b6cd5b6764fc84f7f06120e33307ef7c`
and binds these installed sources:

- routing-quality scorer:
  `5d53624613bf5a80ad80e6d103d07cb0fab2d2a6ae2a1456e6c2709147d67aa7`;
- routing module:
  `e0711bc40a90c364ca52c7a9884d29342be21e3df43950ec26033a70c2b6e9fd`;
- CLI module:
  `92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`;
- evidence module:
  `78b792098ee0c49bedc7c135dffc33f4096f7d92222bc437f5d8438f1e015c7b`;
  and
- evaluator runner:
  `6f179cb93ef85754e05e86bf8f300f1d430aefa34cccbf3ae7e23feb618402cc`.

The diagnostic source distribution contains 142 files and has SHA-256
`30f08f92d243a50735a6f6e6fc1e7363936e20e5645f5a69c5754d211c012b81`.
The 69-file wheel has SHA-256
`8527d2b0bd64740f4d76906799d7881a2fe9c4224a8979c3c42b75133c368e7f`.
`release_automation.py validate-distribution` verified both. An isolated wheel
installation loaded schema 3 / active / `active-anchor-e559a8aa-v1`; top-level
help and `catalog repair-apply --help` completed successfully. These are
diagnostic artifacts, not published releases.

## Validation

The final implementation checkpoint passed:

- `848/848` full repository tests under Python 3.13;
- `848/848` full repository tests under Python 3.11;
- a 331-test focused plan/apply/catalog/routing/activation basket;
- independent review runs of `93/93` repair/catalog/apply tests and `108/108`
  additional plan/end-to-end/routing tests;
- the true end-to-end fake-provider apply-to-automatic-retrieve acceptance;
- `scripts/validate_ranking_contract.py` with 13 datasets, 369 judgments, and
  frozen bundle SHA-256
  `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`;
- `scripts/c6_syntax_forecast.py validate` at forecast SHA-256
  `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`;
- `scripts/release_automation.py validate-source` and
  `validate-distribution`, including active source/runner receipt validation;
- `uv sync --locked --python 3.13`, `uv lock --check`, complete source/test/
  script compilation, and `git diff --check`;
- wheel/source-distribution build, isolated wheel install, command-help smoke,
  and no-argument packaged-authority load.

The sandboxed full run predictably blocked five existing localhost crawler
fixtures and two existing clean-install tests that resolve build dependencies.
The exact suite then passed with localhost/cache/network permission under both
supported interpreters. The performance harness invoked only the already-
cached pinned BGE model; no model was downloaded.

## Privacy and rollout boundary

Schema-v3 card passages are bounded but verbatim-derived source excerpts.
Normal Buoy catalog/routing output redacts passages and vectors, but a principal
authorized to query raw provider rows in `buoy-routing-catalog-v1` can read the
excerpts. Deployment must therefore treat raw catalog credentials and ACLs as
source-content access, not metadata-only access.

All source, catalog, and content interactions in tests used local fixtures or
in-memory fakes. No live website, repository, warehouse, Turbopuffer namespace,
schema, card, content row, credential, deployment, registry, tag, release, or
pull request was read or mutated by this task. Dependency synchronization and
isolated package installation used the package network/cache only.

Existing remote catalogs require the explicit reader-first schema-v3 migration
after compatible code is deployed; a missing catalog requires separate
operator provisioning. Existing corpora acquire truthful passages only from a
fresh reviewed plan/apply or separately authorized backfill. Rolling back to
an older exact-v2 reader after v3 migration fails closed and therefore requires
the documented operational plan. This task performs no live migration,
deployment, release, or self-integration.
