Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/done/2026-07-20-shape-prose-token-budget-compatibility.md, .10x/specs/deterministic-repository-prose-token-budget-compatibility.md, .10x/tickets/2026-07-19-evaluate-python-syntax-chunking.md

# Prose Token-Budget Compatibility Shaping Evidence

## What was observed

The preserved C6 tokenizer report remains `.10x/evidence/.storage/2026-07-20-c6-python-syntax-tokenizer-preflight.json.gz`, embedded checkpoint `c3a1560e611114760909c110a118a3ce1a60f0527de08c769a85a20b263f4e0f`. Its tokenizer contract remains `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, tokenizer-files identity `9c7beccadaa552c323907a895ad9ab188d8b75763022403f72c5d91085334f3b`, `transformers.models.bert.tokenization_bert.BertTokenizer` under locked `transformers==5.12.1`, maximum 512, special tokens enabled, and truncation disabled. The four report-pinned files are `special_tokens_map.json` (125 bytes, SHA-256 `b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3`), `tokenizer.json` (711,396 bytes, `d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66`), `tokenizer_config.json` (366 bytes, `9261e7d79b44c8195c1cada2b453e55b00aeb81e907a6664974b4d7776172ab3`), and `vocab.txt` (231,508 bytes, `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3`). The shaping process set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` before import and used only the exact local revision.

Read-only inspection accounted for all **366 incompatible treatment prose plan rows** as **183 unique `(repository,row_id)` parents across exactly 57 repository paths**. Each unique parent occurs byte-for-byte and identity-for-identity in `current-default`, `fixed-80-python-breadcrumbs`, and `python-ast`; the preserved tokenizer report lists only the two treatment copies, hence `183 * 2 = 366`. The corresponding 183 unchanged `current-default` rows were not scanned by that treatment-only report but have the same complete embedding payloads and exact token counts. Any compatibility treatment that changes only the two treatment arms therefore breaks current prose parity; any treatment that changes all three arms changes the preserved current-default output.

The canonical sorted projection of the 183 unique report entries over `repository`, `row_id`, `repo_path`, `section_path`, and `token_count` is 38,588 bytes with SHA-256 `9ad340dae722e698df749c590c3f254d00aa87fedbe058d5a2fb8268df3fe626`. The gzip report remains the authority for every exact row ID and section path rather than duplicating 183 identities into this narrative.

### Exact class and path accounting

| Class | Unique parents | Paths | Exact token range | Total tokens above 512 |
|---|---:|---:|---:|---:|
| pytest RST documentation | 9 | 6 | 513–606 | 327 |
| Ruff Markdown documentation/changelogs | 48 | 14 | 514–689 | 3,651 |
| Ruff Markdown test fixtures | 56 | 28 | 513–634 | 1,849 |
| Ruff other Markdown (`crates/ruff_benchmark/resources/README.md`) | 1 | 1 | 546 | 34 |
| Ruff type-benchmark text snapshots | 69 | 8 | 513–610 | 2,401 |
| **Unique total** | **183** | **57** | **513–689** | **8,262** |
| **Two treatment copies in report** | **366** | **57** | **513–689** | **16,524** |

By extension, the 183 unique parents are 9 `.rst`, 105 `.md`, and 69 `.txt` rows. Their exact excess distribution is 54 rows at 1–16 tokens over, 84 at 17–64 over, 35 at 65–128 over, and 10 at 129–177 over.

### Exact 57-path inventory

Each line is `path — incompatible unique parents; min–max exact tokens`. Treatment-plan occurrence count is twice the stated parent count.

**pytest (9 parents / 6 paths)**

- `doc/en/announce/index.rst` — 3; 513–561
- `doc/en/announce/release-2.3.0.rst` — 1; 519
- `doc/en/announce/release-7.3.0.rst` — 1; 606
- `doc/en/announce/release-8.4.0.rst` — 1; 564
- `doc/en/announce/release-9.1.0.rst` — 1; 528
- `doc/en/explanation/flaky.rst` — 2; 531–553

