Status: active
Created: 2026-07-20
Updated: 2026-07-20

# Repository Python Syntax Chunking Experiment

## Authority and activation gate

This is the active exact contract for C5 in `.10x/tickets/done/2026-07-19-implement-opt-in-python-syntax-chunking.md`. It supersedes `.10x/specs/superseded/repo-python-syntax-chunking-experiment-originating-citation.md` after the user ratified one narrow evidence-driven correction on 2026-07-20: `current-default` preserves exact existing generic-parser citation behavior even when a final source row has no parseable `Lines S-E` component. Treatment arms still require exact line ranges. The correction changes no arm, output, coordinate, AST/tokenizer, ownership, subdivision, header, treatment coverage/citation, fallback, validation, default, or safety semantic.

The following boundaries are already established by the task and active records:

- the experiment is explicit opt-in, local-plan-capable, Python-only, and standard-library-only;
- current fixed 80-line repository rendering plus generic Markdown token splitting/overlap remains the default and must be the paired control;
- the existing `--repo-search-metadata` mode remains compatible outside the isolated experiment;
- Tree-sitter, new dependencies, live retrieval, writes, deletes, catalog/default changes, and product promotion are excluded.

Current source inspection establishes the implementation boundary that this active behavior governs:

- `src/buoy_search/github_repo.py` currently renders non-Markdown/non-prose repository files from `text.splitlines()` in consecutive 80-entry Markdown sections headed `Lines <start>-<end>`;
- every rendered repository code page currently begins with an H1 path plus a section containing `Repository file` and `Language`;
- `--repo-search-metadata` adds a file-wide path/stem/symbol preamble and regex-derived Python symbol breadcrumbs;
- `src/buoy_search/chunker.py` then applies the generic 300-token Markdown parser/split and up-to-two-sentence overlap to every section; embedded Markdown-like headings in code or fixture payloads can replace the originating line-range heading in a final chunk's `section_path`;
- manifest citations retain the GitHub blob URL and `section_path`; they do not create per-chunk GitHub line-fragment URLs;
- supported CPython 3.11+ provides `ast`, `tokenize`, class/function/async-function locations, and inclusive `lineno`/`end_lineno` spans. A fixed `feature_version=(3, 11)` can hold accepted grammar constant across the supported 3.11/3.13 CI matrix.

The current downstream split means a rendered 80-entry section is not necessarily one final chunk, generic splitting can normalize payload text, and sentence overlap can duplicate text between final chunks. Therefore the current-default control cannot truthfully claim exact final-chunk source reconstruction or exact payload-level line citations. The two experimental treatment arms below make final source chunks the exact-coverage boundary without changing that control. If C5 cannot preserve both contracts without changing unselected default behavior, it MUST stop.

## Purpose and scope

Define one local repository-indexing comparison that separately measures:

1. the actual current promoted default: fixed 80-entry repository sections followed by current generic Markdown token splitting and overlap;
2. Python ancestor breadcrumbs over isolated fixed physical-line source chunks;
3. Python AST-derived ownership boundaries with the same breadcrumb vocabulary.

The experiment covers selected repository source files only. It does not change file selection, repository size caps, Markdown/prose handling, embedding configuration, retrieval ranking, eval judgments, namespace policy, or product defaults.

## Behavior

### Stable arm identifiers, actual control, and isolation

The comparison would expose exactly these logical arm identifiers:

| Arm | Source treatment | Searchable breadcrumb line | Final split treatment |
|---|---|---|---|
| `current-default` | current `text.splitlines()` repository sections of 80 entries | none | current generic Markdown 300-token split plus up-to-two-sentence overlap |
| `fixed-80-python-breadcrumbs` | consecutive LF-coordinate physical lines `1-80`, `81-160`, ... | AST-derived symbol chains intersecting the range | none; each rendered source range is one final source chunk |
| `python-ast` | LF-coordinate AST ownership regions, subdivided to at most 80 physical lines | the owning symbol’s ancestor chain | none; each rendered source range is one final source chunk |

