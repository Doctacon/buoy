Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/2026-07-19-evaluate-python-syntax-chunking.md, .10x/specs/repo-python-syntax-chunking-experiment.md

# C6 Python Syntax Pilot Local Forecast

## What was observed

The merged C5 implementation generated nine local-only plans for the exact `current-default`, `fixed-80-python-breadcrumbs`, and `python-ast` arms over the fixed Buoy/pytest/Ruff pilot. Every repository used its C1-pinned public source commit and exact C1 selected-path set as the selection allowlist. The unchanged 50 KiB source-file ceiling and the active spec's prohibition on file-card/oversize-card treatments then selected 57 Buoy source files, 572 pytest files, and 9,758 Ruff files identically across all three arms. Buoy's seven C1 oversize-card paths were deterministically omitted from every arm; their exact paths remain in the checkpoint artifact.

The checked-in machine-readable checkpoint is `.10x/evidence/.storage/2026-07-20-c6-python-syntax-pilot-forecast.json` (3,008,787 bytes; whole-file SHA-256 `4f40e8630438e1c1c2dead10c9587711652f695cab458a1f3efff68942ecb2bd`; embedded canonical payload SHA-256 `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`). It records every selected path with source hash/size/language, all nine namespaces and deterministic plan/artifact identities, local artifact file hashes, full row/token/chunk/fallback/storage distributions, path-hashed fallback categories, per-arm multipliers, first-apply diff summaries, and safety/equivalence results. The compact checked-in authority `.10x/evidence/.storage/2026-07-20-c6-python-syntax-pilot-authority.json` is 73,036 bytes (whole-file SHA-256 `cb12243c7cfea0701871c9a6205cb28e6afea4871db4cb1d99a45b831235ad71`; canonical SHA-256 `be56034851566fce250b58d64e24ece1902e139aeca977f5238519d3a762b100`) and pins the immutable plan/checkpoint projection without checking in the large plan roots. `scripts/c6_syntax_forecast.py` reconstructs the derived checkpoint from explicit hash-verified plan/source roots when generating and validates all checked-in checkpoint facts against that compact authority without relying on `/tmp`; the original external plan files are generation inputs by recorded hash, not runtime validation authority.

### Pinned corpus selection

| Repository | Source commit | C1 paths | Selected source files | Omitted oversize-card paths | Selected-path SHA-256 | Selected-corpus SHA-256 |
|---|---|---:|---:|---:|---|---|
| Buoy | `fcb7abbe1652d2eab4ee23816b6d992d893603ac` | 64 | 57 | 7 | `132b8ce145841c16ce661bf95ae63f89358428f0b2ee4488fc44347e81714433` | `4ad84f89503ea659832e9fe5c4c0f08d5b2fdf163d88f760b8711514b243e820` |
| pytest | `1aa747de62dd9e9f395513c25298ba604f1724d0` | 572 | 572 | 0 | `c31372d0f22b3fa2b628f4776fcb9e40db478103cb124715368f16239a5788ee` | `d66fa012dcf48e45ed020eafd10c6966b93ef9b389b944adf548411ecf8f7fb2` |
| Ruff | `e6856de97d72225196444b7d969b8fe084140503` | 9,758 | 9,758 | 0 | `52170634aef04324792002c607f4765da230ccc000a667ee721ed0879a7998b0` | `a44fba4516993d6c9f6e1e4533370f990f6259428d4671e64320029087e83a01` |

### Per-repository arm forecast

`Source rows` means every non-header final row belonging to a code file. `Prose rows` covers the unchanged Markdown/prose path. Token counts use C5's local deterministic `approximate_token_count`; they are not an exact model-tokenizer claim. `Storage estimate` is serialized `chunks.jsonl` bytes plus raw 384-dimensional f16 vector bytes and excludes provider index/ANN/attribute overhead.

