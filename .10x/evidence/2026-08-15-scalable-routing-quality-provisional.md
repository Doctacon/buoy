Status: recorded
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-implement-scalable-routing-quality.md

# Scalable Routing Quality Provisional Evidence

## Recorded state

- Branch: `work/scalable-routing-quality`.
- Source, tests, and the collect-only packaged calibration are implemented in
  the task worktree. Four explicitly authorized test content namespaces and
  their schema-v1 cards were created as recorded below. No existing corpus,
  shared catalog schema, credential, release, or publication was changed.
- The selected representation is one zero-to-eight `routing_examples` array
  plus a separately hashed, ordinary non-ANN prototype vector on the existing
  card row. The legacy ANN vector remains the unchanged base-card authority.
  Prototype rows, aliases/tags encoding, a second catalog namespace, and
  late-interaction vectors were rejected.
- Production remains exact `buoy-routing-catalog-v1`, one card per live
  content namespace, and no more than three selected content namespaces.
- No proposed-card overlay, duplicate card file, or second routing authority
  exists in the repository.

## Authorized real-corpus test preparation

The owner explicitly authorized creation of new corpora for feature testing.
Four small fictional manuals were prepared outside the repository as two
confusable pairs: OrbitStock/OrbitWatch and FleetDeck/FleetShield. Exact local
plans target namespaces `routing-test-orbitstock-v1`,
`routing-test-orbitwatch-v1`, `routing-test-fleetdeck-v1`, and
`routing-test-fleetshield-v1`.

The four plans contain one source document and four chunks each. Their plan
IDs are `plan_da4c396651a57537`, `plan_e13db0a262accd14`,
`plan_88c86dc35eea59b6`, and `plan_b1c0ee0bb5a19fc0`. Thirty-five candidate
route canaries now cover the four fixtures plus RentPTR, WhiteboxGeo, and
Salesforce. With the approved legacy-50 projection, all seven packs load as an
85-case suite with SHA-256
`220b693d9e0322ff3d19c6734a49543c0d8294114334c5ebde8be6cf83c0a5ad`.
The current three-pack subset for the seven presently eligible real corpora
loads as 65 cases with SHA-256
`d77e03c447dee4aa38bc7b7b5e0c03cbd9f635762c182890d476cae49f29be4f`.
Planning reported zero source/provider API calls. The source fixtures,
candidate canaries, and four applied-state receipts live under
`/private/tmp/buoy-routing-test-corpora`; the successfully consumed plan
artifacts were not retained. No test source or card overlay was added to the
repository.

The three current-real-corpus pack hashes are RentPTR
`04b382e61448b587d7b6276a69067c7c67641c2105d45f98514bdda29664f123`,
WhiteboxGeo
`a73e38f527e6a428a5210f8af25e68464a6bc7ec8d833ccb601eb7a3a222e032`,
and Salesforce
`15a087c94cfdb0b0758f251c0748d4a3fe0566c9954408d443680947e223af9a`.
RentPTR reuses exact owner-approved questions `u21-rentptr-purpose` and
`u22-rentptr-telematics`; WhiteboxGeo reuses exact owner-approved questions
`u23-whiteboxgeo-purpose` and `u24-whiteboxgeo-interfaces`. Their other three
questions per pack and all five Salesforce questions are new and remain
candidate ground truth. A strong live catalog validation of the current
three-pack suite covered all seven eligible cards at the same snapshot and
produced catalog projection
`d8f8c814ef4f13b512843e15aa058b45434b4997a4b648b04c17f571158a1525`.

The owner then directed the work to use real new corpora. Each reviewed plan
was applied with exactly four rows and registered through Buoy's ordinary
schema-v1 workflow. Each generated card was immediately disabled and replaced
by a complete manual, still-disabled card. The public apply workflow therefore
created a brief eligible window before each immediate disable; no automatic
retrieval was run in those intervals. Final strong readback at catalog
snapshot `793f6844d7141959b43a5f03c33dbbd7b657d4ff186c622ac0ee1635be9217f7`
recorded:

- `routing-test-orbitstock-v1`, apply
  `apply_20260815T163503.117889Z0000_plan_da4c396651a57537`, card revision
  `132fdfced513e80671ec6b4c40048ca54b3854149a9808c16db183180216109b`;
- `routing-test-orbitwatch-v1`, apply
  `apply_20260815T163704.411853Z0000_plan_e13db0a262accd14`, card revision
  `e009324f6a8d8e4c073be5cf379d1318c3136cd61e001401372a8dff5ea08049`;
- `routing-test-fleetdeck-v1`, apply
  `apply_20260815T163829.973854Z0000_plan_88c86dc35eea59b6`, card revision
  `5d91be183324820cd544681096895e8e26af559c4e116362f74a9a198f361e09`;
- `routing-test-fleetshield-v1`, apply
  `apply_20260815T163952.911089Z0000_plan_b1c0ee0bb5a19fc0`, card revision
  `f118fe4959e2a46a28eb5d04e5d109380a63deff9e57ed8f18e87d74e8e18ec4`.