`current-default` MUST be an actual control, not the prior proposed no-overlap `fixed-80` approximation. For the same source commit, selected files, acquisition settings, and with metadata/card flags disabled, it MUST produce the same corpus pages, normalized documents, final chunks, chunk IDs, hashes, plan rows, and citations as the ordinary no-arm path before C5. An explicit control selector MAY be private, but selecting it cannot alter output. The eventual implementation MUST NOT create a public/default product profile in C5.

The two Python-aware arms are isolated experimental treatments. They MUST NOT pass their source sections through the current generic token/sentence splitter and MUST NOT combine with each other or with the completed metadata treatment. Across all three comparison arms, no `Search metadata`, path tokens, file stem, file-wide symbol list, symbol-token list, file-card page, or oversize-file-card page may be added. Selecting any logical comparison arm together with `--repo-search-metadata`, `--repo-file-cards`, or `--repo-oversize-file-cards` MUST fail before corpus generation with a user-facing incompatibility error rather than combine treatments silently.

The ordinary no-arm path and the existing metadata/card flags MUST keep their current behavior and output. Comparison-arm incompatibility does not deprecate or alter those existing options.

This control satisfies the parent rule that every index-changing comparison use paired current promoted defaults on the same source commit/corpus: C6 MUST pair each Python-aware treatment against `current-default`. Neither Python-aware treatment may stand in as the parent-required default baseline.

### LF-coordinate physical lines

The Python-aware arms MUST use AST-aligned physical lines defined only by LF (`"\n"`) boundaries after the repository’s existing universal-newline text acquisition has normalized CRLF/CR terminators to LF. Define the ordered physical-line vector as `source.split("\n")`, except that an empty source has zero physical lines and the one terminal empty element produced when `source.endswith("\n")` is discarded. Consecutive LFs still create numbered blank physical lines. A terminal LF is a terminator, not an additional line. Text inside each vector element, including form-feed and other non-newline characters, MUST remain unchanged. A bare carriage return remaining after acquisition violates the coordinate invariant and MUST fail planning rather than be interpreted differently by the parser and coverage logic.

Coordinates are one-based vector indexes. Equivalently, a character’s row is one plus the number of preceding LF characters. On the required normalized input this is the row model used by Python `ast` and `tokenize`: form-feed (`"\f"`) is whitespace within one physical line and MUST NOT create a new line or increment a citation. The current-default control intentionally retains the current `text.splitlines()` behavior; the LF-coordinate definition governs only the two isolated Python-aware arms and their coverage validation.

### Python parse and decorator contract

Only a file whose current repository language classification is `python` is eligible for breadcrumb or AST treatment.

Eligible content MUST be parsed with the standard library equivalent of:

```python
ast.parse(source, filename=repo_path, mode="exec", type_comments=True, feature_version=(3, 11))
```

Only `ast.ClassDef`, `ast.FunctionDef`, and `ast.AsyncFunctionDef` are symbol nodes. Lambdas, comprehensions, assignments, imports, module docstrings, and control-flow nodes are not symbol nodes. A missing or invalid required position is an invariant failure, not a guessed boundary.

The same source MUST also be tokenized with standard-library `tokenize` so physical decorator ownership comes from token coordinates rather than assuming that a decorator expression’s AST `lineno` identifies its `@` line. For each decorated symbol:

1. find the symbol’s definition-keyword token and its indentation column;
2. immediately before that definition, collect the consecutive decorator logical statements at the same indentation, allowing only comment/blank `NL` trivia between them and the definition;
3. a decorator logical statement begins only when OP token `@` is its first non-trivia token; an `@` later inside the decorator expression (for example matrix multiplication) is not an introducer;
4. pair those introducer `@` tokens in lexical order with `decorator_list`, requiring equal counts; and
5. define each decorator’s physical span as every LF-coordinate row from the introducer token’s `start[0]` through the logical statement’s terminating `NEWLINE` token row, inclusive.