| Repo | Arm | Header | Source | Prose | Final / row writes | 64-row write requests | Mean / p95 / max tokens | Rows >512 approximate tokens | Python parse fallback | Content bytes | Raw vector bytes | Storage estimate | Row multiplier | Storage multiplier |
|---|---|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---:|
| Buoy | `current-default` | 46 | 756 | 74 | 876 | 14 | 266.616 / 384 / 401 | 0 | N/A (not parsed) | 789,588 | 672,768 | 3,098,501 | 1.000000 | 1.000000 |
| Buoy | `fixed-80-python-breadcrumbs` | 46 | 252 | 74 | 372 | 6 | 558.694 / 1,178 / 1,720 | 211 | 0/40 (0%) | 863,227 | 285,696 | 1,860,192 | 0.424658 | 0.600352 |
| Buoy | `python-ast` | 46 | 1,298 | 74 | 1,418 | 23 | 152.554 / 520 / 1,279 | 73 | 0/40 (0%) | 895,765 | 1,089,024 | 4,566,896 | 1.618721 | 1.473905 |
| pytest | `current-default` | 291 | 2,113 | 1,089 | 3,493 | 55 | 234.629 / 380 / 404 | 0 | N/A (not parsed) | 2,844,424 | 2,682,624 | 11,966,435 | 1.000000 | 1.000000 |
| pytest | `fixed-80-python-breadcrumbs` | 291 | 914 | 1,089 | 2,294 | 36 | 331.643 / 776 / 3,199 | 614 | 0/236 (0%) | 3,036,721 | 1,761,792 | 9,089,023 | 0.656742 | 0.759543 |
| pytest | `python-ast` | 291 | 5,520 | 1,089 | 6,900 | 108 | 116.276 / 314 / 3,199 | 98 | 0/236 (0%) | 3,192,631 | 5,299,200 | 20,842,635 | 1.975379 | 1.741758 |
| Ruff | `current-default` | 9,156 | 39,589 | 7,662 | 56,407 | 882 | 190.714 / 380 / 2,085 | 7 | N/A (not parsed) | 34,189,046 | 43,320,576 | 194,902,691 | 1.000000 | 1.000000 |
| Ruff | `fixed-80-python-breadcrumbs` | 9,156 | 18,427 | 7,662 | 35,245 | 551 | 263.057 / 784 / 6,524 | 7,240 | 559/2,875 (19.4434783%) | 36,241,418 | 27,068,160 | 137,183,443 | 0.624834 | 0.703856 |
| Ruff | `python-ast` | 9,156 | 28,167 | 7,662 | 44,985 | 703 | 208.149 / 748 / 6,524 | 6,951 | 559/2,875 (19.4434783%) | 36,555,904 | 34,548,480 | 163,878,888 | 0.797507 | 0.840824 |

Both treatment arms also recorded deterministic non-Python fallback by every observed language: 6/6 Buoy non-Python code files, 55/55 pytest non-Python code files, and 6,281/6,281 Ruff non-Python code files. The checkpoint contains each language's count and rate. `current-default` parsed nothing and therefore has no syntax fallback rate.

### Aggregate write/resource checkpoint

| Arm | New namespaces | Final rows / row writes | 64-row write requests | Approximate tokens | Content bytes | Raw f16 vector bytes | Storage estimate | Rows multiplier | Storage multiplier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `current-default` | 3 | 60,776 | 951 | 11,810,733 | 37,823,058 | 46,675,968 | 209,967,627 | 1.000000 | 1.000000 |
| `fixed-80-python-breadcrumbs` | 3 | 37,911 | 593 | 10,240,075 | 40,141,366 | 29,115,648 | 148,132,658 | 0.623782 | 0.705502 |
| `python-ast` | 3 | 53,303 | 834 | 10,382,189 | 40,644,300 | 40,936,704 | 189,288,419 | 0.877040 | 0.901512 |

The exact nine-namespace envelope is **151,990 final rows / 151,990 estimated row writes / 2,378 default 64-row upsert requests / zero deletes / 547,388,704 estimated serialized-row-plus-raw-vector bytes**. Relative to the three current-default namespaces alone, that envelope is `2.500822693x` rows/writes and `2.607014766x` the stated storage estimate. Provider overhead and billing are unknown and are not represented as exact.

### Deterministic experimental namespaces

