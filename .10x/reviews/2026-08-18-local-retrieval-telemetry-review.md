Status: pass
Created: 2026-08-18
Updated: 2026-08-18
Ticket: .10x/tickets/done/2026-08-18-implement-local-retrieval-telemetry.md
Evidence: .10x/evidence/2026-08-18-local-retrieval-telemetry.md
Decision: .10x/decisions/buoy-records-opt-in-local-retrieval-telemetry.md
Specification: .10x/specs/local-retrieval-telemetry.md

# Local Retrieval Telemetry Review

Target: implementation commit
`3a9aa15db39829171d5c9fc74754d48b9629e224`, tree
`3b58627d4279f48bf9418156bd86f5e6a2ec1de2`, based directly on exact
`develop@df8b82eef61ed36275773273f0648d29763acd65`.

## Review performed

Independent review challenged:

- the exact commit topology, all 11 changed paths, diff hygiene, and the
  byte-identical certified CLI, evidence, routing, and routing-quality files;
- default-off enablement, the standard SDK kill switch, invalid ambient SDK
  configuration, and disabled-mode filesystem/output/context equivalence;
- isolation from the process-wide OpenTelemetry provider/current context,
  absence of outbound trace propagation, and absence of any Collector, OTLP,
  HTTP, gRPC, socket, or DNS implementation or dependency;
- executor propagation of only Buoy's private trace state, including rejection
  of unrelated caller `ContextVar` values;
- the sink-side span/event/attribute allowlists and exact-byte adversarial
  exclusion of queries, content, namespaces, URLs, paths, credentials, raw
  exceptions, command arguments, vectors, payloads, and ambient resources;
- total failure isolation for SDK setup, sink failures, lock contention,
  rollback, symlinks, incompatible stores, and original retrieval exceptions;
- atomic first-store creation, private permissions, UTC timestamp fidelity,
  and validation of untrusted DuckDB schemas without binding stored views or
  honoring shadowed catalog macros;
- live explicit-single, multi-namespace, automatic, widening, partial-failure,
  reranking, evidence, and fanout semantics; and
- the exact source/lock/ranking/C6 gates and external-effect boundary.

The review reproduced 21/21 adversarial telemetry tests and 138/138 focused
telemetry/retrieval tests. All 117 established retriever, evidence, and
automatic-retrieval tests also passed with local telemetry forcibly enabled
under an isolated home. Full Python 3.11 discovery passed all 904 tests;
Python 3.11 and 3.13 compilation, `uv lock --check`, source validation,
ranking validation, C6 validation, and `git diff --check` passed.

An enabled retrieval completed and persisted under a Python socket/DNS audit
hook with zero connection/DNS events and zero stdout/stderr. The lock adds
only the OpenTelemetry API, SDK, and semantic-conventions packages; it adds no
OTLP exporter. Counterfeit canonical-view metadata, persisted catalog macro
shadows, a removed external-file view, non-UTC DuckDB timestamps, atomic
creation, rollback, byte-exact incompatible-store preservation, ambient
`traceparent`, unrelated context, invalid SDK environment, and root-only event
probes all passed.

The four unchanged certified source receipts were independently recomputed:
CLI `92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`,
evidence `78b792098ee0c49bedc7c135dffc33f4096f7d92222bc437f5d8438f1e015c7b`,
routing `e0711bc40a90c364ca52c7a9884d29342be21e3df43950ec26033a70c2b6e9fd`,
and routing quality
`5d53624613bf5a80ad80e6d103d07cb0fab2d2a6ae2a1456e6c2709147d67aa7`.

## Verdict

PASS. No correctness, privacy, network, failure-isolation, schema-security,
behavioral-equivalence, scope, or documentation blocker remains in the exact
implementation commit. The implementation is bounded, local-only,
content-free at the persistence boundary, and compatible when disabled.

This verdict authorizes the bounded closure records, task-branch push, ready
pull request, exact-head CI, and the owner's explicitly requested squash merge
through a separate integration session. It does not authorize self-integration
by the implementation session, existing-asset migration, provider/model/
credential work, remote telemetry export, `main` mutation, publication,
release, tag, GitHub Release, or branch-protection change.
