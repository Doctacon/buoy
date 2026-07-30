Status: active
Created: 2026-07-29
Updated: 2026-07-29

# Semantic Build Operations

## Purpose and scope

Define CLI estimation, build, remote verification, and bounded inspection for autonomous Phase 3B semantic builds. There is no Command Center semantic UI, item approval, scheduling, deletion, retention, or graph visualization.

## CLI

Buoy MUST expose lazy, provider-inert help for:

- `buoy semantics doctor`
- `buoy semantics estimate --snapshot-id ... --model-endpoint ... --model-id ... --model-revision ...`
- `buoy semantics build ... [--resume] [--sample-size N --sample-seed N]`
- `buoy semantics verify --build-id ...`
- `buoy semantics inspect --build-id ... --kind concepts|mentions|taxonomy|summary [--status accepted|provisional] [--limit 1..100]`

Configuration follows existing CLI/environment conventions without persisting endpoint credentials. Model concurrency is fixed at one. Threshold validation is `0 <= provisional < accepted <= 1`.

## Estimate

Estimate verifies the completed snapshot, reads counts plus at most a deterministic default 20-row evidence sample, and may make bounded local model calls. It MUST write neither semantic namespace nor local artifact. It reports snapshot/active/sample counts, evidence UTF-8 bytes, conservative approximate token method/count, observed local latency, estimated model calls/time range/candidate/concept/mention/taxonomy counts and bytes, exact maximums, pass/fail limits, and truthful zero hosted cost/writes/artifact flags. Exact token claims require a trustworthy tokenizer endpoint.

## Build reporting

Build reports local model calls; turbopuffer reads and internal semantic writes; zero source/evidence-branch writes; zero hosted calls/cost; no local corpus; bounded manifest path/bytes; every incomplete internal namespace; computational/storage counters; and the automatic quality report required by `.10x/specs/autonomous-semantic-builds.md`.

## Verification

`semantics verify` MUST load no local model and perform no write. It reads the completed semantic catalog and completed evidence snapshot; validates exact namespace schemas and observations when available; streams every concept/mention/taxonomy row; recomputes row and semantic logical hashes; validates concept references, active evidence membership and chunk hashes, taxonomy endpoints/status/acyclicity/counts, model/build identity, and supplied or present local manifest. A manifest-only check is incomplete.

## Inspection

`semantics inspect` is remote-read-only, model-inert, bounded to 100 rows, status-aware, and never dumps full evidence content. It shows bounded fields appropriate to concepts, mentions, taxonomy, or summary, including accepted/provisional state, evidence IDs, concise rationale, and compact score breakdown where applicable.

## Activity truth

- Doctor: local model calls true; evidence rows zero; turbopuffer calls/writes false; hosted calls/cost zero.
- Estimate: local model and turbopuffer reads true; writes/artifacts/hosted calls zero.
- Build: local model and turbopuffer reads/internal writes true; source/evidence-branch/hosted writes false; local corpus false; manifest true.
- Verify/inspect: model false; turbopuffer reads true; writes and hosted calls/cost zero.

Provider billing counters are reported only when exposed.

## Documentation and roadmap

README stays concise; `docs/semantics.md` documents local-only privacy, pinning, contracts, commands, policy, sampling/full coverage, storage/resume/determinism/limits; evidence and Command Center docs state integration/internal filtering. Roadmap: 3A remote evidence snapshots implemented; 3B autonomous local concepts/mentions/taxonomy implemented; 3C evidence-backed typed assertions future; Phase 4 graph review/visualization future; Phase 5 incremental semantic maintenance future. No complete-ontology claim.

## Acceptance criteria

Fake-client tests prove no-write/no-artifact estimate, verification corruption/reference/status/hash/cycle/count/manifest failures without model availability, bounded filtered inspect without model/write/full content, exact activity flags, help/import inertness, internal namespace filtering, and package contents. Full repository validation and distribution checks pass without network, credentials, model runtime, weights, crawl, or browser. Live local smoke remains explicitly gated and skipped absent separate configuration.
