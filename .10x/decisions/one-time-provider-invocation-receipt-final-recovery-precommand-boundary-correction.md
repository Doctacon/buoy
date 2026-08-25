Status: active
Created: 2026-08-25
Updated: 2026-08-25
Supersedes: .10x/decisions/superseded/one-time-provider-invocation-receipt-final-recovery-model-authority-correction.md
Authorization: .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-authorization.md
Preflight-Failure: .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-live-preflight-failure.md
Historical-Candidate-Evidence: .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-dual-model-candidate.md
Historical-Candidate-Review: .10x/reviews/2026-08-25-provider-invocation-receipt-final-recovery-dual-model-candidate-review.md
Plan: .10x/tickets/2026-08-25-provider-invocation-receipt-final-recovery-plan.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Automatic-Retrieval: .10x/specs/automatic-multi-corpus-retrieval.md
Routing-Quality: .10x/specs/scalable-routing-quality.md
Evidence-Abstention: .10x/specs/automatic-retrieval-evidence-abstention.md
Routing-Activation: .10x/specs/bounded-prototype-routing-activation.md
Multi-Corpus-Decision: .10x/decisions/buoy-owns-bounded-multi-corpus-retrieval.md
Bounded-Routing-Decision: .10x/decisions/buoy-uses-bounded-prototype-routing.md
Routing-Activation-Decision: .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md
Evidence-Decision: .10x/decisions/buoy-owns-automatic-retrieval-evidence-abstention.md
Candidate-Readiness: .10x/knowledge/provider-free-candidate-readiness-before-one-shot-authority.md
Package-Inheritance: .10x/knowledge/exact-reproduced-package-digests-inherit-reviewed-safety.md
Attempt-Accounting: .10x/knowledge/provider-budgets-distinguish-logical-operations-and-transport-attempts.md
Implementation-Evidence: .10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md
Implementation-Review: .10x/reviews/2026-08-24-provider-invocation-receipt-integration-review.md

# One-Time Provider Invocation Receipt Final Recovery: Corrected Precommand Boundary

## Context

The owner authorized repeatable provider-free local build, debug, correction,
and review followed by exactly one ordinary live command. The authorization
makes command start—not the first provider-free assertion—the consumption
boundary. It expressly permits preparation to rebuild and correct owned
provider-free harness/runtime material until the exact reviewed candidate and
its required checks pass or a real product defect is established.

The exact dual-model candidate previously passed independent review at evidence
commit `fa70a8c3e79d2df4d5b643f7bc1cc8af462f51ec`, tree
`45b2684c7d2f71e7c03a65e2d9bd5e201b923ffa`, wheel SHA-256
`42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`.
A later runner entered provider-free identity and operational-state reproof but
returned generic stage `preflight` before the reviewed wrapper was invoked. The
command-start ledger was absent. No credential value was accessed, no model was
imported or constructed, no telemetry operation ran, no DNS/TLS/provider/
network/catalog/content/retrieval access occurred, and no receipt existed.
Command-start count is therefore exactly zero.

The superseded decision and generated live ticket incorrectly treated that
provider-free pre-wrapper failure as terminal, deleted the approved retained
candidate, and required new owner authority. The deletion remains a truthful
observed cleanup event and creates a preparation regression. It does not consume
the owner's sole live authority and does not create a new live attempt.

## Decision

Continue the existing non-executable parent and exactly its two sequential
children. Reopen the original candidate child as the active regression owner.
Keep the existing live child blocked and inactive. Do not create another live
child and do not increase the authorized command count.

### Phase 1: repeatable provider-free preparation through complete pre-wrapper PASS

Only
`.10x/tickets/2026-08-25-prepare-provider-invocation-receipt-final-recovery-candidate.md`
may rebuild and prepare the candidate. All work before credential-value access,
model-library import or model construction/loading/inference, DNS/TLS/provider
or other network access, telemetry access, wrapper invocation, and ordinary-
command start is provider-free preparation. That includes every candidate,
repository, cache, model-asset, telemetry-filesystem, credential-source-
metadata, process, global-state, case/dataset, wrapper, and operational-state
assertion formerly run as live preflight.

Under its existing provider-free activation, phase 1 MUST:

1. rebuild from a local VCS-aware clone or checkout at exact reviewed source
   commit `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
   `9017c4a335938faca80cdded54545df8b79c12f8`, without source or ref mutation;
2. use only an owner-private UV cache, optionally seeded by read-only copy from
   the existing cache, with every build/runtime write in owned temporary state;
3. iteratively diagnose and correct only owned provider-free build, cache,
   environment, runtime, validator, harness, wrapper, manifest, or assertion
   mechanics and rerun them without a build, correction, or preflight-run limit;
4. accept only wheel filename
   `buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl`, version
   `0.5.2.dev87+g0b27c4eaa`, size 730602 bytes, the established 78 reviewed
   members, and SHA-256
   `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`;
5. reuse the exact integration package evidence cryptographically and never
   author or run a novel archive member-type classifier;
6. reprove exact package, routing, installation, help/import, fake-only receipt,
   and strict canonical receipt behavior without retrieval;
7. inspect only by provider-free filesystem reads the exact cache roots, refs,
   and public assets for both authorized models, guard their exact identities
   and settings, and reject every other model, download, or substitution without
   importing or constructing a model;
8. run the complete pre-wrapper preflight repeatedly until every assertion
   passes in one bound run against the exact candidate and then-current state;
9. preserve only bounded content-free assertion categories and generic outcomes
   needed to diagnose and prove each iteration; no record or retained diagnostic
   may contain a private path, credential value, query, namespace, content,
   result, raw exception, raw output, manifest body, receipt bytes, or other
   prohibited data; and
10. retain the complete rebuilt source, wheel, owned cache, runtime,
    dependencies, installed package, harness, wrapper, manifests, and content-
    free summary privately after a failed provider-free assertion and after the
    final PASS. Delete only unnecessary raw diagnostics and correction scratch;
    never delete the candidate merely because a pre-wrapper assertion failed.

Bounded assertion categories MAY identify only the failing class needed for
correction, such as exact candidate identity, repository/current state, owned or
source UV cache equality, authorized model-cache filesystem equality,
telemetry-filesystem equality, credential-source metadata equality, global/tool/
home equality, process state, case/dataset identity, or wrapper/harness identity.
They MUST NOT disclose the checked private value, path, manifest body, or raw
failure. A provider-free assertion failure remains in phase 1 and may be
corrected, rebuilt, and rerun. A reproducible exact-product defect blocks phase 1
and grants no source change or live access.

There is no authority in phase 1 to read/source/copy/print/hash a credential
value; import or construct/load/run either model; access DNS, TLS, provider,
network, catalog, content, retrieval, or telemetry database/store/API/command;
install or replace a global tool; mutate an existing cache, model cache,
credential source, telemetry filesystem, source, test, specification, lock,
routing artifact, dataset, repository ref, or unrelated state; or invoke the
wrapper or ordinary command.

The exact production model boundary remains:

- `BAAI/bge-small-en-v1.5` at revision
  `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32, unchanged production
  automatic-device behavior, offline/local-only/no-download; and
- `cross-encoder/ms-marco-MiniLM-L-6-v2` at revision
  `c5ee24cb16019beea0893ab7796b1df96625c6b8`, CPU-only, local-files-only,
  safetensors-only, remote code disabled, max-length 512, batch 8, offline/no-
  download.

The historical PASS/GO remains truthful for the exact candidate that existed at
review time, but deletion makes it stale and non-transferable. Phase 1 closes
again only after the rebuilt exact candidate is retained, one complete
pre-wrapper preflight passes, and a fresh independent **PASS/GO** binds the new
sanitized evidence commit/tree and all retained immutable handoff identities.
GO review is provider-free and performs no build, credential, model, telemetry,
provider/network, retrieval, wrapper, or command operation.

### Phase 2: the existing exactly-one live command

Only
`.10x/tickets/2026-08-25-run-provider-invocation-receipt-final-recovery-live-command.md`
may execute live. It remains `Status: blocked`, `Activation: inactive`, command-
start count zero, and live authority unconsumed while phase 1 is active. It
becomes eligible—not activated—only after the rebuilt exact candidate, complete
pre-wrapper preflight PASS, and fresh independent PASS/GO all exist together and
remain unchanged.