The symbol’s inclusive effective source span begins at the first paired introducer `@` row when decorators exist, otherwise at the definition node’s `lineno`; it ends at the definition node’s `end_lineno`. Ownership is by whole physical rows, so all rows of a multiline decorator—including an `@` row when its AST expression begins on a later row, continuation rows, final-row comments, and trivia between consecutive decorators and the definition—belong with the decorated symbol. Any token/AST count or coordinate inconsistency MUST fail local planning; it MUST NOT shorten the decorator span or silently fall back.

A symbol chain consists only of unqualified symbol names from outermost to innermost, joined with ` > `. It does not include the repository path, file stem, derived module path, symbol kind, arguments, bases, decorators, or global symbol inventory. Examples are `Client` and `Client > request > decode`.

### Fixed-window breadcrumb arm

For each `fixed-80-python-breadcrumbs` physical-line range, include every distinct symbol chain whose effective span intersects at least one physical line in that range. Chains MUST be ordered by `(effective_start, effective_end, lexical AST order)` and de-duplicated without truncation. This includes a containing long symbol when a fixed range begins in its body and nested chains whose definitions intersect the range.

When at least one chain exists, emit exactly one searchable line before the source payload:

```text
Symbol breadcrumbs: <chain-1>; <chain-2>; ...
```

A range with no intersecting symbol emits no breadcrumb line. Breadcrumb text is generated context, not a physical source line, and is excluded from source-coverage accounting.

### AST ownership and boundary arm

The AST arm MUST assign every physical source line to exactly one initial owner:

1. among symbol effective spans containing the line, the lexically innermost symbol owns it;
2. if no symbol contains it, the synthetic module owner owns it.

Nested definitions are therefore carved out of their parent: the nested symbol owns its complete decorator-through-`end_lineno` range, while the parent owns its signature and body lines outside nested-symbol spans. Top-level imports, assignments, expressions, module docstrings, and other module statements are module-owned. Statements inside a symbol remain owned by the innermost containing symbol.

Comments and blank lines inside a symbol’s effective span have that symbol owner. Outside every symbol, a physical line is trivia exactly when `line.strip()` is empty or `line.lstrip().startswith("#")`. Each maximal consecutive trivia run MUST be reassigned to the owner of the nearest later non-trivia line; if no later non-trivia line exists, it MUST be reassigned to the owner of the nearest earlier non-trivia line. An all-trivia file remains one module-owned region. Form-feed participates only as whitespace in these tests; it never creates a physical line. This exact forward-except-at-EOF rule prevents trivia-only chunks without guessing comment intent.

After trivia reassignment, maximal contiguous ranges with the same owner are ownership regions. A parent may consequently have multiple regions around nested children. Module-owned ranges have no breadcrumb. Symbol-owned ranges emit exactly one `Symbol breadcrumbs: <outer > ... > owner>` line.

### Deterministic subdivision

Every Python-aware fixed range and AST ownership region MUST contain at most 80 LF-coordinate physical source lines. A longer ownership region MUST be subdivided from its first line into consecutive ranges of 80 lines, with a final shorter range when needed. Subdivision MUST have zero source-line overlap and MUST NOT search for a prettier statement, token, sentence, or blank-line break.

Each subdivided range retains the same owning breadcrumb chain. There is no generic token-based or sentence-based second subdivision and no content overlap for Python-aware final source chunks. A physical line longer than the downstream token target remains one intact source line; no treatment behavior may split, normalize, truncate, or duplicate it silently. If the existing plan path cannot carry such a chunk safely, planning MUST fail clearly rather than weaken coverage.

The 80-line maximum is a physical-source-line bound, not a promise that every chunk fits an embedding model’s token limit. C5 is local-only; any later model/write resource bound belongs to C6’s separately approved plan.

