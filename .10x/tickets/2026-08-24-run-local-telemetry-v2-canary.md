Status: active
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: .10x/tickets/done/2026-08-24-integrate-retrieve-command-telemetry-into-develop.md
Decision: .10x/decisions/one-time-local-telemetry-v2-canary.md
Authorization-Evidence: .10x/evidence/2026-08-24-local-telemetry-v2-canary-authorization.md
Specifications: .10x/specs/retrieve-command-telemetry.md, .10x/specs/local-telemetry-v2-storage-and-migration.md, .10x/specs/local-telemetry-writer.md

# Run Local Telemetry V2 Canary

## Outcome

Prove the exact integrated retrieve-command telemetry build can explicitly
migrate the owner's compatible real schema-v1 telemetry store and record four
bounded approved preview/live observations with distinct truthful command and
pipeline timing, while leaving the global tool and every remote state surface
unchanged.

## Scope

1. Revalidate the exact source, user-global tool baseline, approved dataset
   digest, real schema-v1/12-run/empty-queue telemetry snapshot, credential
   source presence, and absence of an active writer or migration.
2. Build exact
   `d3ae1ba272c9ce8999332dd04058116e8a5dda0f`/tree
   `38174e3d8167bbe4a7bd1afd3e1f16402ad8b7bc` into an owner-private temporary
   wheel and environment without changing the repository or global tool.
3. Verify the temporary candidate's package identity, entry point,
   dependencies, source hashes, version/help, and isolated-home telemetry
   status before it may access the real home.
4. Hash the exact closed v1 database, invoke the candidate's public migration
   once, and prove the immutable backup, schema-v2 store, preserved v1 views,
   permissions, and complete post-state without invoking migration again.
5. Run exactly the four approved forms bound by case IDs in the governing
   decision: preview and explicit-single `u01`, then explicit-multi and
   automatic `m01`. Use each exact form once, telemetry-local only, the intended
   credential source in a command-local subshell, enforced offline model
   settings, and no output persistence beyond private short-lived shape checks.
6. Flush the canary's accepted envelopes, wait for a terminal writer state, and
   query the database read-only for sanitized canary-window aggregates.
7. Validate privacy against the complete new telemetry artifact surface using
   the private literal inputs without placing those literals in evidence.
8. Remove the temporary environment and raw output, preserve the required v1
   backup, record bounded evidence/review, and reconcile this ticket honestly.

## Acceptance criteria

- The candidate wheel and installed package are bound to the exact integrated
  commit/tree, the three accepted production source SHA-256 identities remain
  exact, and the temporary CLI reports the expected exact-commit Hatch-VCS
  version.
- The global executable remains at its original path, uv-managed package,
  version, Python runtime, entry point, and package source identity throughout.
- Fresh pre-migration status exactly matches schema v1, 12 persisted runs, an
  empty queue, and no active writer/migration. Any drift stops before mutation.
- Migration exits zero once, retains a byte-identical immutable v1 backup,
  publishes a compatible schema-v2 database, preserves all 12 v1 rows and exact
  v1 view definitions/meaning, and leaves no unsafe or pending migration state.
- Exactly four v2 command observations are attributable to the bounded canary
  window: one explicit-single preview and three live observations in
  explicit-single, explicit-multi, and automatic modes.
- The preview has nonnegative command duration and null pipeline duration. Each
  successful live command has nonnegative command and pipeline durations, a
  source-reachable graph, truthful status, and command scope not narrower than
  its nested pipeline scope. Automatic fanout never exceeds three.
- All four commands exit zero. If any command fails, its truthful telemetry is
  still flushed and inspected, but this success criterion fails and no retry or
  repair occurs.
- Content provider access is bounded to at most six namespace query calls plus
  the automatic route's established catalog reads. No provider, catalog,
  namespace, content, credential, model-cache, or remote state write occurs.
- No model/network download occurs; required local model inference uses only
  already available pinned assets or stops before provider access.
- New telemetry artifacts contain no query, argv, namespace, credential,
  content, raw error, stack trace, URL, document/source identifier, or private
  path value. Evidence records only case IDs and content-free aggregates.
