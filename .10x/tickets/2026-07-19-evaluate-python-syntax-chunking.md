Status: blocked
Created: 2026-07-19
Updated: 2026-07-21
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-19-implement-opt-in-python-syntax-chunking.md

# C6: Evaluate Python Syntax Chunking

## Scope

After C5 has an active ratified spec, passing required CI, and exact paired plan counts, evaluate only the specified `current-default`, fixed/breadcrumb, and syntax arms on Buoy, pytest, and Ruff. `current-default` MUST be the actual unchanged 80-entry repository renderer followed by current generic Markdown token split/overlap; pair each isolated Python-aware treatment against it on identical source commits/corpora. Use new namespaces and zero deletes.

## Acceptance criteria

- C5 is complete, focused/full CPython 3.11/3.13 CI is passing, and exact per-arm namespace names, commits, header/source row counts, storage multipliers, and write counts are reported before approval.
- The `current-default` control is proven identical to the ordinary pre-C5 no-arm pipeline; each Python-aware treatment is isolated from generic split/overlap and metadata/card treatments and paired against that control on the same selected corpus.
- Every apply targets a new namespace; no stale or namespace delete occurs; baseline namespaces, catalog, defaults, and local applied state outside the new namespaces remain unchanged.
- Live eval after approved applies is retrieval-only.
- Primary metrics match C4. Also report chunk-count multiplier, mean/p95 chunk tokens, symbol-boundary coverage, and fallback rate by language.
- The three-repo no-regression/positive-average/two-improving-repo rule is only an experiment escalation gate. Stop an arm at the pilot if it fails that gate, exceeds an approved chunk/storage bound, or gains only from the already-completed global metadata preamble. Passing permits only a request for separately approved full-basket experimentation; it is not promotion authority.
- Full-basket expansion requires a separate exact ten-repo forecast and approval; only the full-basket keep gate is governed by the active distribution policy.
- Passing means promotion-candidate evidence only; fixed-line behavior remains the default.

## Approval gate

Blocked until C5 local plans can fill this exact checkpoint:

> Approve up to `<rows>/<new namespaces>/<estimated writes and storage multiplier>` for the ratified Buoy/pytest/Ruff `current-default` control and its paired isolated Python-aware arms on the reported identical commits/corpora, with zero deletes and no catalog/default change?

Past namespace approvals do not authorize these writes. Approval covers only the exact planned commits/arms/counts.

## Stop conditions

- Stop before any live operation without exact approval.
- Stop on commit/corpus mismatch, unapproved/exceeded rows or storage, a failed pilot gate, fallback/coverage behavior that violates the active spec, or any need to delete/mutate a baseline namespace.
- Do not add Tree-sitter unless the Python experiment first passes and a later multilingual need is explicitly ratified.
- Stop before full expansion until its exact incremental forecast is separately approved.

## Evidence expectations

Approval provenance; required CPython 3.11/3.13 CI; paired control/treatment plan and apply summaries; exact header/source rows and writes/deletes; per-arm metrics/resources/fallbacks; retrieval-only proof; review; explicit no-promotion conclusion.

## Blockers