### Mandatory common repository header chunk

Every selected code file in every comparison arm MUST produce exactly one identical non-source header final chunk before any source final chunks. It preserves the current common repository page header section:

```text
Repository file: `<repo_path>`
Language: `<current language classification>`
```

Its `section_path` MUST be the current cleaned H1 repository path, its canonical URL and document metadata MUST match the source file, and it MUST contain no source payload, breadcrumb, search-metadata preamble, or `Lines S-E` component. Within current repository path limits this existing section is one generic final chunk in `current-default`; C5 MUST assert that invariant and directly emit the same one chunk in each Python-aware arm. If exact one-chunk parity cannot be maintained, planning MUST fail rather than split, drop, or enrich the header.

The header final chunk is part of per-arm final chunk/row counts, hashing, storage forecasts, and paired-plan comparison. It is excluded from physical-source-range ordering, reconstruction, source-line counts, symbol-boundary metrics, fallback coverage, and line-citation integrity checks. Header equality MUST be compared independently across the three arms.

### Source final chunks, coverage, and citations

A **final chunk** is the chunk/plan row after all splitting applicable to its arm. Header chunks and source chunks are distinct final-chunk kinds for validation even if the current row schema does not yet expose a public kind field.

For every selected nonempty source file in either Python-aware arm:

- each final source chunk MUST represent one nonempty contiguous inclusive LF-coordinate range `[start, end]`;
- ranges sorted by `start` MUST begin at line 1, end at the last numbered physical line, be adjacent (`next.start == previous.end + 1`), and never overlap;
- concatenating the unchanged physical-line payload vectors in range order MUST equal the LF-coordinate physical-line vector exactly;
- generated breadcrumb and common header text MUST be structurally distinguishable from and excluded from source reconstruction; and
- no downstream generic split or sentence overlap may duplicate, normalize, or omit source payload.

Each Python-aware final source chunk MUST use `Lines <start>-<end>` as the final `section_path` component and retain the existing immutable GitHub blob URL as `canonical_url`. No `#Lx-Ly` URL fragment is proposed because the current page/manifest boundary owns one canonical URL per source file. Every Python-aware line-range citation MUST describe exactly the source payload carried by that final chunk.

For `current-default`, validation instead MUST prove exact parity with the pre-C5 pipeline at two boundaries: rendered 80-entry repository sections and final generic Markdown chunks. Its final source chunks MUST preserve the exact existing `section_path` emitted by generic Markdown parsing, splitting, and overlap. That path MAY retain the originating `Lines S-E` component, but embedded Markdown-like headings in code or fixtures MAY replace it, leaving no parseable line-range component. Control validation MUST NOT require, synthesize, or restore a line range where the ordinary path emits none. Control rows MUST NOT be reported as exact payload-level line citations, and final-chunk reconstruction/nonoverlap assertions MUST NOT be falsely applied to them. The mandatory non-source header remains excluded from both control section coverage and treatment source coverage.

### Fallback

For Python `SyntaxError` or `ValueError`, both Python-aware arms MUST fall back for the entire file to isolated LF-coordinate fixed 80-line final source chunks: zero breadcrumbs, no generic token/overlap split, exact treatment coverage/citations, and no partial AST result. The plan summary MUST count the file as a Python parse fallback without exposing source content in the error summary.

For every non-Python code language, both Python-aware arms MUST deterministically use the same isolated LF-coordinate fixed/no-breadcrumb treatment and count the file as a non-Python fallback. Markdown and prose files retain their existing non-code path and are not counted as syntax fallbacks.

Unexpected parser, tokenizer, coordinate, or runtime failures other than the stated `SyntaxError`/`ValueError` parse fallback MUST fail local planning; they MUST NOT silently downgrade. Fallback does not enable the existing regex metadata scanner. `current-default` never parses Python and therefore records no syntax fallback.

