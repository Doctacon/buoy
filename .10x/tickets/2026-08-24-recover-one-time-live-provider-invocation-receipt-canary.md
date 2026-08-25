Status: open
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: .10x/tickets/done/2026-08-24-validate-provider-invocation-receipt-integration.md
Activation: inactive
Decision: .10x/decisions/one-time-live-provider-invocation-receipt-canary-recovery.md
Authorization-Evidence: .10x/evidence/2026-08-24-provider-invocation-receipt-canary-recovery-authorization.md
Authorization-Review: .10x/reviews/2026-08-24-provider-invocation-receipt-canary-recovery-authorization-review.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Blocked-Predecessor: .10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md
Predecessor-Failure: .10x/evidence/2026-08-24-provider-invocation-receipt-canary-preflight-failure.md
Dependency-Evidence: .10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md
Dependency-Review: .10x/reviews/2026-08-24-provider-invocation-receipt-integration-review.md
Reviewed-Dependency: commit 0b27c4eaa2449493125f4040af3cd1f7c926b531, tree 9017c4a335938faca80cdded54545df8b79c12f8

# Recover One-Time Live Provider Invocation Receipt Canary

## Outcome

Make one fresh, forward-only candidate build/preflight attempt from the exact
reviewed receipt integration. Only after the complete preparation passes and an
independent reviewer records GO for its exact evidence and still-identical
candidate, run the same single automatic live retrieval authority that remained
unconsumed when the blocked predecessor stopped. Accept only one strict
canonical content-free receipt with catalog invocations at most 5 and content
invocations at most 18 while leaving model cache, telemetry filesystem,
provider write surfaces, global tools, repository refs, and unrelated state
unchanged.

## Scope and activation gate

This is a new recovery ticket, not a resumption of
`.10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md`.
The predecessor remains blocked and its failure evidence remains immutable. The
predecessor cannot build, validate, install, or run again. Its unconsumed one-
command authority is exclusively assigned here and is not duplicated.

This ticket is open and inactive. This records-only creation turn MUST NOT
activate it, build/export/install anything, inspect operational model/cache/
credential/telemetry state, access a provider or network, seek preparation GO,
or run a command. Before future preparation starts, independent review MUST
pass the exact recovery authorization records and a separate activation record
MUST bind their reviewed commit/tree. Activation authorizes only the one
preparation attempt; it is not live-command GO.

## Exact immutable dependency and identities