After a separate live activation binds that fresh GO and current clean state,
phase 2 receives only the already prepared immutable handoff. It performs no
build, cache seed/correction, installation, harness/wrapper correction,
preparation assertion, or provider-free reproof. Invocation of the retained
wrapper for its sole ordinary automatic command is the live start boundary and
consumes all live authority before any credential-value access, model
construction, provider/network access, or ordinary-command behavior inside it.
If wrapper invocation or any later step fails, is interrupted, or is uncertain,
there is no wrapper, command, provider, or receipt retry and no second command.

The sole command remains exact:

- case `m01-dagster-turbopuffer-quality` from dataset
  `automatic-multi-corpus-retrieval-v1` at SHA-256
  `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`;
- only the exact BGE and MiniLM models and settings above, constructed or reused
  only where unchanged ordinary automatic routing/retrieval requires;
- the existing intended credential source, used privately without exposure;
- telemetry disabled;
- provider behavior limited to current strong catalog reads and selected
  content reads;
- catalog invocation count at most 5 and content invocation count at most 18;
- no preview, explicit command, alternate case/dataset/model/candidate,
  substitution, download, provider write/management action, provider retry,
  command retry, receipt retry, receipt-only run, or second command.

PASS still requires a known truthful successful original command outcome kept
separate from receipt acceptance, one terminal strict canonical compact UTF-8
content-free receipt satisfying both active specifications with every
represented operation/attempt successful, catalog `<=5`, content `<=18`, exact
post-state equality, provider read-only reconciliation, bounded retention and
private/raw cleanup, and independent final review. Missing, incomplete,
observer-failed, malformed, noncanonical, over-bound, privacy-unsafe, error, or
interrupted receipt fails without inference or retry.

Post-state equality still covers repository/ref/worktree, retained candidate
until authorized cleanup, owner-private and source UV caches, both exact model
cache roots/refs/assets, telemetry filesystem, credential-source identity
without value retention, global tools/home, process state, and bounded unrelated
state. Neither phase may claim physical wire sends, SDK-internal retries,
provider billing, cost, or rate-limit behavior.

## Historical disposition and compatibility

The preflight-failure evidence remains immutable observation: generic
`preflight` failed, cleanup deleted the candidate, no wrapper or ordinary
command started, no prohibited access occurred, and no receipt exists. This
decision supersedes only its then-governing retry/authority interpretation.
Command-start count remains zero.

The model-authority correction is canonical history at
`.10x/decisions/superseded/one-time-provider-invocation-receipt-final-recovery-model-authority-correction.md`.
Its former active path remains a relative compatibility link to that
`Status: superseded` record and grants no current authority. The earlier flawed
one-model decision remains separately superseded history. All three earlier
consumed canary tickets remain blocked, consumed, and ineligible; none is
reopened by this correction.

## Alternatives considered

### Treat pre-wrapper identity reproof as the one-shot live attempt

Rejected because it conflicts with the owner's explicit split between
repeatable provider-free build/debug and exactly one live command. It also makes
candidate readiness impossible to prove safely before a one-shot transition.

### Require new owner authority or a new live ticket

Rejected because wrapper/ordinary-command start count is zero and the current
owner explicitly corrected the boundary without widening the authorized count.
The existing live ticket remains the sole live owner.

### Reuse the historical GO after rebuilding

Rejected because the reviewed retained handoff was deleted. Rebuilding and
complete pre-wrapper PASS must be followed by fresh independent GO bound to the
new retained identities.

### Move any pre-wrapper reproof back into the live child

Rejected because any assertion that can fail before credential/model/provider/
network access or wrapper/command start is repeatable provider-free preparation,
not one-shot live execution.

## Consequences

The candidate ticket truthfully owns the deletion regression, exact rebuild,
complete repeatable pre-wrapper preflight, retention, and fresh GO. The live
ticket remains blocked/inactive and singular. Provider-free failures can be
safely diagnosed and corrected without consuming command authority; the first
wrapper invocation is irreversible and receives no retry. The exact two-model,
case/dataset, privacy, telemetry-off, provider-read-only, 5/18, receipt,
post-state, cleanup, and no-claim rules remain unchanged.