### Defaults, locality, and side effects

With no comparison arm selected, generated corpus pages, normalized documents, plan rows, hashes, citations, generic split/overlap behavior, and existing metadata/card behavior MUST remain unchanged.

C5 implementation and validation, if later activated, MUST be local-only. It MUST NOT load embedding models, read service credentials, call GitHub beyond the already-selected local acquisition flow, contact turbopuffer or another live retrieval service, create/write/delete a namespace, update catalog/applied state, change datasets or labels, or promote an arm.

No Tree-sitter package, parser grammar, model, or other dependency may be added. Standard-library `ast` and `tokenize` are the only proposed syntax machinery.

## Acceptance scenarios

1. **Actual control and paired isolation:** Golden pre-C5 fixtures prove `current-default` and the ordinary no-arm path have identical rendered pages and final generic token/overlap chunks; each Python-aware treatment is paired against that control on the same source commit/corpus and rejects metadata/card combinations.
2. **Three-arm distinction:** One parseable Python fixture produces the current generic final split in `current-default`, isolated fixed ranges plus AST chains in `fixed-80-python-breadcrumbs`, and AST ownership ranges plus the same chain vocabulary in `python-ast`.
3. **LF coordinates and coverage:** An acquisition-normalized CRLF fixture containing form-feed, blank LF lines, module statements, nested symbols, and a final line without LF proves form-feed is intra-line whitespace and reconstructs the exact LF physical-line vector from each Python-aware arm; a post-acquisition bare CR fails the coordinate invariant.
4. **Decorators and nesting:** Fixtures with multiple decorators, `@` on a row whose AST expression starts later, multiline calls, an expression-internal `@`, sync/async definitions, and nested definitions prove introducer-token matching, complete physical decorator ownership, ancestor chains, and no parent duplication.
5. **Long symbol and trivia:** A 161-line ownership region yields `80/80/1`; leading, interstitial, nested, and trailing comment/blank-only runs follow the next-region/last-region rule without a trivia-only chunk.
6. **Header and citation integrity:** Every arm emits one identical first non-source header final chunk included in row counts but excluded from coverage. Every Python-aware source chunk’s `Lines S-E` equals its exact payload and unchanged blob URL; control citations are validated only for exact existing generic-pipeline parity and may lack a parseable line range.
7. **Fallback:** Malformed Python falls back wholly to isolated LF fixed/no-breadcrumb chunks with one sanitized parse-fallback count; representative non-Python source uses the same treatment and count; Markdown/prose remains unchanged; unexpected tokenizer/coordinate failures stop.
8. **Compatibility:** No-arm output and existing `--repo-search-metadata`/card output match pre-change fixtures, including current generic split and overlap; comparison selectors reject incompatible flags before corpus generation.
9. **Runtime and CI parity:** Focused syntax fixtures plus the full suite run in the existing required CI matrix on CPython 3.11 and 3.13 and produce identical boundaries, breadcrumbs, headers, fallback counts, and citations. A one-runtime local pass is insufficient closure evidence.
10. **Safety:** Local plan/preflight validation proves zero embeddings, credentials, remote retrieval calls, writes, deletes, catalog/default mutations, and live apply.

## Explicit exclusions

- Tree-sitter, multilingual syntax parsing, or dependency changes.
- Path-token/global-symbol preambles or metadata/file-card ablations.
- Token-overlap tuning, semantic splitting, retrieval/ranking changes, or model evaluation.
- Live retrieval, namespace writes/deletes, catalog/applied-state changes, dataset/label changes, or promotion.
- A public/default chunking profile or automatic language selector beyond deterministic fallback.
- Repairing current-default `splitlines()` coordinates, synthesizing missing control line ranges, or changing its existing section-path behavior inside C5/C6.

## Ratified exact checkpoint

The user confirmed the complete contract above by ratifying all seven reviewed items below exactly as written:

1. **Arms, actual control, and pairing:** Confirm exactly `current-default`, `fixed-80-python-breadcrumbs`, and `python-ast`; the control is the unchanged current 80-entry renderer followed by generic 300-token/up-to-two-sentence-overlap splitting; each isolated Python-aware arm is paired against it on the same commit/corpus and rejects metadata/card combinations.
2. **Physical lines, AST, and decorators:** Confirm LF-only one-based coordinates after existing universal-newline acquisition (terminal LF adds no line; form-feed is intra-line whitespace; post-acquisition bare CR fails), Python 3.11 grammar via standard-library `ast`, only class/sync-function/async-function symbols, and standard-library `tokenize` first-token `@` coordinates owning complete physical multiline decorator spans.
3. **Breadcrumbs and ownership:** Confirm name-only outer-to-inner chains, all intersecting chains on fixed physical windows, innermost-symbol/module ownership, nested source carved out of parents, and outside-symbol comment/blank-only runs attached forward (or backward only at EOF).
4. **Treatment subdivision and final chunks:** Confirm isolated Python-aware final chunks have a hard maximum of 80 physical source lines, deterministic `80/80/.../remainder` subdivision, zero overlap, no generic token/sentence split, and fail-closed handling when an intact line/range cannot be planned safely.
5. **Common header, coverage, and citations:** Confirm exactly one identical `Repository file`/`Language` non-source header final chunk in every arm, included in row/storage counts but excluded from source coverage; exact LF-vector reconstruction and payload-accurate `Lines S-E`/unchanged-blob citations apply to Python-aware final source chunks, while current-default preserves exact existing generic-pipeline citation output—including rows without a parseable line range—and is validated for exact pre-C5 parity.
6. **Fallback:** Confirm whole-file isolated LF fixed/no-breadcrumb fallback for Python `SyntaxError`/`ValueError`, the same treatment for non-Python source, sanitized fallback counts, no control parsing/fallback count, and fail-closed behavior for unexpected tokenizer/coordinate/runtime failures.
7. **Compatibility, validation, and safety:** Confirm no-arm and existing metadata/card outputs stay unchanged; focused plus full validation is required in CI on CPython 3.11 and 3.13; and C5 remains dependency-free/local-only with no model load, credential read, live call, write, delete, state, dataset, default, or product change.

Original ratification provenance is recorded in `.10x/evidence/2026-07-20-python-syntax-chunking-contract-ratification.md`; citation-correction ratification and supersession rationale are recorded in `.10x/evidence/2026-07-20-python-syntax-citation-correction-ratification.md`; independent review history is recorded in `.10x/reviews/2026-07-20-python-syntax-chunking-contract-review.md`. Any future semantic correction requires this active specification to be superseded rather than edited in place.

## References

- `.10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md`
- `.10x/tickets/done/2026-07-19-implement-opt-in-python-syntax-chunking.md`
- `.10x/tickets/2026-07-19-evaluate-python-syntax-chunking.md`
- `.10x/evidence/2026-07-20-python-syntax-chunking-contract-ratification.md`
- `.10x/evidence/2026-07-20-python-syntax-citation-correction-ratification.md`
- `.10x/specs/superseded/repo-python-syntax-chunking-experiment-originating-citation.md`
- `.10x/reviews/2026-07-20-python-syntax-chunking-contract-review.md`
- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/research/2026-06-28-repo-search-precision-state-of-art.md`
- `.10x/research/2026-06-28-expanded-validation-ranking-hypotheses.md`
- `.10x/tickets/done/2026-06-28-repo-searchable-path-symbol-metadata.md`
- `src/buoy_search/github_repo.py`
- `src/buoy_search/chunker.py`
- `src/buoy_search/plan_artifacts.py`
- `tests/indexing/test_github_repo.py`
- `tests/indexing/test_chunker.py`
- `.github/workflows/ci.yml`