Preparation MUST use a mode-0700 owner-private root outside the repository and
an exact detached/no-ref-mutation export of reviewed source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`. It MUST reproduce these prebound
source/package identities before any candidate can be accepted:

| Identity | Exact value |
| --- | --- |
| `pyproject.toml` SHA-256 | `f80f4c53b5a6e1fe15e79abf31b40cdf529336a28144cec085ef1c7749861c22` |
| `uv.lock` SHA-256 | `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254` |
| `src/buoy_search/_provider_invocation_receipt.py` SHA-256 | `73361cde0ad7fad2906d01c10a7044f1a7ff34d28425e987f4265e7f60404349` |
| `src/buoy_search/retriever.py` SHA-256 | `89aeb5db61a1997f127db2ebe651beb9f184d4358e0e0cd3d98921713c9b613d` |
| `src/buoy_search/remote_catalog.py` SHA-256 | `3d859a21c257f7edaf113593aa486defdc78d1c89d45367811d0ac9ce991399d` |
| `src/buoy_search/cli.py` SHA-256 | `c6b575e160c5379b8a7214b3434a06d47864f0414e1478f44bcddeff313609ce` |
| routing artifact SHA-256 | `79c780a5c3ffebfe5569d463663c30d681cf224aec3ddfb1e03202641b97ed1e` |
| approved dataset SHA-256 | `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b` |

The frozen offline lock check MUST pass before the build. The one build MUST use
the exact reviewed source and locked/offline runtime and MUST be wheel-only. It
MUST reproduce all of these exact wheel identities:

- version and metadata exactly `0.5.2.dev87+g0b27c4eaa`;
- filename exactly
  `buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl`;
- size exactly 730602 bytes;
- exactly 78 unique, traversal-safe, regular/nonsymlink archive members;
- SHA-256 exactly
  `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`;
- sole console entry point exactly
  `buoy = buoy_search.entrypoint:main`; and
- source-to-wheel equality for the five production identities above, including
  exact routing artifact and CLI bytes.

## Exactly one build and corrected output inventory

The wheel build command may begin once only. Build start consumes the one fresh-
build authority even if uv, the wrapper, inspection, or later preparation
fails. There is no rebuild, build retry, corrected inspector rerun, alternate
output directory, alternate candidate, source change, or validation retry.

Wheel enumeration MUST be independent from complete directory enumeration:

1. enumerate regular nonsymlink `*.whl` entries and require exactly the one
   expected wheel;
2. validate that wheel directly against every exact identity above; and
3. enumerate every output-directory entry separately and allow no entry except
   that wheel and, if uv created it, exactly one regular nonsymlink expected
   uv-generated `.gitignore` marker.

The marker is not a distribution artifact and MUST NOT be counted as one. Any
second wheel, source distribution, directory, symlink, socket, unexpected
hidden file, or other entry fails permanently. The marker itself MUST be
validated as the expected uv-generated output marker rather than ignored by a
blanket hidden-file filter.

## Exact schema-v3 routing authority

The complete routing artifact hash above is mandatory. Validation MUST use the
already reviewed production `load_routing_confidence_calibration` and
`validate_routing_confidence_calibration` path from the exact source and again
from the isolated installed wheel. Existing reviewed package metadata, archive,
installed-package, help/import, strict receipt, and source-to-wheel procedures
from the done integration evidence MUST be reused where applicable. A new
partial routing or package parser MUST NOT decide acceptance. Standard-library
archive enumeration is permitted only for exact digest/member/path/hash checks
that the reviewed production/package validators do not expose.

The actual artifact paths and values are:

- top-level `/schema_version`: exact integer `3`;
- top-level `/calibration_revision`: exact string
  `active-anchor-e559a8aa-v1`;
- top-level `/bindings`: exact object below; and
- `/receipts/cli_module_sha256`: exact string
  `c6b575e160c5379b8a7214b3434a06d47864f0414e1478f44bcddeff313609ce`.

No `/revision`, `/bindings/revision`, `/receipts/revision`, or other invented
generic path is permitted. Hash equality plus strict production loading is
required; checking only the four named values is insufficient.

The full reviewed `/bindings` object is exactly:

```json
{
  "routing_model": "BAAI/bge-small-en-v1.5",
  "routing_model_revision": "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
  "routing_reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
  "routing_reranker_revision": "c5ee24cb16019beea0893ab7796b1df96625c6b8",
  "schema_contract": "remote-routing-card-schema-v1-v2",
  "projection": "separate_prototype_vector_normalized_mean_v1",
  "shortlist_limit": 12,
  "max_examples": 8,
  "feature_contract": "max_prototype_score_and_margin_v1",
  "score_field": "reranker_score",
  "margin_field": "reranker_margin",
  "canary_suite_sha256": "0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5",
  "catalog_projection_sha256": "e559a8aac5a4f7fb808f137b1c6a3710b6cd5b6764fc84f7f06120e33307ef7c",
  "certified_namespaces": [
    "site-dagster-io-v1",
    "site-developer-salesforce-com-v1",
    "site-oscilar-com-v1",
    "site-rentptr-com-v1",
    "site-turbopuffer-com-v1",
    "site-whiteboxgeo-com-v1",
    "site-www-thistle-co-v1"
  ],
  "certified_catalog_projection_sha256": "e559a8aac5a4f7fb808f137b1c6a3710b6cd5b6764fc84f7f06120e33307ef7c",
  "catalog_policy": "certified-exact-otherwise-provisional-v1"
}
```

## Isolated install and provider-free candidate gates

Install the exact digest-validated wheel only into one isolated temporary
runtime under the owner-private root, offline and without dependency drift.
Prove exact installed distribution/module version, sole entry point, complete
installed package manifest, five production source identities, routing artifact
hash, strict routing loader result, executable/module version and help, private
receipt import, and strict receipt encode/decode/validator behavior. Provider-
free preview/help/import checks MUST prove no provider, credential, model,
telemetry store, `.buoy`, or global-tool access. The installed candidate and its
dependencies MUST be the exact reviewed package state; no editable checkout or
ambient `PYTHONPATH` may satisfy an installed-package check.

There is no user/global install, uninstall, replacement, rollback, release,
deployment, publication, push, ref mutation, hosted operation, or invocation of
an installed global Buoy.

## Complete preparation ledger before GO

After candidate identity passes and still before provider/network access, bind
content-free pre-state:

- exact repository refs/worktrees and candidate/runtime/package identities;
- host/platform/architecture and unchanged production automatic device class;
- privately extracted exact approved case
  `m01-dagster-turbopuffer-quality` from
  `automatic-multi-corpus-retrieval-v1` at dataset SHA-256
  `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`,
  without retaining query, namespace, card, or content values;
- intended credential-source presence after inherited provider credentials are
  removed, without opening it during retained preflight output or exposing its
  value;
- exact model/cache root set, ref, assets, file types/targets/content, complete
  159-entry manifest, and historical manifest SHA-256
  `c395f5807452ede94efade87f5be77c0492911e6ac5936a85ce9aaf72ac4263f`;
- exact cached model `BAAI/bge-small-en-v1.5` revision
  `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, complete local assets, float32,
  unchanged production automatic-device behavior, and enforced offline/local-
  only/no-download controls;
