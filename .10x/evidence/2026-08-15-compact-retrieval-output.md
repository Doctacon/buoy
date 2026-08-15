Status: recorded
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-compact-retrieval-output.md

# Compact Retrieval Output Evidence

## Frozen documentation baseline

This presentation task began from `origin/develop` commit
`7569143aaa62836ee00ecf91b5bf26515d18f944` and tree
`9fc8fe3ea69f960bb61e548f94a637976252bfae`.

At that baseline, live text was diagnostic-first: it printed retrieval/fusion
headers, effective embedding precision, per-hit corpus, URL, optional section,
path, ordered tags, score dictionaries, and a content preview. The renderer did
not offer `--explain`. Baseline `src/buoy_search/cli.py` SHA-256 was
`e40b1dc264a26a5d9b746e91c32a7253e4840d36410248f3590cc618ea116f8f`.

The product request is to make passages and citations primary without changing
the retrieval result. It explicitly retains current routing, ranking,
per-corpus coverage promotion, evidence assessment, partial failures, JSON,
and provider calls. The stopped pure-global-ranking branch is not an evidence
or implementation source for those behaviors.

## Record-only shaping performed

- Added a presentation-only decision, executable specification, and bounded
  implementation ticket.
- Amended the active tag and embedding-precision contracts so compact text may
  omit those diagnostics while JSON, detailed plan output, and `--explain`
  retain their existing authority.
- Updated README, retrieval documentation, and the unreleased changelog to
  describe compact citation-first output, `--explain`, flag conflict, unchanged
  warnings/abstention, and the absence of answer synthesis.

No source, test, dependency, lockfile, routing card, content namespace,
provider, credential, evaluation dataset, ranking behavior, or release state
was changed in this shaping slice. No provider or model call was made.

## Implemented presentation boundary

The bounded implementation changes only:

- `src/buoy_search/cli.py` for `--explain`, the pre-environment flag-conflict
  gate, compact formatting, and renderer selection;
- new `src/buoy_search/model_progress.py` plus constructor-only wrappers in
  `catalog.py`, `chunker.py`, and `cross_encoder.py`; and
- focused presentation/progress tests in `test_cli.py`,
  `test_automatic_routing.py`, `test_multi_namespace_retrieval.py`,
  `test_catalog.py`, `test_chunker.py`, and new `test_model_progress.py`.

`retriever.py`, `routing.py`, `evidence.py`, `remote_catalog.py`, `config.py`,
the multi-corpus evaluator and collector, every evaluation dataset, and every
provider adapter are byte-unchanged from `origin/develop`. Presentation mode
is passed only to the renderer; it is absent from routing, retrieval, ranking,
evidence assessment, and serialized JSON.

Focused tests prove compact single, explicit multi, and automatic output;
citation fallbacks; title/content emptiness; whitespace collapse; word-safe
320-character truncation; pluralization; partial-failure redaction;
`assessment_failed`, abstention, inconclusive, and empty states; the exact
legacy explained multi/partial text; detailed plans; and model-progress state
restoration. A three-mode regression invokes the same explicit retriever with
compact, `--explain`, and `--json`, observes identical query/options, and proves
the JSON equals the exact original `to_dict()` payload with no presentation
field.

The `--json --explain` regression sets a removed legacy embedding environment
variable and makes every environment/runtime/provider seam fail if touched.
The command returns status 2, empty stdout, and only the flag-conflict error,
proving the conflict gate runs immediately after argument parsing and before
environment compatibility, credentials, configuration, models, catalog, or
provider work.

## Validation

- Focused suite: `131/131` passed on Python 3.11 and Python 3.13.
- Full suite after the final conflict-gate fix: `690/690` passed on Python 3.11
  and Python 3.13 with loopback and local uv-cache access enabled.
- Both Python versions compiled every changed source module and passed
  `scripts/release_automation.py validate-source`.
- Diagnostic distribution validation passed without publication. Wheel:
  `buoy_search-0.4.1.dev135+g7569143aa.d20260815-py3-none-any.whl`, 64 files,
  SHA-256
  `0e98acef07d5f6d13732b065be5fda3e379481a2cc692f3fd0b4b26d9b7a0264`.
  Source archive: 130 files, SHA-256
  `5113cf18d81aba20056fd6f8f9ed37930c02e78dd73f5b19f6a5ff95d4498c72`.
- A clean temporary Python 3.13 environment installed the wheel with all 104
  dependencies, imported the new module and CLI, exposed `--explain` in help,
  retained detailed explicit dry-run output, and returned only the conflict
  error under the hostile removed-variable smoke.
- A fresh installed-wheel routing-model construction completed from the pinned
  local cache with no raw weight-loading progress output and unchanged model
  type. No provider call or write occurred.
- `git diff --check` passes. Protected ranking/routing/evidence/evaluator/data
  paths have no diff from `origin/develop`.

The initial sandboxed full-suite attempts had exactly five unrelated local
loopback-bind denials and two unrelated uv-cache permission denials on each
Python version. The required unrestricted reruns above passed all 690 tests;
those sandbox failures are not product failures.

## Independent review and disposition

The independent review at
`.10x/reviews/2026-08-15-compact-retrieval-output-review.md` reproduced the
focused checks, verified the full-suite and distribution evidence, confirmed
the final wheel contains the reviewed source, and returned PASS with no
remaining blocker. It also verified that ranking, routing, per-corpus coverage,
evidence decisions, JSON, plans, and provider behavior remain unchanged.

This evidence is therefore recorded and the bounded presentation task is ready
for integration review. No provider mutation, task integration, release
publication, or production-state change has occurred, and the stopped
pure-global ranking policy remains excluded.
