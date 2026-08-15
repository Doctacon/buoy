Status: active
Created: 2026-08-15
Updated: 2026-08-15
Amends: .10x/decisions/buoy-owns-bounded-multi-corpus-retrieval.md

# Buoy Uses Bounded Prototype Routing

## Context

The first bounded multi-corpus router represents each corpus with one broad
BGE passage and scores every downloaded card vector locally. Its exact-name
path is reliable, but a single generated description such as “Indexed
knowledge source at …” cannot represent the different descriptor-free
questions a corpus can answer. Dozens of increasingly similar corpora also
make a bounded second-stage comparison and calibrated confidence necessary;
the exact in-memory dot products themselves remain cheap at that scale.

Buoy already has the required bounded components: one reserved Turbopuffer
catalog namespace with an ANN-indexed vector per card, one immutable local BGE
model, one immutable local MiniLM cross-encoder, explicit catalog mutation,
and a hard maximum of three content namespaces.

## Decision

Buoy keeps `buoy-routing-catalog-v1` as its only routing catalog and keeps
exactly one card document per content namespace. The additive remote catalog
schema v2 adds an exact four-field non-filterable bundle:
`routing_examples`, `routing_prototype_hash`, `routing_prototype_vector`, and
`routing_prototype_vector_hash`. A card may contain zero through eight
canonical examples. The prototype vector is ordinary `[]float` with no ANN.
Schema-v1 cards reconstruct the complete empty-example bundle from their base
semantic hash, vector, and vector hash; partial v2 state fails closed.

The ANN-indexed 384-dimensional `vector`, `semantic_hash`, and `vector_hash`
remain the exact legacy base-passage authority even when examples exist. Buoy
embeds the base passage and every contextual example passage in one model call,
computes their normalized arithmetic mean into the separate
`routing_prototype_vector`, and binds it with projection identifier
`separate_prototype_vector_normalized_mean_v1` plus its two hashes. It does not
store prototype documents or add a second vector index.

After the live inventory and stable catalog coverage gates, descriptor-free
routing computes exact cosine scores against the prototype vectors already returned by
the two strong catalog passes and retains at most twelve eligible cards. The
pinned local MiniLM then scores the query against each shortlisted card's base
passage and examples. A corpus score is the maximum of those passage scores.
The exact BGE score is a shortlist signal, not the final confidence score.

Complete normalized title and alias matches retain their existing authority:
one named corpus remains first, two or three named corpora select exactly
those corpora, and more than three named corpora fails with explicit-selection
guidance. Routing examples never become exact names. Automatic retrieval
continues to search at most three content namespaces, and explicit
`--namespace` continues to bypass all automatic work.

Raw MiniLM scores are not probabilities. Confident-singleton score and margin
thresholds must come from one immutable packaged calibration revision bound to
the exact model, shortlist, projection, prototype, and canary contracts. The
candidate path remains inactive until its held-out per-corpus canaries are
human-approved and every quality gate passes. There is no runtime, CLI, or
environment threshold override.

Migration is reader-first. The implementation initially accepts both exact
schema versions, continues schema-v1 writes when schema v1 is observed, and
does not migrate the live catalog. Separately authorized disabled schema-v1
test corpora may be created through the existing public workflow; that setup
does not add prototype fields. A later explicitly approved migration may
add the v2 bundle and conditionally backfill cards after the compatible reader
is integrated and deployed, while production routing still uses the legacy
base vector. Reviewed examples may then be installed so the authoritative
catalog can supply the candidate calibration/certification evidence required
before a separate activation. Old binaries reject the additive schema because
their validator is exact; that expected fail-closed incompatibility must be
disclosed and handled by upgrading supported readers before migration.

## Alternatives considered

### Multiple prototype documents in the current schema

Rejected. They avoid a schema field but violate the one-row-per-card identity,
duplicate-target, pagination, count, revision, and optimistic-mutation
contracts. They also break old exact readers and create stale-prototype cleanup
without providing a safe rolling migration.

### Put examples in aliases or tags

Rejected. Aliases control exact-name routing and tags participate in lexical
matching and operator search. Encoding question prototypes there would blur
independent semantics and could silently change shortcut behavior.

### A second catalog namespace or late-interaction vector attribute

Rejected for this scale. A second namespace creates dual authority,
backfill/dual-write complexity, and extra reads. Provider late-interaction is
not needed for at most eight coherent examples. The chosen ordinary prototype
vector is downloaded with the authoritative card snapshot and scored exactly
in memory; it creates no second provider index.

## Consequences

Catalog authority remains one namespace and one row per corpus. Network
request classes and counts remain those of the authoritative inventory and
paginated two-pass catalog read; there is no new shortlist or per-card provider
query. Exact BGE dot products remain linear in eligible cards, while the
materially heavier local MiniLM work is bounded by twelve cards and nine
passages per card.

Manual operators can describe real capabilities without expanding the global
answer-key evaluation. Automatic apply preserves reviewed examples but does
not generate them from source identity: the current plan cannot truthfully
infer product capabilities from a URL, repository name, filename, or relation
name. Content-derived examples require a separate reviewed source/plan
contract.

The additive schema requires a coordinated migration rather than an incidental
apply write. Until approval, current production route selection and the shared
catalog schema remain unchanged. The four owner-authorized disabled test
corpora recorded by this task are operational fixtures, not activation.