- real telemetry root/store/queue/receipt/backup filesystem identities,
  including regular-file bytes/digests, modes, links, and targets, using only
  filesystem inspection and without opening the database or invoking any
  telemetry command/API; and
- process/external-side-effect baseline sufficient to reject an installer,
  telemetry writer/migration, provider write path, or surviving harness child.

The model cache/ref/assets MUST remain exact after candidate preparation, after
the command if GO is later issued, and after cleanup. Do not clear, repair,
evict, download, or force a device. Telemetry remains disabled. Do not open the
real store/database or invoke status, migrate, flush, writer, queue, receipt,
backup, export, or purge behavior.

## Preparation failure and independent GO

Any nonzero, mismatch, ambiguity, privacy gap, candidate drift, cache/ref/asset
mismatch, telemetry-filesystem uncertainty, credential-source absence, process
guard gap, or incomplete preparation evidence is `RECOVERY PREP FAIL`. It stops
this ticket permanently. Clean only owned temporary artifacts, record bounded
sanitized failure evidence, and do not rebuild, rerun a failed validator, alter
operational state, seek GO, or start the command.

On complete preparation PASS, commit bounded sanitized evidence while keeping
the exact accepted candidate/runtime owner-private and immutable. An independent
reviewer MUST inspect the exact evidence commit, both active receipt specs, this
ticket, the original decision/gates, blocked predecessor/failure, candidate and
routing identities, output-inventory correction, cache/store/credential/process
preflight, privacy, and no-unrelated-mutation state. The reviewer must record
one explicit `GO` or `NO-GO` tied to the exact evidence commit/tree and exact
candidate wheel hash.

Only exact GO permits the live phase. A general review PASS without the word GO,
qualified/stale GO, candidate/evidence drift, review finding, or inability to
retain/reprove the same accepted candidate is NO-GO. NO-GO cleans owned
temporary artifacts and ends without command or rebuild. The reviewer does not
rerun preparation or perform operational access.

## Exact one-command harness after GO

After exact GO, the private harness MUST:

1. reprove the accepted wheel/runtime hashes and prebound cache/telemetry
   filesystem identities without rebuilding or changing state;
2. remove inherited provider credentials and all telemetry enablement;
3. load the existing intended credential source only inside the private child,
   never into argv/stdout/stderr/records;
4. privately load the exact approved case/dataset above;
5. enter the underscore-prefixed private in-process receipt scope;
6. run the isolated candidate's ordinary automatic live command operation once
   against the current remote catalog and selected current content namespaces;
7. preserve the exact original return/exception/exit outcome outside the scope;
   and
