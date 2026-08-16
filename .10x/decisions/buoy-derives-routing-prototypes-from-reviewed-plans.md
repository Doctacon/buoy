Status: active
Created: 2026-08-16
Updated: 2026-08-16
Amends: .10x/decisions/compact-delta-plan-storage.md, .10x/decisions/buoy-uses-bounded-prototype-routing.md, .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md

# Buoy Derives Routing Prototypes from Reviewed Plans

## Context

Approved apply already creates or refreshes one routing card after content and
local state commit, but a new generated card contains only source-identity
metadata and no capability examples. Automatic routing does not inspect the
content namespace before choosing it. The active confidence artifact also
binds the exact eligible catalog projection, so adding the otherwise valid
enabled card stops all namespace-free retrieval.

The required product contract is simpler: after `buoy plan` and a successful
approved `buoy apply`, the new namespace must immediately participate in
automatic retrieval without a generative LLM, a per-source catalog command,
or an apply-time evaluation run. The shared account catalog remains a
reader-first, one-time prerequisite.

## Decision

Planning deterministically selects a small reviewed bank of source-grounded
routing passages from the complete desired corpus while that corpus is still
available in memory. The selection is model-free and provider-write-free. Its
exact text, provenance, ordering, and digest are persisted in the compact plan
artifacts even when every selected chunk is unchanged and therefore absent
from the content delta.

Approved apply embeds only that bounded reviewed bank with the existing pinned
local routing embedder and stores its text and individual vectors as
system-owned routing evidence on the same authoritative card. It does not
generate questions, load a generative LLM, run MiniLM, run canaries,
recalibrate thresholds, or reacquire the source.
Reviewed operator-authored routing examples remain separate and preserved.
Manual examples take evidence slots first and generated source passages fill
the remainder, for one fixed maximum of eight non-base passages per card.

Certification becomes authority for calibrated descriptor-free singleton
routing, not authority for basic catalog participation. An exact certified
anchor projection retains current score-and-margin singleton behavior. Valid
additional or changed cards are provisional: exact title/alias routing remains
authoritative, and every descriptor-free route uses the existing bounded
prototype scorer but begins with the best three eligible namespaces (or all
when fewer exist). No threshold from the certified anchor may create a
singleton while provisional cards participate.

Malformed artifacts, malformed cards, stale hashes/vectors, and unstable reads
still fail before content access. Any otherwise valid catalog drift from the
exact certified projection--including added, changed, disabled, missing, or
incompatible certified members--removes singleton authority and routes the
remaining eligible cards provisionally. Unmanaged live namespaces without
cards are reported but do not disable routing through the valid catalog; a
failed apply registration remains a nonzero partial success and cannot claim
automatic readiness.

The compact local format advances to plan schema v3 and delta schema v2. The
remote card contract gains one additive system-owned passage field plus its
flattened bounded vector bank and hash through a reader-first schema v3.
Existing v1/v2 cards normalize to an empty generated passage/vector bank and
retain their exact prior projection when that bank is empty. No prototype row,
second routing namespace, or duplicate per-corpus authority is introduced.

Exact remote schema v3 must already exist before a schema-v3 plan can register
its card. Turbopuffer exposes no atomic create-schema-only-if-absent primitive,
so ordinary apply never attempts to provision a missing catalog or migrate an
existing one. A missing, older, or unreadable catalog after content and state
commit is truthful nonzero partial success with no catalog mutation; the exact
plan is retained and an opaque plan-backed
`repair-apply --inspect-current` command is emitted for use after prerequisite
or read-failure recovery. The inspection
revalidates committed authority under the namespace lock, strongly reads exact
v3 without model work or writes, and emits a repair bound to observed card
absence or exact revision. A later failure after apply already observed exact-v3
state may emit the bound repair directly.

## Consequences

The normal installed workflow becomes plan, review, apply, and namespace-free
retrieve. Apply adds at most one bounded routing-embedding batch and the
existing verified catalog mutation. Broad content is represented by real
source passages rather than invented questions or generic URL metadata.
The repair command references the retained verified plan and committed apply
identity; it never copies source passages into terminal output or shell
history. Generic catalog upsert cannot set, clear, or replace the system-owned
passage bank and preserves existing passages; approved apply, retained-plan
repair, or separately governed migration/backfill owns passage mutation.

Old local plans are not silently upgraded. Old remote readers reject the
additive schema, so compatible readers must be integrated and deployed before
any shared live schema migration. Existing cards can be backfilled truthfully
only by fresh source plan/apply runs or a separately reviewed operation; old
cleaned plans and compact applied state do not retain the source content.
Because bounded excerpts are ordinary remote card attributes, raw catalog-row
read access is source-content access even though normal Buoy output redacts
their text and vectors.

The active confidence artifact must be revised because production routing
module bytes and the catalog-policy contract change. Prior thresholds remain
authority only for the exact unchanged certified anchor; provisional routing
cannot consume them.

## Authorization boundary

On 2026-08-16 the repository owner explicitly directed execution of this
complete implementation after reviewing the plan/apply, content-prototype,
top-three, and certification boundaries. That authorizes bounded local source,
test, documentation, artifact, evidence, review, branch, commit, and PR work.
It does not authorize live provider/schema/card/content mutation, deployment,
release publication, or self-integration into `develop` or `main`.
