Status: active
Created: 2026-07-20
Updated: 2026-07-21

# Deterministic Treatment Token-Budget Subdivision

## Authority and activation

This active focused specification defines source-only post-line-range subdivision for the two active Python-aware treatment arms. Independent review passed PR #76 pre-ratification head `581d9ec79ed5426dbc174e0373805c674d79184c`, and the user ratified the exact reviewed source contract unchanged. It composes with `.10x/specs/repo-python-syntax-chunking-experiment.md`; activation authorizes only the bounded implementation ticket, not implementation in the ratification turn, plan or forecast regeneration, prose behavior, or C6 execution.

The preserved exact checkpoint remains authoritative: `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, maximum 512 tokens, tokenizer-files identity `9c7beccadaa552c323907a895ad9ab188d8b75763022403f72c5d91085334f3b`, `add_special_tokens=true`, and `truncation=false`. Checkpoint `c3a1560e611114760909c110a118a3ce1a60f0527de08c769a85a20b263f4e0f` found exactly 21,292 incompatible treatment rows across 4,162 paths, maximum 12,785 tokens.

Read-only decomposition found that the headline total contains two different surfaces:

| Incompatible row class | Exact plan rows | Unique `(repository, row_id)` values | Distinct report `repo_path` strings | Disposition |
|---|---:|---:|---:|---|
| Treatment source with exact physical-line ranges | 20,926 | 11,427 | 4,105 | Active source-line subdivision contract below |
| Unchanged prose path | 366 | 183 | 57 | Active prose Option A preserves bytes and retains every row fail-closed; this source specification MUST NOT invent prose subdivision |

The two row classes have disjoint `repo_path` strings, producing the checkpoint's exact 4,162-path-string union. Source rows represent 4,111 repository-qualified paths because five source path strings occur in more than one repository; `pyproject.toml` occurs in three repositories, so those five shared strings produce six additional repository-qualified occurrences; the preserved report intentionally defines its headline path count from the unqualified `repo_path` field. The 366 prose plan rows are 9 pytest rows per treatment arm and 174 Ruff rows per treatment arm. Therefore this source-only contract cannot by itself make C6 tokenizer-ready.

## Provenance map

| Ratified or observed semantic | Provenance at activation |
|---|---|
| Exact tokenizer revision, 512 maximum, file identity, special tokens, no truncation; 21,292 rows / 4,162 paths / max 12,785 | Active-record-backed by the C6 forecast/token report and explicitly required by the user |
| Exactly 20,926 incompatible source rows and 366 incompatible prose rows | Source-observed by read-only decomposition of the preserved token report |
| Treatment-only, physical-source-line boundaries, maximal contiguous subranges, exact citations/reconstruction, stable ordering, unchanged control/header | User-ratified exactly as independently reviewed |
| Preserve each parent range's exact breadcrumb tuple on every child and never cross an existing parent boundary | User-ratified exactly as independently reviewed |
| Farthest-feasible exhaustive prefix algorithm rather than binary search or approximate counts | User-ratified exactly as independently reviewed |
| A one-line rendered candidate above 512 invalidates its complete repository/arm plan | User-ratified exactly as independently reviewed |
| The 366 prose rows remain an independent C6 stop | Active prose Option A and record-backed consequence of source-only scope |
| New plan/artifact/namespace/count/storage identities after later implementation | Source-observed consequence of current hash-bound planning; exact values remain blocked on implementation and regeneration |

The source-only semantics became active only after independent PASS and explicit user ratification recorded in `.10x/reviews/2026-07-20-deterministic-token-budget-subdivision-contract-review.md` and `.10x/evidence/2026-07-20-deterministic-token-budget-subdivision-contract-ratification.md`. Subsequent active prose Option A, recorded in `.10x/evidence/2026-07-21-prose-token-budget-option-a-ratification.md`, preserves all prose bytes and retains the 366 rows fail-closed; the completed shaping owner is `.10x/tickets/done/2026-07-20-shape-prose-token-budget-compatibility.md`.

## Purpose and scope

The behavior adds one deterministic compatibility pass after the active syntax processor has produced its exact treatment `SourceRange` values and before treatment `MarkdownChunk` values are finalized. It applies only to source ranges in:

- `fixed-80-python-breadcrumbs`; and
- `python-ast`, including its Python-parse and non-Python fixed/no-breadcrumb fallbacks.

It does not process `current-default`, common repository header chunks, Markdown/prose chunks, or ordinary no-arm/metadata/card paths. It does not rerun AST ownership, decorator matching, trivia attachment, fallback classification, or the generic Markdown/sentence splitter.

## Exact token accounting

### Pinned tokenizer

Every compatibility decision uses only the already-pinned offline tokenizer:

- model: `BAAI/bge-small-en-v1.5`;
- immutable revision: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- implementation observed by the checkpoint: `transformers.models.bert.tokenization_bert.BertTokenizer` under locked `transformers==5.12.1`;
- exact tokenizer file-set identity: `9c7beccadaa552c323907a895ad9ab188d8b75763022403f72c5d91085334f3b`;
- required `model_max_length`: exactly `512`; and
- explicit call behavior equivalent to `tokenizer(text, add_special_tokens=True, truncation=False, padding=False, return_length=True)` with no model construction, inference, network fallback, or alternate tokenizer.

A missing/mismatched revision, implementation, file identity, package lock, maximum, or option fails local planning. An approximate token count may be retained only for descriptive reporting; it cannot make a boundary or readiness decision.

### Complete final embedding payload

For every candidate child `[S,E]`, count the exact `MarkdownChunk.embedding_text` that the final plan would embed, not source text in isolation:

```text
Title: <repo_path>