- **C5 dependency satisfied:** C5 is complete at independently reviewed PR #69 head `360c6b9c666ccf432c082ac44d0a1400955ce3e9`, with required focused/full CPython 3.11/3.13 validation.
- **Exact local forecast recorded but not approval-ready:** `.10x/evidence/2026-07-20-c6-python-syntax-pilot-forecast.md` and its compact checkpoint bind the three arms to C1-pinned Buoy `fcb7abbe1652d2eab4ee23816b6d992d893603ac` (57 selected source files after seven card-incompatible oversize paths), pytest `1aa747de62dd9e9f395513c25298ba604f1724d0` (572 files), and Ruff `e6856de97d72225196444b7d969b8fe084140503` (9,758 files). The exact envelope is 151,990 final rows/row writes across nine new deterministic namespaces, 2,378 estimated 64-row upsert requests, zero deletes, and 547,388,704 serialized-plan-row-plus-raw-vector estimate bytes (`2.607014766x` the three-control subtotal; provider overhead excluded).
- **Control citation wording corrected without output change:** the user ratified that `current-default` preserves exact existing generic-pipeline citation behavior even when no parseable `Lines S-E` component survives. The 2,722 Ruff rows across 170 paths are therefore parity evidence, not treatment-style citation failures. Treatment exact-range requirements remain unchanged; no row, plan, corpus, count, storage estimate, or default changed.
- **Exact model-tokenizer readiness fails:** offline tokenizer-only preflight used `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, exact tokenizer file identity `9c7beccadaa552c323907a895ad9ab188d8b75763022403f72c5d91085334f3b`, and its 512-token maximum with special tokens, no truncation, and no model construction/inference. Across 91,214 treatment plan rows it found 21,292 incompatible rows on 4,162 paths, maximum 12,785 tokens. Exact row IDs, paths, section paths, and counts are recorded in `.10x/evidence/.storage/2026-07-20-c6-python-syntax-tokenizer-preflight.json.gz` at checkpoint `c3a1560e611114760909c110a118a3ce1a60f0527de08c769a85a20b263f4e0f`. Read-only shaping decomposed that total into exactly 20,926 treatment source rows and 366 unchanged prose plan rows (183 unique repository/row identities across 57 paths, duplicated across the two treatments). The exact reviewed source-only contract is now active, with implementation separately open at `.10x/tickets/2026-07-20-implement-deterministic-token-budget-source-subdivision.md`; no source implementation or regenerated readiness result exists yet. The active source contract does not define prose subdivision. The completed shaping owner `.10x/tickets/done/2026-07-20-shape-prose-token-budget-compatibility.md` and active prose specification select exact Option A no action: preserve prose bytes across ordinary/current-default/fixed/AST and retain all 366 occurrences / 183 parents / 57 paths fail-closed. No prose implementation ticket exists by design. Therefore every current incompatible row still fails readiness, and the prose rows remain an independent fail-closed stop even after both source and prose contract ratification. Ruff additionally retains 559/2,875 Python parse fallbacks per treatment; deterministic fallback path-category hashes are in the compact forecast.
- **Independent forecast review and write approval remain absent:** repaired forecast records and deterministic validation require independent review at the refreshed forecast PR head. No exact approval exists for any of the nine namespace writes, and failed exact tokenizer readiness prevents presenting the unchanged write-approval checkpoint as passing. Source-contract ratification authorizes only the separate local source/test implementation ticket; it grants no C6 regeneration, implementation, or write authority. C6 remains `blocked`; no apply, retrieval, catalog/state/default change, delete, or promotion is authorized.

## Explicit exclusions

Source implementation; behavior shaping; Tree-sitter; baseline mutation/deletion; catalog/default changes; automatic promotion.

## References

- `.10x/specs/repo-python-syntax-chunking-experiment.md`
- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/tickets/done/2026-07-19-implement-opt-in-python-syntax-chunking.md`
- `.10x/tickets/done/2026-07-20-shape-deterministic-token-budget-subdivision.md`
- `.10x/tickets/2026-07-20-implement-deterministic-token-budget-source-subdivision.md`
- `.10x/tickets/done/2026-07-20-shape-prose-token-budget-compatibility.md`
- `.10x/specs/deterministic-repository-prose-token-budget-compatibility.md`
- `.10x/evidence/2026-07-21-prose-token-budget-option-a-ratification.md`
- `.10x/reviews/2026-07-21-prose-token-budget-compatibility-contract-review.md`
- `.10x/specs/deterministic-treatment-token-budget-subdivision.md`
- `.10x/evidence/2026-07-20-deterministic-token-budget-subdivision-shaping.md`
- `.10x/evidence/2026-07-20-deterministic-token-budget-subdivision-contract-ratification.md`
- `.10x/reviews/2026-07-20-deterministic-token-budget-subdivision-contract-review.md`
- `.10x/decisions/repo-ranking-promotion-policy.md`

## Progress and notes

