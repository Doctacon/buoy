Status: active
Created: 2026-08-15
Updated: 2026-08-15
Amends: .10x/decisions/buoy-uses-bounded-prototype-routing.md

# Buoy Activates Certified Bounded Prototype Routing

## Context

The schema-v2 reader, prototype projection, exact in-memory shortlist, bounded
MiniLM reranker, migration operator, and reviewed routing examples are already
implemented. The live catalog now has seven eligible cards with six reviewed
examples each. A clean, read-only 65-case run from source commit
`16357c629a96e4b309592917ad479a163cec3047` and tree
`c002897fc3224faae9c8670f785e906884100890` passed every quality gate. Its
report SHA-256 is
`d9369f82d47d17fd0a7388246348c258d97b12f956ca9796e3afaa5442255a9d`.

That report proves the candidate scorer and the exact certified catalog
projection. It predates production activation wiring, so it cannot truthfully
identify the later activation implementation commit. Binding a final artifact
to its own containing commit would also be circular. Commit ancestry alone is
not a durable production-source receipt after task squash integration, so the
exact dormant bytes of `routing.py`, `cli.py`, and `evidence.py` must also be
bound independently.

## Decision

Buoy will activate the bounded prototype route through one strict packaged
artifact. Implementation is dormant first: production wiring and an exact
v1-collect/v2-active loader land on the task branch while the packaged artifact
remains collect-only. That clean dormant commit is then exercised by the same
read-only 65-case collector. Only an independently audited, exactly matching
dormant report may authorize changing the packaged artifact to active.

The active artifact records both authorities:

- the owner-approved original report, source commit, source tree, and quality
  verdict digest; and
- the later clean dormant-wiring report, source commit/tree, evaluator
  identities, exact SHA-256 identities for `routing.py`, `cli.py`, and
  `evidence.py`, and calibration/certification receipts.

The dormant report emits those three production-module hashes. The active
artifact records them as exact fields `routing_module_sha256`,
`cli_module_sha256`, and `evidence_module_sha256`. Its loader recomputes them
from the installed packaged bytes and rejects any mismatch before routing.
Distribution/build tests independently prove the wheel and source-distribution
module bytes reproduce the same receipts.

The certified 65-case ground truth must also be reproducible without a scratch
directory. Buoy therefore packages exactly the three owner-approved current
canary packs as `routing_canaries/rentptr.json`,
`routing_canaries/salesforce.json`, and
`routing_canaries/whiteboxgeo.json`. Their raw-byte SHA-256 identities are,
respectively,
`5a39c38d302cbc5c6d758b1e48d4456456a4357248f559a6cf56e0234742f4f5`,
`32106e02d877788e676cdb3db3f7a3567f57f96fa009a7a558b82ca1d407d13d`,
and `5558a4e8a786f0a5553ba0237ebf8248a5d576bd1937ffd69cf9af66a8ac0916`.
Together with the unchanged approved legacy projection, those exact bytes
retain suite SHA-256
`0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`.

The four disabled synthetic fixture packs remain external experiment inputs.
They are not production ground truth, package members, active-artifact inputs,
or permission to enable their catalog cards. Wheel and source-distribution
inventory must contain exactly the three current packs above under the routing
canary data directory.

The active runtime accepts only the packaged artifact. No command-line option,
environment variable, configuration value, alternate path, or loose threshold
argument can replace its score or margin floors. A valid collect artifact keeps
the legacy hybrid selector during dormant validation. A valid active artifact
selects the bounded prototype route. A missing, malformed, incompatible,
unapproved, partially bound, or projection-drifted active state fails before
any content namespace resource or content query; it does not silently fall
back to the legacy selector.

Explicit namespace retrieval remains an earlier bypass and does not load the
routing catalog, routing confidence artifact, routing embedder, or reranker.
Automatic selection retains exact title/alias priority and a maximum content
fanout of three.

The certified semantic catalog projection is
`e559a8aac5a4f7fb808f137b1c6a3710b6cd5b6764fc84f7f06120e33307ef7c`.
Any change to eligible routing semantics or eligibility changes that digest
and stops active automatic routing until a new candidate is calibrated,
certified, owner-approved, and packaged. Operational rollback is deployment of
the prior legacy-router build at commit
`16357c629a96e4b309592917ad479a163cec3047`, not a schema/card/content rewrite
and not an in-process fallback switch.

## Authorization boundary

The repository owner directed “yes activate” on 2026-08-15 after receiving the
passing result and inactive-state disclosure. That direction authorizes the
bounded task-branch implementation, exact certified active artifact, local and
read-only validation, independent review, push, and a pull request to
`develop`. It does not pre-authorize merging an unknown future PR head into
`develop`, promoting an unknown future `develop` head to `main`, deployment,
tagging, package publication, or release publication. Those actions require
their normal exact-head checks and separately explicit integration/release
authority.

## Consequences

Automatic descriptor-free retrieval gains the already certified prototype
shortlist/reranker and calibrated singleton decision. Exact namespace requests
remain independent. The artifact and semantic projection become deliberate
operational stop gates, so onboarding or changing an eligible corpus requires
a new reviewed routing-quality revision rather than silently widening the
authority of old thresholds.

This activation performs no provider, schema, catalog-card, content-row,
namespace, credential, tag, release, or publication mutation. A normal live
retrieval may query content only after routing succeeds; this decision grants
no new mutation surface.