Section: <cleaned_repo_path> > Lines S-E

[Symbol breadcrumbs: <the parent SourceRange breadcrumb tuple joined by "; ">\n\n]
<whole-file-safe opening fence><language unless text>
<unchanged LF physical lines S through E joined by LF>
<same closing fence>
```

The bracketed breadcrumb block is absent when the parent tuple is empty. Counting therefore includes title/path overhead, the exact final `Lines S-E` citation and its digits, double-LF context separators, breadcrumb text, blank separator, language/fences, source payload, and tokenizer special tokens. The unchanged canonical blob URL and manifest metadata are citations but are not part of the current embedding text; validation asserts they remain unchanged rather than charge nonexistent token overhead.

The whole-file-safe fence and language are computed exactly as the active treatment renderer does. The candidate MUST be rendered through the same production rendering function used for emission; a separately reconstructed approximation is not sufficient authority.

## Deterministic maximal-prefix algorithm

For each active parent source range `P=[p,q]` in existing order, retaining its exact breadcrumb tuple `B`:

1. Set cursor `s=p`.
2. Render and exactly tokenize every candidate prefix `[s,e]` for every integer `e` from `s` through `q`, using the final child citation `Lines s-e` and `B`.
3. Let `F` be the ordered set of candidate ends whose complete rendered embedding payload is at most 512 tokens.
4. If `F` is empty, fail the complete repository/arm plan at physical line `s`; do not split the line, truncate, omit the file, drop breadcrumbs, change the fence/language/citation, or invoke fallback.
5. Otherwise choose `e=max(F)`, emit exactly `[s,e]`, and set `s=e+1`.
6. Repeat until `s=q+1`, then process the next parent range.

This exhaustive farthest-feasible-prefix rule is intentional. Each active parent has at most 80 lines, so at most 80 candidate tokenizations are needed at one cursor. Binary search or “append until first failure” would assume token-count monotonicity even though changing citation digits and tokenizer context has not established that invariant. The selected child is maximal within its parent at its fixed start: no later end in that parent fits the exact budget.

The algorithm MUST NOT combine adjacent compatible parents, cross fixed-80 or AST ownership-region boundaries, search for statement/token/sentence/blank-line breaks, or globally optimize chunk count. A currently compatible parent is tested as one exact candidate first and remains one byte-identical final source chunk when it is at most 512.

## Coverage, citations, breadcrumbs, and ownership

For each emitted child:

- `Lines S-E` MUST equal its exact unchanged LF-coordinate payload;
- children of one parent MUST be nonempty, ascending, adjacent, non-overlapping, and reconstruct that parent exactly;
- all children across the file MUST reconstruct the active treatment's full LF physical-line vector exactly once;
- no generated title, section, breadcrumb, fence, or common header text participates in source reconstruction;
- canonical URL and source/page metadata remain those of the parent file;
- the parent `SourceRange.breadcrumbs` tuple is copied unchanged to every child;
- AST children therefore retain the same innermost owning symbol/module ownership as their parent; nested ownership is not recomputed or crossed;
- fixed-80 children retain the parent window's ordered, de-duplicated intersecting-chain context; and
- Python-parse/non-Python fallback children retain the parent's empty breadcrumb tuple and existing sanitized fallback category.

Copying the parent tuple is the smallest post-line-range composition and makes overhead deterministic. Recomputing narrower fixed-window breadcrumb sets would be a different treatment semantic and is not part of this active contract.

Blank, comment, form-feed, and other trivia-only physical lines remain ordinary intact LF-coordinate lines. They can be grouped with adjacent lines under the same parent and budget; they are never dropped, normalized, attached again, or emitted as zero-line chunks. A blank line is still tested inside the complete fenced/cited payload.

## Identity and order

- File order, header-before-source order, active parent order, and prose order remain unchanged.
- Children replace only their over-limit parent at that position and are ordered by ascending `(start,end)`.
- Final `chunk_index` values are reassigned consecutively using the existing treatment ordering.
- Final row IDs continue to derive from the existing canonical URL, exact child `section_path`, and exact child content hash. Thus regeneration from identical source and contract is deterministic; an unchanged compatible source row retains its row ID even if preceding subdivision changes its `chunk_index`.
- Split parents necessarily receive new child section/content/row identities. Plan ID, artifact hash, JSONL hash, counts, storage, request forecast, and any contract-hash-derived namespace candidate MUST be regenerated rather than projected from the preserved forecast.

“Stable” means deterministic for identical pinned inputs and contract, not preservation of the obsolete over-limit parent's identity.

## Fail-closed file and plan scope

An individually unsplittable physical line is a line whose exact one-line candidate, including its inherited breadcrumbs, final citation/path/title, fence/language, separators, and special tokens, exceeds 512. Its handling is:

1. abort the complete local plan for that repository and treatment arm;
2. report only repository, arm, repo path, one-based line number, exact token count, tokenizer checkpoint, and `max=512`; do not print source content or token IDs;
3. emit no successful partial plan/manifest/chunks artifact and do not omit or fall back the file; and
4. keep the complete nine-plan C6 envelope blocked even if other plans succeeded.

Unchanged non-source rows are independent stop gates. Any common header above 512 would fail rather than be split or changed. Any prose row above 512—including the preserved 366—would fail rather than be truncated, line-split under this source contract, omitted, or silently accepted. Consequently source-only subdivision cannot support a passing C6 readiness checkpoint until prose behavior is separately shaped, reviewed, and ratified or the active plan scope is explicitly changed by separate authority.

## Downstream implementation and validation requirements

Independent review and explicit ratification are complete, and `.10x/tickets/2026-07-20-implement-deterministic-token-budget-source-subdivision.md` is the bounded executable owner under which source/tests may change. That work MUST prove at least:

1. **Tokenizer identity/options:** exact revision/file/class/lock/512 checks; special tokens on; truncation and padding off; offline/no-model/no-inference behavior; mismatch failure.
2. **Complete overhead:** golden counts include title, cleaned path, changing `Lines S-E` digits, breadcrumbs, blank separators, fences/language, payload, and special tokens.
3. **Algorithm:** exhaustive farthest-feasible selection, including a synthetic non-monotone candidate-count seam proving no binary-search/first-failure assumption; every emitted payload is `<=512`.
4. **Coverage:** exact parent/file LF-vector reconstruction, adjacency, zero overlap/omission, terminal-LF/form-feed/blank/trivia behavior, and exact child citations.
5. **Composition:** fixed breadcrumbs copied, AST owner/nesting retained, fallback category retained, no generic split/overlap, and no crossing active parent boundaries.
6. **Failure:** one-line payload at 513 fails the complete plan with sanitized identity; no partial artifact/file omission/fallback/truncation; header/prose incompatibility independently fails.
7. **Identity/order:** deterministic regeneration, unchanged compatible-row identity, expected split-row replacement, consecutive indexes, and stable file/header/source/prose order.
8. **Isolation:** byte-for-byte ordinary no-arm and `current-default` output parity; identical common header chunks; unchanged metadata/card and Markdown/prose behavior.
9. **Runtime matrix:** focused and complete suites pass on CPython 3.11 and 3.13 with identical boundaries, counts, citations, and identities.
10. **Safety:** no model construction/inference, credentials, provider calls, namespaces, retrieval, catalog/applied state/defaults, deletes, evaluation, or promotion.

### Forecast regeneration and stop gates

After passing implementation validation, a separate authorized local forecast task would have to:

- preserve the existing forecast, compact authority, and tokenizer report as immutable historical evidence;
- regenerate all affected treatment plans from the exact C1 commits/path allowlists and validate control/header/corpus parity anew;
- rerun the exact tokenizer-only preflight over every final row, report source/header/prose classes separately, and record individually unsplittable line counts without source content;
- regenerate exact plan/artifact/JSONL/token-report identities, namespace candidates, per-arm rows, writes, 64-row requests, content/vector/storage estimates, and multipliers;
- extend the compact authority and mutation tests to pin algorithm/version, tokenizer identity/options, maximum-child proof, coverage/citation proof, unsplittable-line categories, and unchanged control/header/prose facts; and
- obtain independent review at the exact regenerated head.

Stop before any write-approval checkpoint if any row is above 512, any line is unsplittable, active prose Option A retains the 366 incompatible rows, corpus/control/header parity drifts, coverage/citations fail, a pinned input differs, a count exceeds a newly approved bound, or review does not pass. A source-only passing result is descriptive evidence, not authority to ignore failed prose rows. Even a completely passing regenerated forecast would still require the existing separate exact nine-namespace write approval; no prior approval carries forward.

## Options and tradeoffs

### Selected contract: physical-line exhaustive farthest prefix

- Preserves exact active treatment coordinates, reconstruction, citations, and ownership.
- Deterministic without assuming tokenizer monotonicity.
- Repeats breadcrumb/path/fence overhead and may create more rows than token-fragment alternatives.
- Fails on one rendered physical line above budget and does not solve prose.

### Rejected for this checkpoint: split inside a physical line

Token/character fragmentation could fit a long line but would require new intra-line coordinates and citation semantics, weaken exact `Lines S-E`, and change reconstruction/identity rules. It is a separate product contract, not a fallback.

### Rejected for this checkpoint: generic token/sentence splitter or truncation

The generic splitter can normalize/overlap payload and citations; truncation omits source. Both conflict with exact treatment reconstruction and active treatment isolation.

### Not selected: global optimal partition or crossing parent boundaries

A dynamic program might minimize row count, and merging adjacent parents might recover budget, but either would make existing fixed/ownership boundaries and breadcrumb semantics subordinate to a new global objective. The requested maximal deterministic post-range pass needs neither complexity.

## Acceptance scenarios

1. A compatible 80-line parent remains one identical row.
2. An over-limit parent whose farthest feasible first end is 37 produces `[start,start+36]` followed by the farthest feasible prefix from line 38, with every final payload at most 512.
3. Candidate feasibility that fails at one intermediate end but fits a later end chooses the later farthest feasible end.
4. A 513-token complete one-line payload aborts the repository/arm plan without content disclosure or partial output.
5. Breadcrumb-heavy fixed and AST parents count inherited breadcrumb overhead; every child copies the exact parent tuple and remains inside its parent.
6. Blank/trivia/form-feed and terminal-LF cases reconstruct the exact LF vector with exact child `Lines S-E`.
7. Common headers, `current-default`, ordinary no-arm, metadata/cards, and prose outputs are byte-for-byte unchanged.
8. The preserved 366 incompatible prose plan rows keep C6 readiness false even if every source child fits.
9. Identical pinned inputs regenerate identical boundaries, row identities/order, plan artifacts, and exact forecast.

## Explicit exclusions

Implementation in the ratification turn; dependencies/lockfile changes; prose subdivision; intra-line splitting; truncation; generic treatment split/overlap; breadcrumb recomputation; control/header changes; plan/forecast/token-report mutation; model construction/inference/download; credentials/provider calls; namespace/catalog/applied-state/default operations; retrieval; deletes; evaluation; promotion; or write approval.

## Ratified user checkpoint

> Confirm or correct this **source-only** C6 subdivision contract: use only the exact offline `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` tokenizer with tokenizer-files identity `9c7beccadaa552c323907a895ad9ab188d8b75763022403f72c5d91085334f3b`, maximum 512, special tokens enabled, and truncation/padding disabled; for each existing treatment source range, count the complete final Title + exact `Section: … > Lines S-E` + inherited breadcrumb + fence/language + unchanged source payload, exhaustively choose the farthest end that fits from each cursor, and never cross the existing fixed/ownership parent. Children retain the parent's exact breadcrumb tuple and fallback/AST ownership, cover every LF physical line exactly once with payload-accurate `Lines S-E`, and receive deterministic semantic row IDs/order. If one complete one-line payload exceeds 512, abort that repository/arm plan with no truncation, fallback, omission, or partial artifact. Keep common headers, prose, `current-default`, and ordinary/default paths unchanged. This does **not** unblock C6: the exact checkpoint includes 20,926 incompatible source rows plus 366 unchanged incompatible prose rows; the prose rows remain a separate fail-closed blocker requiring separate shaping authority. After any later ratified implementation, regenerate and independently review the complete exact forecast and stop on any row above 512 before requesting the still-separate write approval.

The user ratified this exact source contract unchanged after independent review and explicitly acknowledged its incomplete C6 effect. The ratification did not supply prose semantics or authorize implementation in the ratification turn, forecast regeneration, model use, or writes.

## References

- `.10x/tickets/done/2026-07-20-shape-deterministic-token-budget-subdivision.md`
- `.10x/tickets/2026-07-20-implement-deterministic-token-budget-source-subdivision.md`
- `.10x/tickets/done/2026-07-20-shape-prose-token-budget-compatibility.md`
- `.10x/specs/deterministic-repository-prose-token-budget-compatibility.md`
- `.10x/evidence/2026-07-21-prose-token-budget-option-a-ratification.md`
- `.10x/reviews/2026-07-21-prose-token-budget-compatibility-contract-review.md`
- `.10x/evidence/2026-07-20-deterministic-token-budget-subdivision-contract-ratification.md`
- `.10x/reviews/2026-07-20-deterministic-token-budget-subdivision-contract-review.md`
- `.10x/tickets/2026-07-19-evaluate-python-syntax-chunking.md`
- `.10x/specs/repo-python-syntax-chunking-experiment.md`
- `.10x/evidence/2026-07-20-c6-python-syntax-pilot-forecast.md`
- `.10x/evidence/.storage/2026-07-20-c6-python-syntax-pilot-forecast.json`
- `.10x/evidence/.storage/2026-07-20-c6-python-syntax-tokenizer-preflight.json.gz`
- `.10x/evidence/2026-07-20-deterministic-token-budget-subdivision-shaping.md`
- `src/buoy_search/repo_syntax_chunking.py`
- `src/buoy_search/github_repo.py`
- `src/buoy_search/chunker.py`
- `src/buoy_search/plan_artifacts.py`
- `scripts/c6_syntax_forecast.py`