**Ruff (174 parents / 51 paths)**

- `README.md` — 8; 520–689
- `changelogs/0.10.x.md` — 1; 544
- `changelogs/0.12.x.md` — 8; 531–662
- `changelogs/0.13.x.md` — 2; 560–581
- `changelogs/0.14.x.md` — 1; 621
- `changelogs/0.2.x.md` — 9; 539–669
- `changelogs/0.5.x.md` — 3; 529–618
- `changelogs/0.6.x.md` — 1; 559
- `changelogs/0.7.x.md` — 1; 576
- `changelogs/0.8.x.md` — 3; 517–589
- `changelogs/0.9.x.md` — 2; 532–560
- `crates/ruff_benchmark/resources/README.md` — 1; 546
- `crates/ruff_linter/resources/mdtest/pyflakes/string-dot-format-extra-positional-arguments.md` — 1; 584
- `crates/ruff_linter/resources/mdtest/pylint/invalid-character-backspace.md` — 1; 547
- `crates/ty_python_semantic/resources/mdtest/annotations/invalid.md` — 1; 525
- `crates/ty_python_semantic/resources/mdtest/annotations/new_types.md` — 1; 553
- `crates/ty_python_semantic/resources/mdtest/assignment/annotations.md` — 1; 540
- `crates/ty_python_semantic/resources/mdtest/bidirectional.md` — 2; 518
- `crates/ty_python_semantic/resources/mdtest/call/union.md` — 7; 536–616
- `crates/ty_python_semantic/resources/mdtest/comparison/tuples.md` — 1; 518
- `crates/ty_python_semantic/resources/mdtest/decorators.md` — 1; 591
- `crates/ty_python_semantic/resources/mdtest/diagnostics/error_context.md` — 1; 515
- `crates/ty_python_semantic/resources/mdtest/expression/boolean.md` — 1; 528
- `crates/ty_python_semantic/resources/mdtest/final.md` — 2; 587–607
- `crates/ty_python_semantic/resources/mdtest/generics/legacy/classes.md` — 3; 539–553
- `crates/ty_python_semantic/resources/mdtest/generics/legacy/paramspec.md` — 5; 520–634
- `crates/ty_python_semantic/resources/mdtest/generics/legacy/variance.md` — 2; 521–532
- `crates/ty_python_semantic/resources/mdtest/generics/pep695/aliases.md` — 2; 514–534
- `crates/ty_python_semantic/resources/mdtest/generics/pep695/functions.md` — 3; 514–577
- `crates/ty_python_semantic/resources/mdtest/generics/pep695/paramspec.md` — 3; 524–586
- `crates/ty_python_semantic/resources/mdtest/import/star.md` — 1; 516
- `crates/ty_python_semantic/resources/mdtest/override.md` — 5; 514–565
- `crates/ty_python_semantic/resources/mdtest/pep613_type_aliases.md` — 1; 545
- `crates/ty_python_semantic/resources/mdtest/properties.md` — 1; 527
- `crates/ty_python_semantic/resources/mdtest/subscript/tuple.md` — 2; 521–546
- `crates/ty_python_semantic/resources/mdtest/type_compendium/tuple.md` — 3; 519–586
- `crates/ty_python_semantic/resources/mdtest/type_of/basic.md` — 1; 524
- `crates/ty_python_semantic/resources/mdtest/type_of/generics.md` — 1; 516
- `crates/ty_python_semantic/resources/mdtest/type_properties/is_disjoint_from.md` — 2; 514–541
- `crates/ty_python_semantic/resources/mdtest/union_types.md` — 1; 513
- `docs/configuration.md` — 2; 514–544
- `docs/faq.md` — 6; 529–685
- `docs/formatter.md` — 1; 582
- `scripts/ty_benchmark/snapshots/black_Pyright.txt` — 4; 528–610
- `scripts/ty_benchmark/snapshots/black_ty.txt` — 1; 591
- `scripts/ty_benchmark/snapshots/isort_Pyright.txt` — 2; 519–538
- `scripts/ty_benchmark/snapshots/jinja_Pyrefly.txt` — 4; 518–568
- `scripts/ty_benchmark/snapshots/jinja_Pyright.txt` — 6; 520–556
- `scripts/ty_benchmark/snapshots/jinja_ty.txt` — 9; 518–604
- `scripts/ty_benchmark/snapshots/prefect_Pyrefly.txt` — 24; 521–603
- `scripts/ty_benchmark/snapshots/prefect_ty.txt` — 19; 513–559