- The temporary executable environment and raw command outputs are removed.
  The immutable v1 backup remains. Repository source/workflows, `develop`,
  `main`, tags, Releases, global installed tools, and unrelated state are
  unchanged.
- Independent review returns PASS or every finding is resolved within this
  exact ticket. Acceptance maps to reproducible evidence with explicit limits.

## Evidence expectations

Record:

- exact commit/tree, artifact and installed-package digests;
- pre/post global-tool identity and repository/ref comparison;
- sanitized pre/post telemetry status and database/backup hashes, sizes,
  permissions, schema/view/row counts;
- per-mode content-free command outcome, command duration, nullable pipeline
  duration, fanout/failure counts, and stage names for only the canary window;
- bounded provider/catalog call accounting available from telemetry and source
  contract, with its limits;
- privacy scan verdict without literal private values;
- temporary cleanup proof; and
- commands by operation description rather than raw argv when argv would
  duplicate prohibited values.

Store no credential value, query text, argv, namespace value, content, raw
retrieval output, URL, raw error, stack trace, private path component, or
provider response body in repository records.

## Dependencies

- Exact integrated telemetry ticket and governing specifications listed above.
- Owner-approved dataset
  `src/buoy_search/data/automatic_multi_corpus_retrieval_evals.json` at SHA-256
  `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`.
- Existing intended credential source and already available local pinned model
  assets; neither may be created, downloaded, changed, or exposed by this
  ticket.

## Explicit exclusions

Global `buoy-search` install/replacement/uninstall/rollback; release, `main`,
tag, Release, publication, workflow, or branch-protection changes; provider or
catalog writes; card/catalog/content repair; namespace deletion; content
mutation; model download or cache change; credential retrieval/change; query
substitution; retries; backup deletion/replacement; telemetry purge/retention
policy; unrelated source, record, local-home, or GitHub changes.

## Side-effect inventory and provenance

- **Local state transition:** compatible closed telemetry schema v1 advances
  once to schema v2; user-ratified and specification-backed.
- **Retention:** exact v1 backup is retained indefinitely; user-ratified and
  specification-backed. No deletion or anonymization is authorized.
- **Eligibility/permissions:** only the owner-private current-user store and
  exact candidate executable are eligible; record-backed and user-ratified.
- **Recipients/cadence:** no telemetry recipient and no recurring operation;
  local-only one-time canary, user-ratified.
- **Failure/retry/escalation:** stop on drift, failure, or uncertainty; no retry
  or repair. Report to the owner in this workstream; user-ratified.
- **Cost/security/privacy:** at most six content namespace reads plus bounded
  catalog reads; no writes, downloads, credential persistence, or prohibited
  telemetry values. User-ratified and specification-backed.
- **Launch authority:** the owner's three-step current-workstream confirmation
  is recorded in the authorization evidence.
- **Operational owner:** repository owner; exact execution delegated under this
  ticket and independently reviewed before closure.

## Progress and notes

- 2026-08-24: Read-only preflight established the exact integrated candidate,
  divergent global-tool version identity, compatible real schema-v1/12-run
  store, empty queue, and credential-source presence without printing secrets.
- 2026-08-24: The owner confirmed the explained canary, then confirmed its
  bounded migration/provider effects, then confirmed the literal approved
  `u01`/`m01` workload forms. Governing decision and authorization evidence
  externalize the complete one-time contract.
- 2026-08-24: Activated before any real telemetry mutation or provider access.
  The worktree was clean on `work/local-telemetry-v2-canary` at records head
  `182e1c14`, whose parent is exact integrated source commit `d3ae1ba2`;
  `develop` and `origin/develop` were both exact `d3ae1ba2`. Repository
  instructions, this ticket, its governing decision and authorization evidence,
  all referenced specifications/decisions/evidence, and the Turbopuffer site
  RAG skill were read in full. Execution is bound to a detached owner-private
  candidate built from exact `d3ae1ba2`, never this records head. No real-home,
  provider, model, credential, installed-tool, or source mutation has occurred.

## Blockers

None. The ticket is executable but has not begun; implementation must occur in
a later turn under the repository execution gate.
