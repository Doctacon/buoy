Status: recorded
Created: 2026-08-25
Updated: 2026-08-25
Relates-To: .10x/tickets/2026-08-25-prepare-provider-invocation-receipt-final-recovery-candidate.md, .10x/decisions/one-time-provider-invocation-receipt-final-recovery-precommand-boundary-correction.md, .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-live-preflight-failure.md

# Provider Invocation Receipt Final Recovery Regression Candidate

## Preparation anchor

Provider-free regression recovery began from clean task HEAD
`94f78cdf318d033d8c81cf4229aac822b7488ce1`, tree
`4c1187a10e512fb1936bfdc9644934ddcdd10db7`, on the registered
`work/provider-invocation-receipts-execution` task worktree. The reviewed source
commit `0b27c4eaa2449493125f4040af3cd1f7c926b531` is an ancestor. Every intervening
path at this anchor is under `.10x/`; `pyproject.toml`, `uv.lock`, `src/`,
`tests/`, and `scripts/` are byte-identical to the reviewed source commit.

One owner-private mode-0700 root contains a no-hardlink VCS-aware local clone,
an owned isolated UV cache seeded by copy-on-write read-only copy from the
existing cache, exact wheel output, CPython 3.13 runtime, validators, and empty
live state. The source clone is detached and clean at exact commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`. No source repository ref or
registered worktree changed.

This commit is the immutable compile-time preparation-evidence anchor for the
retained preflight harness. The complete positive preflight, negative matrix,
final immutable handoff hashes, and current activation binding are appended in
a later evidence commit because the harness must bind this already-existing
commit/tree exactly.

## Owned cache and build boundary

The existing UV cache was read only. A canonical sorted content/type/mode/link
manifest before seeding and after all build/install activity remained identical:
1,314,401 entries, comprising 170,905 directories, 1,139,272 regular files,
4,224 symlinks, zero other types, 32,974,101,113 regular-file bytes, SHA-256
`50abda15ae428f9f95f9f6a18cd5f6b96f6c26e4ce81e7b6d15ee5ffa52b8270`.
Atime is excluded and no atime equality is claimed. No source-cache lock,
repair, clean, prune, or index operation ran.

All build, install, bytecode, HOME, TMP, XDG, and UV writes were directed into
the owned root. Strict offline/no-download controls were set and inherited
provider credentials, telemetry enablement, and `PYTHONPATH` were removed from
every build, installation, validation, help, and fake-test process.

One offline wheel build reproduced exactly:

- filename `buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl`;
- version `0.5.2.dev87+g0b27c4eaa`;
- size 730602 bytes;
- 78 reviewed archive names; and
- SHA-256 `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`.

The output directory contains only that regular nonsymlink wheel and the
established regular nonsymlink one-byte uv `.gitignore` marker. No novel archive
member-type classifier ran. Exact package safety is inherited from
`.10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md`
and its independent PASS review.

## Generic correction ledger

Only bounded generic categories are retained:

| Attempt | Category | Generic outcome |
| --- | --- | --- |
| build 1 | candidate | exact PASS |
| install 1 | runtime | corrected interpreter-minor selection in owned state |
| package validator 1 | package/receipt | PASS |
| fake suite 1 | harness identity | corrected private test-discovery root |
| fake suite 2 | package/receipt | 91/91 PASS |
| operational baseline 1 | UV/model/telemetry/credential metadata | PASS |

Raw build, installation, validator, help, and failed-test diagnostics remain
private only until final cleanup and are not copied into durable evidence.
Neither correction changed source, wheel, existing cache, model cache,
credential source, telemetry filesystem, repository ref, global tool, or
external state.

## Provider-free package and operational proof

The exact wheel was installed without dependencies after the exact frozen lock
was installed offline into CPython 3.13. Dependency consistency passed. Exact
distribution/module version, sole `buoy = buoy_search.entrypoint:main` entry
point, 83 installed distribution files, reviewed production hashes, active
schema-v3 routing authority, executable version/help, module help, private
receipt import, strict canonical receipt round trip, malformed/noncanonical
rejection, and exact dataset/case identity passed. The four installed-wheel
fake-only receipt modules passed 91/91 with a model-library import blocker.
Imports resolved from the isolated installed wheel, not ambient source, user
site, global package, or `PYTHONPATH`.

Filesystem-only model inspection imported and constructed no model. It proved
sole exact refs, complete exact symlinked public asset inventories, regular
in-root blobs, `model.safetensors`, and model-root/snapshot/lock equality for:

- `BAAI/bge-small-en-v1.5` at
  `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`; and
- `cross-encoder/ms-marco-MiniLM-L-6-v2` at
  `c5ee24cb16019beea0893ab7796b1df96625c6b8`.

The BGE model root has 44 entries and 267,599,470 regular-file bytes; its
snapshot has 15 entries including root and its lock root has 2 entries. The
MiniLM model root has 27 entries and 91,815,798 regular-file bytes; its snapshot
has 7 entries including root and its empty lock root has 1 entry. Every exact
manifest is retained privately for complete preflight equality.

Raw-filesystem telemetry identity has 37 entries, 9,468,291 regular-file bytes,
and SHA-256
`077e68a1783d9d40cc9e17c2632a85a3ff0f14e2aee7f86821a464b79dbd8a9f`.
No telemetry database, store, API, status, queue, receipt, writer, migration,
backup, export, or purge behavior was opened or invoked. The intended
credential source passed regular-nonsymlink presence/type/metadata capture
without opening, reading, sourcing, copying, printing, or hashing its value.

## Boundary and current disposition

No credential value, model-library import during model/cache inspection, model
construction/load/inference, DNS/TLS/provider/network, catalog/content access,
retrieval, telemetry operation, global install/tool invocation, source/ref
mutation, wrapper invocation, command-start marker, live command, or receipt
from a live operation occurred. Command-start count remains zero and live
authority remains unconsumed.

## Complete pre-wrapper preflight and negative matrix

The retained harness compiles exact preparation-evidence commit
`a6c52acb37ea5fb20e9f01a426144b5ba8b50974`, tree
`e8e5b13f9493d55f8c5b0c342b9bbc569f0bfb6c`, as immutable candidate evidence.
It separately accepts runtime activation commit/tree values only after proving
they equal actual current Git HEAD/tree, the worktree is clean, candidate
evidence is an ancestor, all intervening paths are records-only, and all paths
outside `.10x/` remain byte-identical to reviewed source commit `0b27c4eaa`.
It does not require a later activation HEAD/tree to equal the candidate-evidence
HEAD/tree.

One explicit `--preflight-only` invocation against the exact clean evidence
anchor passed every bounded category in one run, in this order:

1. `wrapper-harness-identity`;
2. `candidate`;
3. `repository-current-state`;
4. `uv-cache`;
5. `model-cache`;
6. `telemetry-filesystem`;
7. `credential-source-metadata`;
8. `global-tool-home`;
9. `process`; and
10. `case-dataset`.

The terminal generic outcome was `FULL-PRECOMMAND-PREFLIGHT-PASS`. A separate
provider-free negative-fixture matrix rejected candidate-wheel drift,
candidate-evidence drift, model/ref/asset drift, source/owned-cache drift,
telemetry-filesystem drift, repository HEAD/tree/path drift, credential-source
presence/metadata drift, process/command-start drift, wrapper/harness drift, and
case/dataset drift. Each rejection emitted only its bounded generic category;
no checked value, manifest body, private path, raw diagnostic, or prohibited
value was emitted or retained.

Preflight-only exited before credential sourcing, model-library import or model
construction/load/inference, private receipt scope, wrapper live invocation, or
command-start marker. The one-command live-state directory remained empty and
command-start count remained zero.

## Exact immutable retained handoff

The owner-private handoff is immutable except for dedicated empty writable HOME,
temporary, XDG, bytecode, scratch, and live-state directories reserved for the
future separately activated wrapper. Its content-free bindings are:

- preflight harness SHA-256
  `268b1278709660dfaf923fa9d53d6fb832944bed9dbc493e26bee3a0ab181249`;
- Python live harness SHA-256
  `66a1a4178088919cd42c31dfb6e487f15686acbfaf557ab926ab175e757cb3e8`;
- shell wrapper SHA-256
  `13c6d4af186a9c1daf3fcac52c1907a3668128c63aabb10ec8fca8c17dac57b9`;
- handoff manifest SHA-256
  `5451af0a4503579a67b11b5ff2539a10f33979b7de8175d121cb748d59dd5c26`;
- content-free handoff summary SHA-256
  `ef432f8547d391ffd545ab009d569b7d74c82041d6abfe76f52c957a792c4cae`;
- operational baseline SHA-256
  `f0ca4473e98688602fe28e4d28699c2ce91929dd05fb143c00f4b1c438b6e5f7`;
- candidate baseline SHA-256
  `10832e9f6ebff3cfc81e01dcfa2140522b291e52ce81fcce3c451f762fcc1ba6`;
- read-only source manifest SHA-256
  `7eb15164fe6db78141494fc25e6c1ed6593ee07dbcd20856b6329820e6367e03`;
- read-only dist manifest SHA-256
  `f72ad294950678fcf83a08868065a14327cb48dba4ad389e502c7102cdc32f63`;
- read-only runtime manifest SHA-256
  `58e8d29873c7a2119cc3c5339c5ee1154b8a60a12a7bc6ab840f73a8d61b1d0b`;
  and
- read-only owned-cache manifest SHA-256
  `1d64c77889bb4b53d874fcee1395b7c5f1148f4e1084ac21535e7c4ec84e394b`.

The handoff summary binds `candidate_status=active-provider-free-prepared`,
`live_eligible=false`, and command-start count zero. It remains correctly
pending fresh independent review. All correction diagnostics, build/install/
test/help output, process samples, private manifests outside the retained exact
baselines, and temporary validation scripts were deleted. Empty writable roots
were verified empty after cleanup. The exact source, wheel, owned cache,
runtime, installed package, baseline, summary, harness, and wrapper remain
retained.

## Prepared disposition

**FULL-PRECOMMAND-CANDIDATE-PREPARED.** Exact build, package, receipt,
dual-model cache/ref/assets, state, privacy, negative, immutable-retention, and
complete provider-free pre-wrapper gates passed. No credential value, model
import/construction/load, provider/network, telemetry operation, retrieval,
global install/tool invocation, live wrapper, command start, or live receipt
occurred. Command-start count is zero and live authority is unconsumed.

This is candidate preparation evidence, not independent PASS/GO. The candidate
ticket remains active and the live child remains blocked/inactive until a fresh
independent reviewer binds the final evidence commit/tree, exact wheel, complete
preflight PASS, and retained handoff identities.
