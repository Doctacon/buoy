Status: active
Created: 2026-07-20
Updated: 2026-07-21

# Deterministic Repository-Prose Token-Budget Compatibility

## Active authority and purpose

This focused specification activates only the user-ratified Option A no-action contract for the repository Markdown/prose compatibility surface exposed by C6. Every repository-prose `MarkdownChunk` MUST remain byte-for-byte unchanged across the ordinary no-arm path, explicit `current-default`, `fixed-80-python-breadcrumbs`, and `python-ast`. No prose row may be split, truncated, omitted, recited as compatible, or changed in identity, order, count, or artifact representation.

The exact preserved treatment checkpoint therefore MUST retain all 366 incompatible prose plan rows—183 unique `(repository,row_id)` parents across 57 paths, duplicated in the two treatment arms—as an independent fail-closed C6 stop. C6 remains blocked. This active specification authorizes no implementation or implementation ticket, tests, generic pipeline changes, plan/artifact regeneration, tokenizer execution, model construction/inference, provider/live operations, C6 execution, namespace writes, or write approval.

The active source-only contract `.10x/specs/deterministic-treatment-token-budget-subdivision.md` MUST NOT be reused for prose. Repository prose has heading-based sections and generic sentence overlap, not physical `SourceRange` ownership, breadcrumbs, exact `Lines S-E` citations, or source-line reconstruction. Exact decomposition, the 57-path inventory, cause analysis, and rejected exploratory option deltas are recorded in `.10x/evidence/2026-07-20-prose-token-budget-compatibility-shaping.md`.

## Provenance map

| Semantic or observation | Current provenance |
|---|---|
| Pinned BGE tokenizer revision/files/class/lock, maximum 512, special tokens on, no truncation; preserved checkpoint identities | Active-record-backed by C6 records and the active source-only specification |
| 366 treatment occurrences = 183 unique parents across 57 paths; 9 pytest / 174 Ruff unique parents; exact 513–689 range | Source-observed from the preserved gzip report |
| The same 183 title/section/content/index/URL/row signatures occur in `current-default` | Source-observed from the preserved external plan roots |
| Approximate content accounting, heading sections, two-sentence overlap, complete embedding rendering, and semantic row identity behavior | Source-observed in `chunker.py`, `github_repo.py`, and `plan_artifacts.py` |
| No-action preserves parity but leaves C6 blocked | Record-backed consequence |
| Treatment-only splitting breaks prose parity with current-default | Source-observed consequence |
| All-three-arm splitting preserves cross-arm parity but breaks ordinary/current-default byte parity unless the ordinary generic pipeline changes too | Source-observed and active-contract-backed consequence |
| Option A parity, unchanged-row, no-action, and fail-closed policy | User-ratified after independent PASS; active in this specification |
| Split boundaries, overlap, coverage, atomic fallback, or changed failure scope | Rejected and non-authoritative under selected Option A |
| Final row/plan/artifact/namespace/storage identities after any implementation | Not applicable: Option A authorizes no implementation or regeneration |

## Selected Option A authority for the current C6 checkpoint

**Option A is selected: take no prose action in current C6.** Ordinary no-arm MUST remain byte-for-byte equal to explicit `current-default`, and repository prose MUST remain unchanged across `current-default`, `fixed-80-python-breadcrumbs`, and `python-ast`. The exact 366 incompatible treatment occurrences remain fail-closed and C6 remains blocked.

Options B, C, and D are rejected alternatives retained only as historical comparison material. They are not active behavior, recommendations, acceptance criteria, implementation inputs, or authority to open an implementation ticket. Any future proposal to split prose or change the shared generic pipeline would require a new shaping owner, explicit supersession of this Option A contract, independent review, and fresh user ratification. In particular, treatment-only B would supersede unchanged-prose isolation, while C6-local C would supersede ordinary/current-default equality.

## Current behavior that a decision must preserve or explicitly supersede