- Buoy: `github-doctacon-buoy-search-exp-c6-syntax-current-default-e6f97842ec90-v1`, `github-doctacon-buoy-search-exp-c6-syntax-fixed-80-python-breadcrumbs-e6f97842ec90-v1`, `github-doctacon-buoy-search-exp-c6-syntax-python-ast-e6f97842ec90-v1`.
- pytest: `github-pytest-dev-pytest-exp-c6-syntax-current-default-e6f97842ec90-v1`, `github-pytest-dev-pytest-exp-c6-syntax-fixed-80-python-breadcrumbs-e6f97842ec90-v1`, `github-pytest-dev-pytest-exp-c6-syntax-python-ast-e6f97842ec90-v1`.
- Ruff: `github-astral-sh-ruff-exp-c6-syntax-current-default-e6f97842ec90-v1`, `github-astral-sh-ruff-exp-c6-syntax-fixed-80-python-breadcrumbs-e6f97842ec90-v1`, `github-astral-sh-ruff-exp-c6-syntax-python-ast-e6f97842ec90-v1`.

The names mechanically use the active experiment pattern, `c6-syntax-<arm>`, current revised contract-inventory whole-file prefix `e6f97842ec90`, and version 1. They were absent from repository records and local plan inputs before this forecast. No live provider namespace listing was permitted or performed, so this record does not claim remote absence.

## Procedure

1. Verified the task worktree/branch and read C6, the active syntax spec, merged C5 ticket/evidence/review, and the C1 frozen contract/source-path bundle.
2. Used public unauthenticated git fetches to create pinned temporary checkouts. Across the workstream there were six public fetches: one first attempt stopped on an incorrect harness field, a second Buoy/pytest attempt stopped when unconstrained current selection exposed a pytest path outside the C1 frozen corpus, and the final successful attempt fetched all three commits and restricted selection to the exact frozen path allowlists. The stopped attempts created no checkpoint and caused no provider/model/state operation.
3. Built one card-free, metadata-free corpus per repository using exact frozen paths, the unchanged 50 KiB cap, `max_files=10000`, and no binding row cap (`max_chunks=100000`, never reached). Reused each immutable selected corpus for all arms.
4. Ran ordinary no-arm generic planning and explicit `current-default`; compared every plan chunk field through a canonical signature and ran C5's control validator. Both signatures matched exactly for all three repositories.
5. Ran the two isolated syntax processors with fixed `target_tokens=300` and `overlap_sentences=2`; the treatment processors do not perform generic token/sentence splitting.
6. Built and wrote all nine exact plan/manifest/chunk artifacts only under `/tmp`. Diffed each against an in-memory empty first-apply state: every final row is a new embed/upsert, and every plan reports zero stale/retained/deleted rows.
7. Counted rows by code header/code source/prose path, approximate token and physical-line-span distributions, per-file chunk distributions, fallback rates by current language classification, content/serialized-row bytes, and raw `[384]f16` vector bytes. No model was loaded.
8. Compared identical header records across all arms, recorded exact selected-path/source hashes, and emitted the compact checked-in checkpoint.
9. Postflight contract validation exposed that the ratified Buoy judgment removal had revised the contract inventory from C1's historical `918bdbd152f...` hash to current whole-file SHA-256 `e6f97842ec90f0558f51e70f93ea6b8f09f82f63019a27d0738d2b1efb427608`. The stale-name draft stopped locally. Rebuilt the deterministic plan envelopes with current prefix `e6f97842ec90`, recomputed all nine plan/artifact/file/checkpoint identities, and revalidated unchanged rows/content/corpora. No old or final namespace was read or written remotely.
10. After user ratification corrected only the control-citation wording, used the checked-in generator to add deterministic path hashes for Python-parse and non-Python fallback categories. Loaded only the exact cached tokenizer for `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` in offline mode, verified tokenizer file identity `9c7beccadaa552c323907a895ad9ab188d8b75763022403f72c5d91085334f3b` and maximum 512, and tokenized exact Title/Section/content embedding payloads with special tokens and no truncation. No model was constructed and no inference ran.

## Validation and blocking findings

Passing local equivalence/safety checks:

- the checked-in validator fails closed against the compact authority for plan/artifact/signature and local artifact file hashes, control/header/corpus parity, namespaces, fallback category hashes/counts, treatment citations/isolation, safety fields, row classes, JSONL/content/vector sizes, totals, multipliers, and approval arithmetic;
- token-report validation independently cross-checks treatment rows scanned, per-plan incompatible counts, row classes, maximum tokens, tokenizer revision/file identities/hash/options, no-live safety fields, and every duplicated forecast checkpoint identity;
- mutation tests cover each of those categories while recomputing mutable outer artifact hashes, so a self-consistent tampered outer hash does not pass;
- ordinary no-arm and explicit `current-default` plan signatures are exactly equal for Buoy, pytest, and Ruff;
- commit and selected-corpus hashes are identical across arms because each repository's single selected corpus is reused;
- common code-header identity hashes are equal across all three arms per repository;
- all nine first-apply diffs have every row in `rows_to_upsert`, zero stale rows, zero retained stale rows, and therefore zero planned deletes;
- all namespace names are unique and no metadata/card option is enabled;
- no tracked source, test, dependency, dataset, label, model, namespace, catalog, applied-state, or default file changed.

The forecast is **not approval-ready**. User ratification resolved the wording conflict without changing output: Ruff's exactly equivalent ordinary/current-default plan has **2,722 code source final rows across 170 files whose final `section_path` has no parseable `Lines S-E` component**, and the active contract now correctly requires preserving that exact existing control behavior. The affected path-list SHA-256 remains `abf6436f89e794bc8fed9c06ded00a8ffcb71ac98639ea02b12d7c0fc8674d39`. Treatment arms still require exact ranges.

Exact tokenizer readiness fails. The offline tokenizer-only preflight scanned all **91,214** treatment plan rows and found **21,292 incompatible rows across 4,162 paths** above the pinned 512-token maximum, with a maximum of **12,785** tokens. Per-plan incompatible counts are Buoy 232 fixed / 123 AST, pytest 698 / 208, and Ruff 10,221 / 9,810. Exact row IDs, repository paths, section paths, and token counts are in `.10x/evidence/.storage/2026-07-20-c6-python-syntax-tokenizer-preflight.json.gz` (embedded checkpoint `c3a1560e611114760909c110a118a3ce1a60f0527de08c769a85a20b263f4e0f`). No silent truncation or token subdivision semantic is authorized, so any incompatible row fails C6 readiness.

Ruff's 559 Python parse fallbacks per treatment are contract-shaped whole-file fallbacks and are reported, not silently downgraded. Their 19.4434783% rate is dominated by the frozen corpus's parser/formatter fixtures and still requires independent interpretation before any live request.

## Hosted validation at repaired head

GitHub Actions run `29788028012` passed on exact repaired head `d9909fdd65a7456a1bdbb9b6bdb11a8a2b9ddd83`: Python 3.11 job `88503676740` passed in 1m21s, Python 3.13 job `88503676777` passed in 1m13s, and Build distributions job `88503896312` passed in 11s. Both runtime jobs executed the checked-in blocked-forecast validator before the complete test suite. This is CI evidence only; it does not make tokenizer readiness pass or authorize C6.

## What this supports or challenges

This fills C6's exact local resource forecast with pinned commits/corpora, deterministic namespaces, row/write/resource counts, distributions, fallback rates, multipliers, and zero-delete/state/default evidence. It does not make C6 executable and does not ask for or grant namespace writes.

It supports treating the control citation observation as exact parity rather than drift after the user-ratified correction. It still challenges treating the counts as a passing approval checkpoint: exact pinned-tokenizer incompatibilities remain, no truncation or token subdivision is authorized, and independent review has not yet passed. C6 must remain blocked on exact checkpoint `c3a1560e611114760909c110a118a3ce1a60f0527de08c769a85a20b263f4e0f`, independent review, and the unchanged separate exact write approval.

## Limits

The storage estimate is deterministic local serialized-row bytes plus raw vector bytes, not provider storage, ANN overhead, transfer encoding, billing, or an approved budget. The original approximate-token distributions remain descriptive only; exact compatibility is governed by the separate pinned-tokenizer report. Local plan hashes and artifacts prove generated content, not remote namespace absence. No credentials, Turbopuffer/provider namespace operations, retrieval, catalog/state mutation, embeddings, model construction/inference, model downloads, deletes, truncation, token subdivision, or defaults occurred. The ignored `.venv` created by the locked local runner is not project state and is not staged.
