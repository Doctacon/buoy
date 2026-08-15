Status: pass
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-implement-scalable-routing-quality.md
Evidence: .10x/evidence/2026-08-15-scalable-routing-quality-provisional.md

# Scalable Routing Quality Review

## Scope and closure boundary

The independent review compared the complete task-worktree candidate with its
base and governing decision, specification, active ticket, and provisional
evidence. It covered exact schema-v1/v2 compatibility, legacy routing
preservation, bounded candidate routing and model calls, calibration authority,
the source-only route collector, test and packaging inventory, documentation,
and the actual provider-backed fixture effects.

This PASS closes only the bounded, inactive implementation review and permits
handoff to integration. The implementation ticket correctly remains
`Status: active`, and its evidence correctly remains provisional/recorded:
human approval, migration, calibration, certification, and activation are
future work. This review does not close those gates or claim that prototype
routing improves live quality.

## Findings closed during review

- The initial records incorrectly implied that the successfully consumed test
  plans remained available. The final evidence says precisely that the source
  fixtures, candidate canaries, and applied-state receipts remain outside the
  repository, while the consumed plans were not retained.
- The initial records omitted the brief eligible window created by the ordinary
  apply workflow before each test card was disabled. The final ticket and
  evidence disclose that window, state that no automatic retrieval ran during
  it, and bind the final disabled state to a strong catalog read.
- Initial canary material did not cover every currently eligible card. Strict
  candidate packs for RentPTR, WhiteboxGeo, and Salesforce now exist outside
  the repository. The 65-case current-real suite covers all seven eligible
  cards; the 85-case later-fixture suite additionally includes all four disabled
  test corpora. These new packs remain owner-unapproved and cannot support
  activation.
- The first governance sequence circularly required activation evidence before
  the schema capable of storing reviewed examples could exist. The final
  records establish the safe order: integrate and deploy the compatible
  reader; separately approve and perform an exact schema-v2 migration/backfill
  while legacy routing remains authoritative; write reviewed examples; collect
  and certify read-only evidence; then separately approve activation.

## Implementation, compatibility, and authority

- Production routing remains the existing legacy base-vector selector. The new
  prototype shortlist, local MiniLM route reranking, and calibrated confidence
  selector are candidate seams used by tests and the source-only evaluator;
  ordinary automatic retrieval does not call them. Exact title/alias behavior,
  the existing production card projection, and the maximum of three queried
  content namespaces are unchanged.
- The reader accepts only the exact 29-field schema-v1 row or exact schema v2,
  which adds the four-field prototype bundle. Existing v1 cards preserve their
  semantic hash, routing vector and hash, card revision, and serialization.
  Schema v2 stores the prototype vector as an ordinary non-ANN float array and
  reconstructs the bundle only when all four provider values are absent;
  partial bundles and every other row shape fail closed. Write paths preserve
  the observed schema version, and a v1 write with nonempty routing examples is
  rejected before mutation.
- Descriptor-free candidate routing takes an exact in-memory top-twelve
  shortlist from the already-read catalog snapshot. It adds no provider search
  or per-card request. Per case it performs one local BGE query inference and
  one bounded local MiniLM batch over at most twelve base passages plus eight
  examples per card, with deterministic maximum-score aggregation and ties.
  Disabled, stale, missing, and incompatible cards cannot enter the candidate
  route.
- The packaged calibration artifact is collect-only, owner-unapproved, and has
  null thresholds. Strict loading rejects malformed or unauthorized activation
  state, and no CLI or environment threshold override exists. It therefore
  cannot silently replace the current production selector.
- There is no proposed-card overlay, duplicate card inventory, prototype row,
  second catalog namespace, or second routing authority in the repository.
  The source-only collector receives one authoritative catalog snapshot and a
  fixed query, has no content-resource or write interface, issues no content
  query, and emits no questions, examples, passages, vectors, credentials, or
  provider payloads.

## External effects and readback

The separately authorized fixture setup did create real external state. It
applied sixteen total content rows across
`routing-test-orbitstock-v1`, `routing-test-orbitwatch-v1`,
`routing-test-fleetdeck-v1`, and `routing-test-fleetshield-v1`, then disabled
and replaced each generated card with reviewed manual schema-v1 semantics. The
review independently matched all four apply IDs and final card revisions to
the provisional evidence and inspected each local receipt: one apply run,
four active rows, four upserts, zero deletions, and zero retained-stale rows per
namespace.