8. after terminal scope exit, request receipt bytes once and pass the same
   immutable bytes to the reviewed strict validator.

Exactly one automatic command may begin. Command start consumes the sole live
authority. There is no preview, explicit retrieval, second command,
substitution, rerun, receipt-only rerun, provider retry, alternate case, or
candidate rebuild. Failure, interruption, ambiguity, process loss, missing
receipt, validation rejection, side-effect breach, or cleanup gap grants no
retry.

## Provider, model, telemetry, and network boundary

Network access is restricted to DNS/TLS/provider endpoints reached by the
unchanged automatic read path after every gate and GO. Application operations
are only current strong remote-catalog reads and selected content retrieval
reads. Provider/catalog/card/namespace/content create, update, upsert, delete,
repair, migration, management, and every other write path MUST remain excluded
by reviewed source identity and runtime guards where mechanically possible.
There is no remote telemetry export or model/network download.

The harness does not intercept transport or claim physical send identity.
SDK-internal retries, physical sends, provider billing, cost, and rate-limit
effects remain unknown. The receipt is application-boundary evidence only.

## Receipt and original-outcome acceptance

Only after the original operation is terminal, use the already reviewed strict
receipt decoder/validator. Require non-null bytes, schema version 1, unit
`provider_client_invocation`, exact keys/types/enums/counts/sums/order/grammar,
canonical compact sorted UTF-8 JSON, at most 65536 bytes, duplicate/unknown/
missing-key rejection, byte-identical decode/validate/re-encode, and the full
privacy contract from both active specifications.

Acceptance additionally requires:

- automatic catalog was begun and `catalog.invocation_count <= 5`;
- `content.invocation_count <= 18`;
- all begun catalog/content operations and attempts have accepted successful
  terminal structure with no `error` or `interrupted` outcome; and
- the original command outcome is known and recorded truthfully and separately.

The 5/18 gates are post-operation sanitized receipt gates, not pre-operation
kill switches or physical send/SDK retry/billing/cost/rate-limit claims. Missing,
incomplete, observer-failed, malformed, noncanonical, over-budget, error, or
interrupted receipt fails without inference. Source maxima, command success,
logical telemetry, output, or provider behavior cannot substitute. Receipt
failure MUST NOT replace, wrap, suppress, or relabel the original command
outcome.

## Post-state, privacy, retention, and cleanup

After the command or any terminal failure, prove the model cache/root/ref/full
159-entry manifest and real telemetry filesystem are byte/type/target-identical
to pre-state, without a telemetry DB open. Reconcile one command start, one
terminal/uncertain status, no surviving descendant, provider reads only, no
telemetry writer/migration/installer, no cache download/mutation, credential
source unchanged, no global/release/ref operation, and no unrelated mutation.

On PASS, retain indefinitely only one exact canonical validated receipt and
bounded content-free evidence: exact candidate/runtime/model/cache/store
identities, generic original command outcome, generic acceptance/cleanup
outcomes, family counts/outcomes, process/effect inventory, and review
references. On failure, retain no receipt or partial ledger.

After durable sanitized evidence exists, delete and verify absence of query,
argv, namespace/card/catalog/content/result values, credential material,
private paths, raw stdout/stderr/errors/stacks, temporary receipt copies,
harness/scripts, source, wheel, isolated runtime, raw logs, process samples,
path-bearing manifests, and analysis artifacts. Never print, persist, or place
the credential value in argv. In-memory private-literal scans emit only bounded
pass/fail counts. Cleanup touches only owned temporary artifacts.

## Acceptance criteria

- Recovery records pass independent review before one separately recorded
  preparation activation; this creation turn remains records-only/inactive.
- The blocked predecessor remains blocked, its failure evidence immutable, and
  no second live-command authority exists.
- Exactly one fresh wheel build from reviewed source commit/tree reproduces
  exact version, filename, 730602-byte size, 78-member inventory, SHA-256,
  entry point, source identities, and routing artifact; no rebuild/retry occurs.
- Wheel enumeration is independent of complete directory inventory; exactly one
  wheel and at most the one expected regular uv `.gitignore` marker exist, with
  no other entry.