## Why these parents exceed the pinned maximum

Current source establishes three cumulative causes rather than individually over-limit source lines:

1. `src/buoy_search/chunker.py::split_section_into_chunks` targets **300 approximate content tokens**, using `TOKEN_RE`; it does not make decisions with the pinned BGE tokenizer.
2. The splitter deliberately carries up to **80 approximate tokens** of two-sentence overlap after emission. Its post-flush append does not re-test overlap plus the next piece against 300. Exactly 182/183 incompatible parents have detectable predecessor overlap and approximate content above 300; the remaining parent has no detected overlap and approximate content 256.
3. The 300 target applies to content, while exact compatibility applies to `MarkdownChunk.embedding_text`: nonempty `Title:`, nonempty `Section:`, content, double-LF separators, and tokenizer special tokens. Title/section metadata are not charged by the current generic splitting decisions.

Across the 183 unique parents:

| Measure | Minimum | Median | Maximum | Mean |
|---|---:|---:|---:|---:|
| Approximate content tokens | 256 | 380 | 412 | 373.667 |
| Approximate complete payload tokens | 269 | 406 | 434 | 400.869 |
| Exact content-only tokens (with specials) | 468 | 508 | 665 | 521.115 |
| Exact complete embedding tokens | 513 | 546 | 689 | 557.148 |

The exact/approximate complete-payload ratio ranges from `1.225653` to `2.029740` (median `1.361111`). Exact complete-payload overhead above exact content-only count ranges from 16 to 62 tokens (median 37). Exact content alone is above 512 for 85 parents; for the other **98 parents**, content alone fits and Title/Section/separators/context effects push the final payload above 512. Therefore simply lowering or enforcing the existing approximate content target does not prove exact compatibility.

## Current generic prose semantics and citations

- `src/buoy_search/github_repo.py::markdown_for_repo_file` passes `.md/.markdown/.mdx` source through as Markdown and prepends `# <repo_path>` to `.txt/.rst/.adoc` source.
- `src/buoy_search/chunker.py::parse_markdown_file`, `normalize_markdown_body`, `iter_sections`, and `split_section_into_chunks` normalize the page, derive heading-only `section_path` values, split Markdown units/sentences/words with approximate accounting, and add two-sentence overlap.
- `src/buoy_search/chunker.py::MarkdownChunk.embedding_text` renders nonempty `Title:`, `Section:`, and content parts joined by double LF. Prose has no treatment `SourceRange`, no generated `Lines S-E`, and no common code-file header chunk.
- `src/buoy_search/plan_artifacts.py::build_chunk_record` and `generic_site_row_id` derive final row identity from site, canonical URL, exact section path, and exact content hash. `chunk_index` is ordering metadata, not semantic row identity; duplicate URL/section/content groups receive deterministic ordinals.

A prose compatibility pass can retain the existing canonical blob URL and heading path, but it cannot truthfully invent line citations. Repeating the same Title/Section on children adds context overhead. Exact concatenation of child content can reconstruct the already-normalized parent content; it cannot reconstruct original source exactly because the active generic path already normalizes content and introduces inter-parent overlap.

## Locally quantified option probes

These are read-only shaping probes, not selected behavior or regenerated artifacts.

### No action

All 183 unique parents remain unchanged in all three arms. The preserved report retains 366 incompatible treatment occurrences. Cross-arm prose parity and ordinary/current-default parity remain intact, but C6 remains fail-closed.