1. `.md/.markdown/.mdx` repository files enter the generic Markdown pipeline as source Markdown. `.txt/.rst/.adoc` files receive a synthetic `# <repo_path>` heading before generic parsing.
2. Generic parsing normalizes body whitespace/chrome, removes headings from content, and uses the heading stack as `section_path`.
3. Generic splitting uses a 300-token `TOKEN_RE` approximation over Markdown units, sentences, words, and token spans, with two-sentence overlap capped at 80 approximate tokens.
4. Final embedding text is nonempty `Title:`, nonempty `Section:`, and content joined by double LF. The canonical URL and source metadata are stored but not embedded.
5. Prose sections have no physical-line citation. A compatibility child can retain the parent's heading path but MUST NOT fabricate `Lines S-E` or source breadcrumbs.
6. Plan row identity derives from site, canonical URL, section path, and exact content hash, with deterministic duplicate ordinals. `chunk_index` records order but is not an ordinary unique row's semantic identity.
7. Current C6 requires ordinary no-arm and explicit `current-default` equality and requires unchanged prose across all three arms.

## Exact compatibility accounting common to any split option

If a later contract ratifies splitting, every compatibility decision MUST use exactly this pinned tokenizer boundary:

- model ID `BAAI/bge-small-en-v1.5`;
- immutable revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- implementation class `transformers.models.bert.tokenization_bert.BertTokenizer` from locked `transformers==5.12.1`;
- `special_tokens_map.json`, 125 bytes, SHA-256 `b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3`;
- `tokenizer.json`, 711,396 bytes, SHA-256 `d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66`;
- `tokenizer_config.json`, 366 bytes, SHA-256 `9261e7d79b44c8195c1cada2b453e55b00aeb81e907a6664974b4d7776172ab3`;
- `vocab.txt`, 231,508 bytes, SHA-256 `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3`;
- canonical tokenizer file-set identity `9c7beccadaa552c323907a895ad9ab188d8b75763022403f72c5d91085334f3b`;
- `model_max_length == 512`; and
- tokenization equivalent to `tokenizer(text, add_special_tokens=True, truncation=False, padding=False, return_length=True)`.

Before importing Transformers, the process MUST set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`; construction MUST resolve the exact local revision path with `local_files_only=True`. Missing local files, a different path revision, file size/hash/file-set identity, implementation class, package version, model maximum, or call option MUST abort before a boundary decision. No alternate tokenizer, network fallback, model construction, or inference is permitted.

For every candidate child, construct the final production `MarkdownChunk` with the unchanged parent context and count exactly that instance's `MarkdownChunk.embedding_text`. Its current production form is:

```text
Title: <unchanged parent title>

Section: <unchanged parent heading path>

