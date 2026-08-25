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

The exact candidate remains retained. Complete pre-wrapper preflight and final
immutability are pending the harness compilation against this anchor; this
anchor alone is not candidate PASS/GO and does not make the live child eligible.