- The reviewed production routing/package validators establish exact schema-v3
  authority, full artifact hash, actual top-level paths, complete bindings, and
  exact CLI receipt; no generic revision path or partial-parser acceptance is
  used.
- One isolated install passes installed identity and provider-free gates without
  global install/release/deployment/ref mutation.
- Exact current model cache/ref/assets, historical 159-entry digest, telemetry
  filesystem without DB open, credential-source presence/privacy, approved
  case/dataset, process guards, offline model/auto-device, and no-write boundary
  pass in complete sanitized preparation evidence.
- Any preparation failure stops permanently. A passing preparation receives an
  exact independent GO bound to evidence commit/tree and candidate hash before
  command start.
- After GO, exactly one automatic command starts through the private scope;
  start consumes authority and no retry/substitution/second command occurs.
- Original outcome remains truthful and separate; one canonical receipt passes
  both active specs, catalog <=5/content <=18, success-only and privacy gates.
- Cache and telemetry filesystem are exact pre/post, provider activity is read-
  only, no unrelated/global/release/ref mutation occurs, and raw cleanup is
  complete.
- Independent correctness/privacy/side-effect review passes exact final
  execution evidence before closure.

## Evidence expectations

Preparation evidence records exact activation/source/tree/wheel/output marker/
installed package/routing/runtime identities; command counts for build and each
non-retried validator; exact current cache/ref/assets and historical 159-entry
digest; telemetry filesystem identity without DB open; credential presence only;
approved case/dataset identity; process/effect guards; privacy scan; cleanup or
retained-root state; changed paths/diff/status; and explicit independent GO or
NO-GO. It contains no private values or paths.

If GO is issued, execution evidence additionally records the GO commit/tree and
candidate hash, exactly one command start/terminal ledger without argv/PID/time,
generic original outcome, exact canonical receipt and strict-validator verdict,
family counts/outcomes, cache/store pre/post equality, provider-read/no-write
inventory, cleanup absence, no-unrelated-mutation state, and independent final
review. It explicitly disclaims physical sends, SDK retries, billing, cost, and
rate-limit inference.

## Explicit exclusions

Resuming or unblocking the predecessor; more than one build; build/validator/
preflight retry; alternate source/wheel; more than one command; preview,
explicit, substituted, or retried retrieval; receipt-only rerun; partial routing
or package acceptance parser; generic revision path; public/CLI/env receipt
activation; automatic receipt persistence; telemetry-v2 or retention change;
telemetry command/store/database open/migration/flush/writer/purge; provider or
catalog/card/namespace/content write/repair/management; model download/cache
mutation/clearing/repair/forced device; credential output/persistence/mutation;
global install/uninstall/replacement; release/deployment/publication/push/ref or
hosted mutation; transport interception; wire/billing/cost/rate-limit claim;
unrelated cleanup; source/test/spec change.

## Blockers

Independent review of this records-only recovery authorization and a separate
preparation activation are required before the one preparation attempt. Live
execution is additionally blocked on a complete preparation PASS and exact
independent GO bound to its evidence commit/tree and still-identical candidate.

## Progress and notes

- 2026-08-24: Created as a new open/inactive recovery owner under exact current
  approval. The original ticket remains blocked and was not resumed. No source,
  test, specification, or immutable failure-evidence byte changed. No activation,
  source export, build, wheel, install, model/cache, credential, provider,
  network, telemetry/store/database, command, global-tool, release, deployment,
  publication, push, or ref mutation occurred in this records-only turn.
- 2026-08-24: Independent review passed exact recovery-authorization candidate
  commit `4ea0ff771f0d5559ecb04e32f105c76ed0d5148c`, tree
  `941360b413c28e5b6781c8e6abd60f4f50443ff3`, with no blocker. The records
  graph is recovery-activation-ready, but this ticket remains open/inactive
  pending a separate authorized activation record. This PASS did not activate
  preparation and is not the independent GO required after a future complete
  preparation PASS. No build, install, model/cache, credential, provider,
  network, telemetry/store/database, command, global-tool, release, deployment,
  publication, push, or ref mutation occurred in this review reconciliation.