### Minimal farthest-whitespace final-row cap

An exploratory post-pass kept every compatible final prose row unchanged, retained each incompatible parent's exact Title/Section/URL/metadata, added no new overlap, and exhaustively selected the farthest existing whitespace-run end whose complete child embedding payload was at most 512. All 183 parents split into exactly 2 children (366 children); no scalar fallback was needed. This would add 183 rows per affected arm: 9 in pytest and 174 in Ruff.

Treatment-only application would add 366 rows to the preserved nine-plan envelope (`151,990 -> 152,356`) and, before any source subdivision, raise the default 64-row request estimate by 6 (`2,378 -> 2,384`). Applying the same probe to all three arms would add 549 rows (`151,990 -> 152,539`) and 9 requests (`2,378 -> 2,387`). These are isolated prose deltas only; source subdivision and full deterministic regeneration would supersede every aggregate identity and count.

Tradeoff: this is the smallest observed row delta but can split inside Markdown constructs or code spans at whitespace and does not prefer current unit/sentence structure.

### Structure-preferred final-row cap

A second exploratory post-pass kept the same parent/context/isolation rules, preserved every parent character exactly, added no new overlap, and tried deterministic boundaries in this order at each cursor: paragraph boundary, existing generic sentence boundary, whitespace-run end, then Unicode-scalar fallback. Within the first tier containing any feasible end, it chose the farthest end by exact complete-payload tokenization.

Exactly 157 parents produced 2 children and 26 produced 3, for **392 compatible children replacing 183 parents**. The observed boundaries were 366 paragraph and 26 whitespace ends; no sentence or scalar fallback was needed. Per affected arm this is +209 rows: pytest `9 -> 19` (+10) and Ruff `174 -> 373` (+199).

Treatment-only application would add 418 rows to the preserved envelope (`151,990 -> 152,408`) and 6 default-sized requests (`2,378 -> 2,384`). All-three-arm application would add 627 rows (`151,990 -> 152,617`) and 9 requests (`2,378 -> 2,387`). Every observed child was at most 512 exact tokens; observed child counts ranged from 31 to 512. Again, these are isolated probe deltas, not forecast authority.

Tradeoff: this better preserves Markdown block structure but creates 26 more children per affected arm than farthest whitespace. “Paragraph first” is a semantic preference, not an optimization theorem or current active requirement.

Post-review source reconciliation found that this B2 probe is not regeneration-grade. Production `split_sentences` first collapses whitespace with `" ".join(text.split())` and returns sentence strings rather than offsets into exact parent content; paragraph units are likewise stripped and rejoined. The probe did not establish authoritative half-open parent-content offsets or separator ownership. Its exact counts above remain preserved observations, but they cannot ratify or implement B2 until a separate shaping pass defines lossless Unicode-code-point offsets over exact `MarkdownChunk.content` and reruns the projection.

### Integrated exact generic splitter

Replacing approximate accounting inside the generic splitter and retaining two-sentence child overlap could preserve generic structure more directly, but it would potentially change compatible-row boundaries too, create repeated overlap whose exact cap must be rechecked, and affect every caller of the generic pipeline unless narrowly forked. No exact projection was made because target semantics (300 retrieval target versus 512 safety maximum), overlap retry/drop behavior, and global versus experiment scope are blocked decisions.

## Parity consequences

- **Byte-for-byte preserved parity:** only no action preserves the current three-arm prose output and the historical ordinary/current-default output.
- **Treatment-only cap:** can clear the 366 reported prose occurrences in a local projection but makes treatment prose differ from the 183 identical current-default parents. The current-default rows themselves remain above 512 if exact compatibility is applied to them.
- **All-three-arm experiment cap:** preserves cross-arm prose parity but makes C6 `current-default` differ from the ordinary no-arm pipeline, violating the current active control invariant.
- **Global generic cap:** can preserve ordinary/current-default and cross-arm parity prospectively only by changing the generic pipeline for all consumers. That is broader product behavior, not a C6-local mechanical fix, and requires separate authority and compatibility review.