- 2026-07-19: Opened blocked. No namespace names/counts, write budget, live call, or promotion was ratified.
- 2026-07-20: Clarified that the three-repo rule is an experiment escalation gate only, not active promotion policy.
- 2026-07-20: Reconciled C6 with the parent paired-default rule: the required control is the actual unchanged current renderer plus generic split/overlap, and each isolated Python-aware arm must be paired against it on the same corpus. C6 remains blocked on C5 and exact write approval.
- 2026-07-20: The exact seven-item C5 contract is now independently reviewed, user-ratified unchanged, and active. C6 remains blocked on C5 completion, passing exact paired local plans with namespace/row/storage/write counts, and separate exact write approval; no plan, namespace, live operation, or write was authorized.
- 2026-07-20: C5 closed after independent PASS at PR #69 head `360c6b9c666ccf432c082ac44d0a1400955ce3e9`; its dependency is satisfied. The existing bounded three-file Buoy plans do not fill this ticket's exact Buoy/pytest/Ruff pilot forecast. Exact pilot namespace names, commits/corpora, selected-file and header/source/total row counts, storage multipliers, and write counts remain required before the unchanged separate write-approval checkpoint. No C6 plan, live operation, namespace write, retrieval, or promotion was authorized.
- 2026-07-20: Executed only the authorized local forecast/preflight. Nine exact plans over the C1-pinned, arm-identical Buoy/pytest/Ruff source corpora forecast 151,990 rows/writes in nine deterministic namespaces, 2,378 default 64-row upsert requests, zero deletes, and 547,388,704 estimated serialized-row-plus-raw-vector bytes. Ordinary no-arm and explicit `current-default` signatures match exactly; headers/corpora match across arms; no model, credential, provider, namespace, retrieval, catalog, applied-state, dataset, label, default, or promotion operation occurred. Preflight nevertheless found 2,722 Ruff control source rows across 170 files without the active spec's `Lines S-E` component, 15,187 treatment rows above 512 approximate tokens, and 559/2,875 Ruff Python parse fallbacks per treatment. Recorded `.10x/evidence/2026-07-20-c6-python-syntax-pilot-forecast.md` plus compact checkpoint; C6 remains blocked on those findings, independent review, and separate exact write approval. The counts are not a write request and C6 was not made executable.
- 2026-07-20: Repaired the forecast after the user ratified the control-citation correction. Preserved all nine plans, row classes/counts, corpora, outputs, namespaces, and storage. Added checked-in deterministic generator/validator plus CI, path-hashed parse/non-Python fallback categories, and offline exact tokenizer-only preflight. Exact BGE preflight scanned 91,214 treatment rows and failed 21,292 rows across 4,162 paths above the pinned 512-token maximum (max 12,785); it used no truncation, model inference, provider, credentials, or writes. C6 remains blocked at exact checkpoint `c3a1560e611114760909c110a118a3ce1a60f0527de08c769a85a20b263f4e0f` for later shaping, independent review, and separate write approval.
- 2026-07-20: Hosted GitHub Actions run `29788028012` passed on exact repaired head `d9909fdd65a7456a1bdbb9b6bdb11a8a2b9ddd83`: Python 3.11, Python 3.13, and Build distributions all passed. CI pass validates the checked-in fail-closed checkpoint mechanics; it does not make C6 ready or grant write authority.
- 2026-07-20: Hardened only PR #71's validator review blockers. Added a 73,036-byte checked-in compact authority for the nine external plan projections and made validation fail closed over immutable plan/checkpoint identities, parity, namespaces, fallbacks, citations, safety, row/byte summaries, arithmetic, and the complete duplicated exact-token checkpoint. Added outer-hash-resigning mutation probes for every reviewed category. Forecast and token numbers remain unchanged; C6 remains blocked with no live operation or write authority.
- 2026-07-20: Refreshed PR #71 onto `origin/develop` `8c7750d` after PR #73 without changing the preserved forecast, authority, tokenizer report, or fail-closed validator/test bytes. Recorded the user's explicit decision to shape deterministic token-budget subdivision under a separate open ticket. Source-line boundaries, exact resulting citations, and individually over-limit line failure are candidate scope rather than active semantics; C6 stays blocked and no subdivision implementation, live plan/apply, or write authority exists.
- 2026-07-20: Source-only shaping produced an inactive focused draft and exact checkpoint decomposition: 20,926 incompatible source plan rows and 366 incompatible unchanged prose plan rows sum to the preserved 21,292. The draft proposed no prose behavior, so those 366 rows remained a separate fail-closed readiness stop. No active spec, source/test, plan/forecast/token report, validator, namespace, or live state changed.
- 2026-07-20: Independent review passed PR #76 pre-ratification head `581d9ec79ed5426dbc174e0373805c674d79184c`, and the user ratified the exact reviewed source-only contract unchanged. The specification is active and a bounded local source/test implementation ticket is open. Exactly 366 incompatible prose plan rows remained under a separate blocked shaping owner, so C6 remained blocked before any regeneration or write checkpoint. No source/tests, preserved plan/forecast/token artifact, validator, model/live operation, namespace, or write changed in ratification.
- 2026-07-21: Independent review passed PR #78 pre-ratification head `02adbd1cd9fc33dd7f5d52e6c9ef33770f155f74`, and the user ratified exact prose Option A. Prose remains byte-for-byte unchanged across ordinary/current-default/fixed/AST; exact 366/183/57 incompatibilities remain fail-closed; no split, truncation, omission, compatibility relabeling, identity/order/count/artifact change, implementation ticket, regeneration, live operation, namespace write, or write approval exists. Prose shaping closed, but C6 remains blocked.