The final strong read at snapshot
`793f6844d7141959b43a5f03c33dbbd7b657d4ff186c622ac0ee1635be9217f7`
reported twelve live namespaces and cards, seven eligible cards, five disabled
cards, and zero missing, stale, or incompatible entries. All four new cards are
live, manual, disabled, and `enabled=false`; four explicit read-only retrieval
smokes each returned an intended fixture hit. The compatible new reader
independently reproduced that inventory with zero writes.

Apart from those disclosed fixture content/card writes and their transient
eligible windows, the candidate made no existing-content-namespace write,
content deletion, shared-schema mutation, prototype-field write, credential
change, publication, or release. The fixtures and local candidate packs are not
repository overlays. Removing the provider-backed fixtures would require a
separately authorized future deletion.

## Validation

- The final focused suites passed `154/154` on Python 3.11 and `154/154` on
  Python 3.13. The independent reviewer reran the same focused suite in the
  settled worktree and observed `154/154` passing. The full suites passed
  `745/745` on both supported Python versions.
- The route-quality module, runner, and release-inventory regressions include
  thirty focused tests. Locked-dependency validation, source-release
  validation, compilation, trailing-whitespace checks, and `git diff --check`
  passed.
- The 65-case current-real suite has digest
  `d3577d32e848acfa648ba1f377ef2acd3045d57dc7af439373639e4c226abaed`
  and matched all seven eligible cards at the final snapshot, with catalog
  projection digest
  `d8f8c814ef4f13b512843e15aa058b45434b4997a4b648b04c17f571158a1525`.
  The later 85-case suite has digest
  `227c44671d65beac8b829604cae85e93efc61f7f284b7e0e700872e933a3f28e`.
  Loading and validation were read-only; all new ground truth remains candidate
  unless already inherited exactly from the previously approved basket.
- Distribution validation produced a 66-file wheel with SHA-256
  `985a42f0cfd3c1354f8c6f2b8e6069c5a6550ebff986fca3ea58435187f86023`
  and a 135-file source archive with SHA-256
  `1cbe156f7ecc92f13ffd6930575da5f39bd4bf591295c444033b7773be59b38e`.
  A clean Python 3.13 wheel install, imports, CLI help, routing-example option,
  and packaged collect-artifact load passed. The wheel contains the
  routing-quality module and calibration artifact; the source archive contains
  the source-only evaluator and its focused tests. Nothing was published.

## Post-implementation live baseline

The final source-only collector ran from exact clean commit
`100efc9242fbd90f16a9ee014feb23957b9c6e5b` and tree
`079b52a2b81cfc98612fd8c51c64cb8f76f24f9b`. Its content-free report at
`/private/tmp/buoy-routing-quality-current-100efc9.json` has SHA-256
`7b7da9b0bc53054f31cd695cfa82d86bb96abcbe82a0fc25cf8a784e663ac3b9`.
The run made 65 query-embedding calls, 65 bounded MiniLM calls over 455 total
base-card passages, and no content query, per-card provider query, model
download or write.

The exact shortlist contained all `67/67` required routes. Candidate top-three
Recall@3 was `65/67`, versus `63/67` for the legacy selector. That aggregate
improvement did not satisfy the frozen gate: the candidate fixed four misses
but introduced two different regressions, leaving Salesforce at `2/3` and
Oscilar at `8/9`. The strict per-corpus and no-regression checks therefore
failed. The collector also correctly failed owner-approval and active-artifact
checks, returned `collect_only`, and changed no production routing behavior.
Because every live card still had zero routing examples, this is a base-card
reranking baseline rather than evidence for the proposed example-enhanced
projection.

## Verdict and remaining gates

PASS for the bounded inactive implementation and integration handoff. The
candidate is exact-schema safe, preserves the production route, bounds its
provider/model work, keeps calibration under packaged owner authority, creates
no repository overlay, and gives the collector no content-write boundary. The
real fixture effects are fully disclosed and their final disabled state is
verified.

The post-implementation live baseline does not change this implementation
verdict, but it is an explicit quality STOP: the candidate selector must not be
activated from these results. Integration of the compatible inactive reader is
separable from, and does not imply approval of, routing activation.

The active ticket must remain open until all new canary judgments receive
explicit owner approval; the compatible reader is integrated and deployed;
an exact, drift-checked schema-v2 migration/backfill is separately authorized;
reviewed examples are written; live read-only calibration and locked
certification satisfy every end-to-end gate; the exact active artifact is bound
to its source and evidence and explicitly approved; and activation receives a
separate approval. This PASS authorizes none of those steps, no merge or
release, and no cleanup deletion of the external fixtures.