Any splitting changes the affected parents' content hashes and row IDs, inserts children at the parent position, shifts later `chunk_index` values, and requires regenerated plan/artifact/JSONL/token-report/namespace/count/storage identities. Compatible semantic row IDs can remain unchanged because identity excludes `chunk_index`, but this must be proved after implementation. No preserved identity can be projected as final authority.

## Individually unsplittable content and failure boundary

Neither local final-row probe needed character/scalar fallback for the exact 183 parents, so the preserved checkpoint does not empirically choose a fallback. Reviewer repair makes the recommended future shared-pipeline C shaping boundary exact without selecting it: after ratified structure/whitespace tiers fail, exhaustively test every later Unicode-code-point end using production rendering and choose the farthest feasible end. Because token-count monotonicity is unproved, a failed one-code-point prefix alone is not terminal. Atomic failure occurs only when the exhaustive nonempty scalar-prefix feasible set is empty.

The recommended failure scope for that future shaping pass is the complete repository/arm plan: no partial artifact, file/row omission, retained oversize parent, truncation, context weakening, or approximate fallback. A sanitized diagnostic can report repository, arm, path, section, zero-based content offset, minimum observed scalar-prefix payload count, tokenizer checkpoint, and maximum, but no content, scalar, candidate end, or token IDs. Prose has no truthful physical-line citation. This is a recommendation for separate shaping only; Option A remains the current C6 recommendation and no fallback is selected or active.

## Procedure

1. Ran the required branch/status and worktree inspection and read the shaping ticket, active source-only token contract, C6 ticket/evidence, current generic Markdown renderer/chunker, syntax-arm routing, and plan row identity implementation.
2. Read the preserved gzip report with the Python standard library. Filtered only `row_class=prose`, checked exact repository/arm duplication, and computed the canonical 183-entry projection hash. The report was not rewritten.
3. Read the preserved external C6 plan roots still present under `/private/tmp/buoy-c6-python-syntax-forecast/plans`. Verified every one of the 183 row signatures—title, section, content, index, canonical URL, and row ID—is identical across all three arms.
4. Used the locked `transformers==5.12.1` environment and the already-local exact tokenizer files. Constructed only `BertTokenizer`, tokenized text with special tokens and no truncation, and reproduced every report token count. No model was constructed and no inference ran.
5. Ran the two in-memory probes described above against the exact parent payloads and printed aggregate results. No plan, corpus, source checkout, report, test, cache, namespace, or project artifact was created or mutated by the probes.
6. Drafted only shaping records. No active spec, source, test, dependency, CI, plan/forecast/token artifact, validator, namespace, state, dataset, default, or live service changed.

## Preserved-artifact attestation and limits

The preserved artifacts and validator must retain these whole-file SHA-256 values after record edits:

- forecast JSON: `4f40e8630438e1c1c2dead10c9587711652f695cab458a1f3efff68942ecb2bd`;
- compressed tokenizer report: `7adb1d6e05b2ce9f24ab69468758b867d6d7871221ba5d014090b3088e8fb808`;
- compact authority JSON: `cb12243c7cfea0701871c9a6205cb28e6afea4871db4cb1d99a45b831235ad71`; and
- `scripts/c6_syntax_forecast.py`: `0c3c0dd5d9cda426f4018a5a42a0ef1c759e535dcd1771552839c3a13dac45f8`.

The temporary plan roots are generation inputs previously hash-verified by the forecast, not checked-in authority. The probes establish local feasibility and isolated row/request deltas only. They do not ratify a boundary preference, prove an implementation, forecast source-subdivision interactions, generate final identities/storage, make current-default exact-token policy authoritative, clear C6, or grant write approval.

No dependency install/download, embedding model construction/inference, credential/provider/network call, namespace/retrieval/catalog/applied-state/default operation, delete, evaluation, promotion, active-spec/source/test/CI/forecast/token-report/validator mutation, or live plan/apply occurred.