<exact candidate content>
```

The two lines beginning `Section:` and their following blank separator are omitted when the parent `section_path` is empty; the angle-bracket placeholders and this explanatory sentence are not literal payload. `MarkdownChunk.embedding_text` also omits an empty title under current production behavior, although the preserved 183 parents have nonempty titles. Title, optional Section, exact double-LF separators, exact candidate content, and tokenizer special tokens are charged. Canonical URL and stored metadata remain outside embedding text and MUST be compared unchanged rather than charged.

A separately reconstructed string or approximate counter MUST NOT authorize a boundary. If its bytes differ from the production property, planning aborts. Every emitted final production payload MUST be re-rendered and re-counted; a count above 512 aborts the complete repository/arm plan before any successful artifact is emitted.

The remainder of this specification preserves the reviewed option analysis. RFC 2119 terms are binding only for selected Option A. Every statement under rejected Options B, C, and D—including projections, recommendations, future gates, and proposed mechanics—is non-authoritative comparison material.

## Selected Option A — no action / preserve exact generic prose

- Keep all prose chunks byte-for-byte identical across ordinary no-arm, `current-default`, and both treatment arms.
- Keep all section paths, overlap, identities, indexes, counts, and plan artifacts unchanged.
- Do not reinterpret the exact maximum, truncate silently, or claim tokenizer readiness.
- Keep all 366 preserved incompatible treatment occurrences as an independent C6 fail-closed stop.

This is the only option that preserves every current parity invariant without widening generic behavior. It does not advance C6 readiness.

## Rejected Option B — treatment-only final-row compatibility pass (non-authority)

This option would process only generic prose rows inside `fixed-80-python-breadcrumbs` and `python-ast` after current generic chunking and before final plan emission.

### Common minimal behavior

- A complete final parent `MarkdownChunk.embedding_text` at or below 512 retains exact content, Title/Section rendering, URL/path, document kind, tags, source hash, and metadata. Its final `chunk_index` and internal index-derived `MarkdownChunk.id` may change when preceding parents split; its manifest semantic row ID remains stable under the duplicate-group condition below.
- An over-limit parent is replaced at its current position by ordered children; no child crosses a parent boundary.
- Every child copies the exact parent `title`, heading `section_path`, canonical URL, `path`, `doc_kind`, ordered `tags`, `source_hash`, page hash, and complete source metadata. The compatibility pass changes only `content`, per-child `id`, and final `chunk_index` as required by splitting.
- Children MUST NOT receive physical-line citations, source breadcrumbs, code headers/fences, or invented headings. Their only embedding citation context remains the copied production Title and optional heading Section; canonical URL and stored metadata remain unchanged outside embedding text.
- Each child content is nonempty and is an exact half-open slice of the already-normalized parent content. Ordered slices begin at offset 0, are adjacent and non-overlapping, end at `len(parent.content)`, and concatenate character-for-character to exactly `parent.content`. The pass preserves the generic overlap already duplicated between different parents but adds no overlap between compatibility children and removes no existing parent character.
- After all replacements, chunks retain file/page and parent order, children occupy their parent's position in increasing offset order, and final `chunk_index` values are reassigned to consecutive integers beginning at 0 across the complete final indexing plan.
- `chunk_hash` remains SHA-256 of exact content. Row identity continues to use existing `generic_site_row_id(site_id, canonical_url, section_path, chunk_hash, duplicate_ordinal)`. After final ordering is known, existing `disambiguate_duplicate_chunk_row_ids` semantics assign ordinal 0 to the first member and increasing ordinals 1, 2, … to later members of every repeated base identity group; an ordinary unique group retains ordinal 0. Identical pinned inputs therefore regenerate identical ordinals and IDs.
- A compatible unchanged row retains its ID when its final duplicate-group membership and ordinal are unchanged, even if preceding splits shift only `chunk_index`. A split parent and its children necessarily have different content hashes and row IDs. If splitting changes duplicate-group membership or ordinal for an otherwise byte-identical row, its ID is not claimed stable; complete regeneration and an explicit identity-diff check are mandatory.
- All plan ID, artifact hash, manifest, chunks JSONL, token report, row/request/count/storage estimates, and any contract-hash-derived namespace candidate require complete regeneration; the preserved counts and artifacts remain immutable historical evidence.

### Boundary option B1 — farthest whitespace

Offsets are half-open Python `str` indexes into exact already-normalized `parent.content`. A whitespace run is a maximal nonempty sequence of code points for which `str.isspace()` is true; its candidate end is the offset immediately after the run, so the preceding slice owns the complete run. From each cursor, exhaustively count `parent.content[cursor:end]` for every later whitespace-run end plus `len(parent.content)` and select the farthest complete production-rendered candidate at or below 512. Adjacent slices therefore retain every character and reconstruct the parent exactly. If none fits, the recommended but unselected scalar policy below would apply only after separate ratification.

The exact C6 probe split every 183 unique parent into 2 children with no scalar fallback. Per treatment arm this would replace 183 parents with 366 children (+183: pytest +9, Ruff +174). Across both treatments, the isolated preserved-envelope delta is +366 rows and +6 estimated 64-row requests before source subdivision.

Tradeoff: smallest observed row increase, but it can split Markdown constructs or code spans at whitespace.

### Boundary option B2 — structure-preferred hierarchy (blocked definition)

The exploratory probe tried paragraph, current generic sentence, whitespace-run, and Unicode-scalar tiers in that order, choosing the farthest feasible end in the first tier with a feasible candidate and never assuming token-count monotonicity. It produced 392 children: 157 parents split in 2 and 26 split in 3. It used 366 paragraph ends and 26 whitespace ends, with no sentence or scalar fallback. Per treatment arm this is +209 rows (pytest +10, Ruff +199); across both treatments, +418 isolated rows and +6 estimated 64-row requests before source subdivision.

**B2 is not regeneration-grade and cannot be ratified from this draft.** Current `split_sentences` first computes `" ".join(text.split())` and returns normalized sentence strings; it does not return offsets into the already-normalized parent `MarkdownChunk.content`. Current paragraph/unit splitting also strips units and later rejoins them with double LF. The probe did not establish an authoritative mapping from those normalized values back to half-open Python `str` character offsets `[start,end)` in the exact parent content, including which child owns separator whitespace, repeated whitespace, LF runs, fenced-block newlines, or terminal whitespace. Guessing that mapping could change exact child bytes, token counts, coverage, and the reported projection.

A separate B2 shaping pass would have to define: offsets over the exact final parent content using Python Unicode-code-point indexing; an exhaustive set of paragraph and sentence end offsets derived without lossy reverse matching; deterministic ownership of every separator character; candidate content exactly `parent.content[start:end]`; and proof that ordered half-open intervals are nonempty, adjacent, non-overlapping, begin at 0, end at `len(parent.content)`, and concatenate exactly to the parent. Until those definitions are ratified and the projection is rerun, the observed B2 counts remain preserved exploratory evidence only and MUST NOT be acceptance criteria or implementation inputs.

Tradeoff if later defined: paragraph preference may preserve structure more strongly but the observed probe added 26 more rows per affected arm than B1. Tier priority and separator ownership are retrieval semantics, not implementation details.

### Parity consequence

Either B1 or B2 clears the 366 preserved treatment-prose occurrences in the local probe while deliberately breaking treatment/current-default prose equality for the affected parents. The identical 183 current-default parents remain above 512. Ratifying this option therefore requires explicit supersession of C6's unchanged-prose treatment-isolation invariant and an explicit decision that exact compatibility is treatment-only.

## Rejected Option C — all-arm or global final-row compatibility pass (non-authority)

Apply B1 or B2 identically to `current-default` and both treatment arms. This preserves prospective cross-arm prose parity.

- B1's isolated all-three-arm delta is +549 rows and +9 estimated 64-row requests.
- B2's isolated all-three-arm delta is +627 rows and +9 estimated 64-row requests.

If applied only inside C6 arm routing, explicit `current-default` ceases to equal the ordinary no-arm path. If applied to the shared generic pipeline, ordinary/current-default equality can remain prospective, but every generic caller gains an exact pinned-tokenizer dependency and changed behavior for over-limit final rows. The project-wide affected population is unknown. This is broader than treatment-prose compatibility and requires a separate global compatibility contract and impact review; it MUST NOT be smuggled into a C6-local implementation ticket.

## Rejected Option D — integrate exact accounting into the generic splitter (non-authority)

Replace approximate accumulation decisions inside the generic unit/sentence/word splitter with complete-payload exact accounting while retaining a separate 300 retrieval target and/or 512 hard maximum.

This could preserve generic structural intent more directly but leaves several independent choices:

- whether 300 remains an approximate soft target or becomes an exact content/full-payload target;
- whether Title/Section overhead is charged against 300, only against 512, or both;
- whether two-sentence overlap is retried, shortened, dropped, or allowed to force an earlier boundary;
- whether compatible existing chunks may be rechunked;
- whether a long sentence/word/code block is split by whitespace, token-like spans, Unicode scalars, or fails; and
- whether the behavior is treatment-only, all C6 arms, repository prose globally, or every generic corpus.

No projection is authoritative until those semantics are ratified. This option has the widest regression surface and is not the minimal C6-local change.

## Rejected future Option C mechanics retained for comparison only

Option A is active, so no splitting or fallback is selected. The following previously reviewed proposal is retained only as non-authoritative historical comparison material; it MUST NOT be implemented or used to open a ticket:

1. At a fixed half-open parent-content cursor, exhaustively test all ratified structural or whitespace end offsets greater than the cursor using exact production payload accounting; choose the farthest feasible end from the first ratified tier containing one.
2. If no such end fits, scalar fallback tests every later Python `str` boundary, which is a Unicode-code-point boundary for the UTF-8-decoded parent, and chooses the farthest end whose exact `parent.content[cursor:end]` production payload is at most 512. Scalar fallback does not skip, rewrite, normalize, or trim whitespace and does not require a boundary-adjacent character to be non-whitespace; exact adjacent interval coverage owns every character.
3. The terminal atomic failure condition is exact: after exhaustively rendering and counting every nonempty scalar-prefix candidate `parent.content[cursor:end]` for all `end` from `cursor + 1` through `len(parent.content)`, the feasible set is empty. Only then abort the complete plan for that repository and arm. Testing only the one-code-point prefix is insufficient because token-count monotonicity is not established. An empty-content child is never emitted.
4. On any tokenizer/render mismatch, terminal atomic failure, or final emitted row above 512, emit no successful plan, manifest, chunks JSONL, token report, or derived artifact for that repository/arm. Do not omit a file/row, retain an oversize parent, truncate, drop/alter Title or Section, accept a partial artifact, or invoke the old approximate path as fallback.
5. A sanitized atomic-failure diagnostic reports only repository, arm, repo path, unchanged section path, failing zero-based parent-content code-point offset, the minimum exact production-payload token count observed across the exhaustively tested nonempty scalar prefixes, model/revision/file-set checkpoint, and `max=512`; it prints no content, scalar value, candidate end, or token IDs. Prose has no truthful physical-line citation.

Dropping context, truncating, omitting content, or accepting oversize content is not recommended and is outside every option in this draft.

## Non-authoritative downstream considerations for any future superseding split

If a future, separately shaped contract supersedes Option A, its later implementation ticket would have to prove:

1. exact tokenizer identity/options/offline behavior and full final payload accounting;
2. deterministic boundary selection without monotonicity assumptions;
3. every final affected payload is at most 512;
4. exact normalized-parent content reconstruction under no-new-overlap behavior, plus preservation of existing inter-parent generic overlap;
5. unchanged Title/Section/canonical URL/metadata and absence of invented line citations/breadcrumbs/headers;
6. selected unsplittable/failure behavior with sanitized diagnostics and no partial artifact;
7. deterministic child identities/order/indexes and unchanged compatible-row identities;
8. exact selected parity scope: treatment-only divergence, all-arm parity, or global ordinary/current-default parity;
9. no source-range/generic-code/header/metadata-card behavior drift beyond the ratified scope; and
10. no model construction/inference, network fallback, credentials/provider calls, namespaces, retrieval, catalog/applied-state/default operations, deletes, evaluation, or promotion.

After separately reviewed implementation, a separately authorized complete forecast must regenerate source and prose together, validate every final row with the exact tokenizer, recompute all plan/artifact/JSONL/report/count/request/storage/namespace identities, and receive independent review. C6 stays blocked on zero incompatible rows and its still-separate exact nine-namespace write approval. No option in this draft unblocks C6 or carries prior approval forward.

## Authority exclusions

Activation selects no-action Option A only. It authorizes no source, test, dependency, lockfile, CI configuration, plan, manifest, chunks JSONL, forecast, compact authority, tokenizer report, validator, cache, corpus, or namespace mutation; tokenizer or model construction; inference; download or network access; credential/provider calls; retrieval; catalog, applied-state, routing-default, or namespace operations; deletes; evaluation; promotion; merge; or write approval. It creates no implementation authority and requires no implementation ticket.

## Exact ratified user checkpoint

The reviewed checkpoint is retained below verbatim for provenance. The user confirmed only its first Option A recommendation; every alternative and future Option C statement in the quoted checkpoint is rejected non-authority.

> **Recommendation for current C6 — confirm or correct Option A.** Preserve every current repository-prose `MarkdownChunk` byte-for-byte across ordinary no-arm, explicit `current-default`, `fixed-80-python-breadcrumbs`, and `python-ast`. Do not split, truncate, omit, recite as compatible, or alter prose identity/order/counts/artifacts. Keep the exact 366 incompatible treatment occurrences—183 unique parents across 57 paths, duplicated in the two treatments—fail-closed. C6 remains blocked and receives no implementation, regeneration, readiness, approval, or write authority.
>
> **If exact prose compatibility is required instead of Option A, do not activate B, C, or D from this draft.** Confirm only a separate shaping authorization for Option C on the shared ordinary generic pipeline. That shaping must preserve prospective ordinary/current-default and three-arm equality and must return for independent review with one exact regeneration-grade boundary contract. B2 is currently blocked because `split_sentences` and paragraph normalization do not provide lossless parent-content character offsets; its preserved +209 rows per affected arm / +418 across treatments is exploratory only.
>
> The separate Option C checkpoint must preserve this exact non-negotiable boundary unless explicitly corrected before any activation: use only model `BAAI/bge-small-en-v1.5`, revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, and class `transformers.models.bert.tokenization_bert.BertTokenizer` from locked `transformers==5.12.1`. Require `special_tokens_map.json` = 125 bytes / SHA-256 `b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3`; `tokenizer.json` = 711,396 bytes / `d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66`; `tokenizer_config.json` = 366 bytes / `9261e7d79b44c8195c1cada2b453e55b00aeb81e907a6664974b4d7776172ab3`; `vocab.txt` = 231,508 bytes / `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3`; and canonical file-set SHA-256 `9c7beccadaa552c323907a895ad9ab188d8b75763022403f72c5d91085334f3b`. Set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` before import; require the exact local revision path with `local_files_only=True`; require `model_max_length == 512`; and call equivalently to `tokenizer(text, add_special_tokens=True, truncation=False, padding=False, return_length=True)`. Any identity, option, local-file, or production-render mismatch aborts before a boundary decision; no alternate tokenizer, network, model construction, or inference is allowed.
>
> Count and revalidate only the final production `MarkdownChunk.embedding_text` for each candidate and emitted row; `<=512` is mandatory, and any reconstructed/production byte mismatch fails. Copy exact Title, heading Section, URL, path, document kind, ordered tags, source/page hashes, and metadata; keep URL/metadata outside embedding text; invent no physical-line citation, breadcrumb, code header/fence, or heading. Partition exact already-normalized parent content into nonempty adjacent half-open Unicode-code-point slices covering offsets 0 through `len(parent.content)` exactly once; preserve existing overlap between different generic parents and add no child overlap. Keep compatible content/context/metadata bytes unchanged; allow only index-derived internal `MarkdownChunk.id` and `chunk_index` to shift when preceding splits require it. Preserve plan order; place ordered children at the parent position; assign consecutive zero-based final indexes. Compute each base identity from site ID, canonical URL, exact Section, and exact content SHA-256; in final order assign duplicate ordinal 0 to the first repeated base identity and 1, 2, and so on to later members, while an ordinary unique identity remains ordinal 0. Require a compatible manifest row ID to remain stable whenever its duplicate-group membership and ordinal are unchanged.
>
> If no ratified structural or whitespace end fits from a cursor, exhaustively test every later Unicode-code-point end and choose the farthest exact feasible end. Abort the complete repository/arm plan only when that exhaustive nonempty scalar-prefix feasible set is empty; a failed one-code-point prefix alone is not terminal because token-count monotonicity is unproved. Emit no partial plan, manifest, chunks JSONL, token report, or derived artifact; do not omit, truncate, drop context, retain oversize content, or fall back to approximate behavior. Diagnostic fields are limited to repository, arm, repo path, section path, zero-based parent-content offset, minimum exact payload count observed across the scalar-prefix candidates, model/revision/file-set checkpoint, and `max=512`, with no content/scalar/candidate-end/token IDs.
>
> All B1/B2 row and 64-row-request deltas remain shaping projections; source subdivision changes later totals. Any future implementation still requires a separately reviewed active spec and executable ticket, complete source-and-prose regeneration, exact artifact/count/storage/namespace identities, independent review, zero incompatible final rows, and the still-separate exact nine-namespace write approval. This checkpoint authorizes no selection or activation; no source, test, dependency, lockfile, CI, plan, manifest, chunks JSONL, forecast, compact authority, tokenizer report, validator, cache, corpus, or namespace mutation; no tokenizer/model construction, inference, download, network, credential/provider call, retrieval, catalog/applied-state/default operation, delete, evaluation, promotion, merge, or write approval. Option A confirmation records no action only; shared-pipeline C authorization permits shaping records only. Neither path itself unblocks C6.

Independent review passed PR #78 pre-ratification head `02adbd1cd9fc33dd7f5d52e6c9ef33770f155f74`, and the user explicitly confirmed exact Option A. This specification is therefore active only for the no-action contract. The shaping ticket is done, no implementation ticket exists, and C6 remains blocked on the unchanged 366/183/57 fail-closed incompatibilities.

## References

- `.10x/tickets/done/2026-07-20-shape-prose-token-budget-compatibility.md`
- `.10x/evidence/2026-07-21-prose-token-budget-option-a-ratification.md`
- `.10x/reviews/2026-07-21-prose-token-budget-compatibility-contract-review.md`
- `.10x/evidence/2026-07-20-prose-token-budget-compatibility-shaping.md`
- `.10x/tickets/2026-07-19-evaluate-python-syntax-chunking.md`
- `.10x/specs/deterministic-treatment-token-budget-subdivision.md`
- `.10x/evidence/.storage/2026-07-20-c6-python-syntax-tokenizer-preflight.json.gz`
- `.10x/evidence/2026-07-20-c6-python-syntax-pilot-forecast.md`
- `src/buoy_search/chunker.py`
- `src/buoy_search/github_repo.py`
- `src/buoy_search/plan_artifacts.py`