All four cards report `target_status=live`, `catalog_status=disabled`,
`enabled=false`, and `semantic_origin=manual`. The final inventory contains
twelve live content namespaces, twelve cards, seven eligible cards, and five
disabled cards, with zero missing, stale, or incompatible entries. Four
read-only explicit retrieval smokes returned one intended hit each. No
content delete, existing-namespace write, shared-schema write, prototype-field
write, credential change, or model download occurred.

## Baseline and limits

The approved automatic multi-corpus implementation recorded route Recall@3
`57/58 = 0.9827586`, complete multi-corpus route coverage `10/10`, zero
incorrect high-confidence singleton routes, average fanout `1.98`, and maximum
fanout `3`. Those results qualify the current bounded router; they do not
validate the proposed prototype projection, exact local shortlist, MiniLM route
reranking, or new confidence thresholds.

The current generated website summary contains source identity but little
capability information. The present verified plan has no trustworthy
capability summary from which to invent examples. The new contract therefore
lets operators provide specific reviewed examples; automatic apply preserves
them and otherwise leaves the list empty.

Official provider documentation states that a new attribute may be added to
an existing namespace and is null for existing documents, while attribute type
changes and deletions are not in-place. That provider capability does not make
the change rolling-compatible with Buoy's current binaries: the current exact
schema validator rejects an added field. The recorded migration is therefore
reader-first and separately approved rather than an implementation side
effect.

## Implementation validation

- Focused catalog, remote-catalog, apply-registration, automatic-routing,
  routing-quality, runner, and release-inventory suites passed 154/154 on
  Python 3.11 and 154/154 on Python 3.13.
- Full repository discovery passed 745/745 on Python 3.11 and 745/745 on
  Python 3.13 with the socket/cache fixtures allowed to run.
- Locked-dependency validation, source-release validation, Python compilation,
  `git diff --check`, and the trailing-whitespace audit passed.
- A live read-only strong catalog smoke through the new reader accepted the
  current exact schema-v1 snapshot `793f6844d7141959b43a5f03c33dbbd7b657d4ff186c622ac0ee1635be9217f7`,
  returned the same four disabled test cards and seven eligible production
  cards, and recorded zero writes.
- The route-only runner and packaged collect artifact passed their dedicated
  30-test suite. The runner reads one authoritative catalog snapshot, performs
  one real BGE query inference and one bounded MiniLM call per case, creates
  no content resource, issues no content query, exposes no write method, and
  emits no question, routing example, vector, credential, or provider payload.
- Distribution validation built diagnostic version
  `0.4.1.dev136+g7da055fa0.d20260815`, producing a 66-file wheel with SHA-256
  `985a42f0cfd3c1354f8c6f2b8e6069c5a6550ebff986fca3ea58435187f86023`
  and a 135-file source distribution with SHA-256
  `1cbe156f7ecc92f13ffd6930575da5f39bd4bf591295c444033b7773be59b38e`.
  Publication remained paused.
- A clean Python 3.13 environment installed 104 packages from the built wheel.
  Version/import/help passed, the installed catalog help exposed the bounded
  repeatable `--routing-example`, and the installed packaged artifact loaded
  as `mode=collect`, `owner_approved=false`, with null thresholds. The source
  distribution contains the route-only evaluator and both focused tests; the
  wheel contains the routing-quality module and calibration data.

## Provisional activation state

- No route-canary dataset or judgment is approved for this work.
- No calibration/certification split has been frozen.
- No MiniLM score or margin threshold has been selected or approved.
- The required initial artifact is collect-only, owner-unapproved, and has
  null thresholds. It cannot change ordinary automatic routing.
- No schema-v2 migration is authorized. The pre-existing live card rows and
  shared schema remain untouched; only the four new schema-v1 test cards were
  added and updated.
- The current hard-coded BGE confidence behavior remains production authority
  until a later reviewed activation satisfies the complete specification.

## Required next evidence

Implementation evidence must demonstrate exact schema-v1/v2 compatibility,
legacy hash/vector preservation, bounded example projection, an exact local
top-twelve shortlist with no added provider call, deterministic MiniLM
max-prototype scoring, unchanged exact-name behavior, maximum fanout three,
and zero provider writes from the candidate route/evaluator path. The separate
authorized test-corpus effects are accounted above.

Activation evidence must additionally bind human-approved held-out per-corpus
canaries, calibration and locked certification digests, passing per-corpus and
aggregate gates, a clean source commit, exact model/artifact contracts,
read-only call accounting, distribution validation, and independent review.
Only an explicit owner-approved active artifact may lift the pause.

Migration evidence is later and separate. It must bind an exact stable v1
snapshot, approved additive schema write, conditional card backfill, two strong
v2 readbacks, and proof that no content namespace or row changed. Its safe
sequence is compatible-reader deployment, schema-v2 migration/backfill,
reviewed example writes, read-only candidate evidence, then separate
activation; it is not circularly conditioned on evidence that v1 cannot
produce.

## External effects

The exact four test namespaces above were created with sixteen total content
rows. Their generated catalog cards were disabled and updated to the reviewed
manual semantics. They are recoverable only through an explicit future
provider deletion, which this task does not authorize or perform. Ordinary
automatic routing ignores them because all four cards are disabled. Existing
content namespaces and cards were outside every mutation target.
