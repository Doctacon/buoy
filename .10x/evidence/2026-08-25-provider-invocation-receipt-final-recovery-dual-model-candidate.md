Status: recorded
Created: 2026-08-25
Updated: 2026-08-25
Relates-To: .10x/tickets/done/2026-08-25-prepare-provider-invocation-receipt-final-recovery-candidate.md, .10x/decisions/one-time-provider-invocation-receipt-final-recovery-model-authority-correction.md, .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-candidate-preparation.md, .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-candidate-repair.md

# Provider Invocation Receipt Final Recovery Dual-Model Candidate

## Bound retained candidate

Provider-free correction resumed only the active preparation ticket. The exact
retained source, wheel, owned cache, isolated runtime, and installed package
came from preparation evidence commit
`5e2259d5422a3f3b649c521422a868d770dc7d0d`, tree
`cc80dc4bf49ed3eec63b8d379b30af0e82f23f4d`. The retained harness and handoff
summary continue to require exact equality to that evidence commit/tree; a
merely well-formed substitute remains rejected.

The source remained detached and clean at commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`. Its 1,630-entry, 33,617,577-byte
content/type/mode/link identity remained equal before and after correction.
The exact accepted wheel remained a regular nonsymlink file named
`buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl`, version
`0.5.2.dev87+g0b27c4eaa`, 730602 bytes, 78 inherited reviewed members, SHA-256
`42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`.
No source, wheel, runtime, installed-package, owned-cache, routing, lock, test,
specification, or dataset byte changed.

The retained source identity again reproduced the reviewed private-receipt,
retriever, remote-catalog, CLI, routing-artifact, and dataset hashes recorded in
`.10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-candidate-preparation.md`.
Additional exact installed model-path source bindings are:

| Installed path | SHA-256 |
| --- | --- |
| `buoy_search/config.py` | `b33407002f60c6ca3429e05043f2c1451902112bf793ce2ae2ed0ae9e4da5620` |
| `buoy_search/catalog.py` | `2f1034c5caa807f094df4deeb45b16315cd9df4fa935e7a94365c60203b7ad2c` |
| `buoy_search/chunker.py` | `98a036fa829cbec675b5fd04cc1dd717a0ccc04c417a25ea33433827cec908d8` |
| `buoy_search/cross_encoder.py` | `ed963371948f9c51fdbc7d25df4193613e7b2616f34ba18e7b7b2e01d2ba1674` |
| `buoy_search/routing.py` | `e0711bc40a90c364ca52c7a9884d29342be21e3df43950ec26033a70c2b6e9fd` |

## Exact provider-free dual-model cache inspection

A filesystem-only validator inspected only the two authorized public model
cache roots, their exact refs, snapshot links, resolved public asset files, and
model-specific lock roots. It imported no model library and constructed, loaded,
or ran no model. The validator required the complete exact asset-name sets,
required every snapshot file to be a symlink resolving to a regular blob inside
its own model root, required `model.safetensors`, required the sole cached
snapshot/ref revision below, and rejected an absent, extra, unresolved,
nonregular, or substituted asset.

The manifest scheme is canonical sorted JSON lines over relative path, type,
mode, regular-file size/content SHA-256, symlink target, and—only for the
snapshot asset manifest—resolved public asset size/content SHA-256. It excludes
atime. Exact before/after equality passed for every manifest.

### BGE routing/embedding model

- model: `BAAI/bge-small-en-v1.5`;
- revision: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- required runtime: float32 with unchanged production automatic device;
- complete snapshot: 15 entries including root, 3 directories and 12 asset
  links, manifest SHA-256
  `1bf7fa02387e7354960a9a4485bb36b774e9eb2669e6c311578ab6fdd0e9f7cc`;
- exact model root: 44 entries, 267,599,470 regular-file bytes, manifest
  SHA-256
  `1f72f397ff2449bcdbf23304c6139fa3a6bea93848e935317b4d8d3cc55526b0`;
- exact model lock root: 2 entries, manifest SHA-256
  `6073a064144b11223a8be570256a54b634fdf43d56c0b6991c02320f905ec443`.

### MiniLM production reranker

- model: `cross-encoder/ms-marco-MiniLM-L-6-v2`;
- revision: `c5ee24cb16019beea0893ab7796b1df96625c6b8`;
- required runtime: CPU-only, local-files-only, safetensors-only, remote code
  disabled, max length 512, batch 8;
- complete snapshot: 7 entries including root and 6 asset links, manifest
  SHA-256
  `206ee6ddbab112d0a95c0edd9a0614f43e6ca6dca29b29fab174e3289e038de6`;
- exact model root: 27 entries, 91,815,798 regular-file bytes, manifest SHA-256
  `a39b47bc2ebae4aeb02a6486ba341f54b40eb8e450693f4af86a7ac5c1705b1b`;
- exact empty model lock root: 1 directory entry, manifest SHA-256
  `4543bf6da0cb1ee287e02ff073ffc3b4c5c53059f4aea602e35b5b8eaff208f2`.

No download path was enabled or used. Both exact model roots and lock roots were
content/type/mode/link-identical after all validation.

## Generic retained-harness corrections

Only the owner-private retained harness and content-free handoff summary were
corrected. The harness now:

- retains the exact preparation-evidence commit/tree gate;
- permits only the exact BGE constructor, injects the exact revision,
  local-files-only, disabled remote code, safetensors, and exact cache root,
  preserves automatic device selection, and requires the exact float32 runtime
  configuration;
- permits only the exact MiniLM constructor with exact revision, CPU,
  local-files-only, safetensors, disabled remote code, max length 512, batch 8,
  exact cache root, and the production torch backend;
- rejects every other model, revision, device override, setting substitution,
  nonlocal load, unsafe model format, or download route before construction;
- binds exact installed source hashes for the production model paths; and
- still contains exactly one ordinary automatic command, with model guards
  installed before that command.

Provider-free construction-only checks passed for exact positive BGE and MiniLM
constructor shapes. Negative checks rejected another model, another revision,
nonlocal loading, a device override, and unsafe safetensors settings. Separate
negative exact-evidence checks rejected a different valid 40-hex commit and a
different valid 40-hex tree. The exact positive evidence gate reached only the
construction self-check. No one-execution or command-start marker was created;
the live-state directory remained empty; no command was crossed.

Final retained identities are:

- `run_once.py` SHA-256:
  `f6df9056e466212107be12b6a952e67278bfabb79d0d076801f9bb0400aedeb8`;
- `run-once.sh` SHA-256:
  `d9f67cdc69d22b3f5ae0c9595571a7445fc0332b3b1028d75e6f66d7c3cd4345`;
- harness combined regular-file bytes: `12158`;
- read-only three-entry harness manifest SHA-256:
  `7af3345fc072dc5a7e6a42ffea61b63c7963d58421472f1bc30408bb165da1aa`;
- content-free handoff-summary SHA-256:
  `e962878fe94702fdffa79b384437c4db97a29315c5771e86d1806763650c1bb8`.

The content-free summary records `candidate_status=active`,
`live_eligible=false`, and
`provider-free-pass-pending-fresh-independent-review`. It names no private path.
The harness directory, harness files, source, wheel output, owned cache,
runtime, and summary were restored to owner-read-only modes. Writable scratch,
live-state, bytecode, and XDG roots are empty.

## Reproved package, receipt, and operational identities

The isolated CPython 3.13.0 runtime again proved exact distribution/module
version, the sole `buoy = buoy_search.entrypoint:main` console entry point, 83
installed distribution files, exact production hashes, schema-v3 active
routing revision `active-anchor-e559a8aa-v1`, exact BGE/MiniLM routing bindings,
executable version/help, module help, strict receipt canonical round trip,
noncanonical/wrong-shape/invalid-UTF-8 rejection, exact dataset SHA-256
`29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`,
and exactly one content-free case ID
`m01-dagster-turbopuffer-quality`. The installed-file path/content inventory
SHA-256 under the supplemental canonical scheme was
`56e5b871e91d7d1da6c816cac9c6b8f4f224c7a5f4f9ae6361bd2f3cba9c0e1d`.

The exact four-module fake-only installed-wheel suite passed 91/91 with a model-
library import blocker. Imports resolved only inside the retained runtime; no
ambient editable source, user package, global package, or `PYTHONPATH` supplied
the installed product.

The existing UV cache was read only for equality proof. Its before/after
manifest remained exactly 1,314,401 entries: 170,905 directories, 1,139,272
regular files, 4,224 symlinks, zero other types, 32,974,101,113 regular-file
bytes, supplemental manifest SHA-256
`3ede14ff010c83acefa6e028c66d223c33997c5a7a2b25f526e9810070482c8e`.
No cache lock, write, build, install, clean, prune, repair, or index operation
ran. The retained owned cache, runtime, source, and dist identities remained
exactly equal before/after.

Raw-filesystem telemetry equality passed without opening any database or API:
37 entries, 11 directories, 26 regular files, 9,468,291 bytes, supplemental
manifest SHA-256
`b0908ca57ec8acb4cb4c44d2043c1ec30a15bf64d1555e903f674f51412aecba`.
The intended credential source remained one regular nonsymlink file with exact
presence/type/metadata equality; its value was never opened, read, sourced,
copied, printed, or hashed. Credential environment inspection recorded names'
presence only and read no value.

The task baseline before this supplemental evidence was clean at HEAD
`80249751a7ad4d9449b18d81c0262425b235ba9c`, tree
`6ed42d4c222ae68c94bb3b52615e0f923ad9afe5`, on exact task ref
`refs/heads/work/provider-invocation-receipts-execution`. The 67-entry worktree
inventory SHA-256 was
`ff8b29423c79d53739a04c4dda792df9fdfe8903ac28c328fae15ef75a683081`.
The retained source remained detached/clean. Content-free process guards found
zero candidate build/install, harness, telemetry-writer, or related surviving
processes.

## Prohibited access, cleanup, and disposition

No credential value, model-library import during provider-free validation,
model construction/load/inference, provider client, DNS, TLS, network, catalog
or content operation, telemetry database/store/API/command, retrieval, preview,
global install/tool, build/rebuild, source/ref mutation, or live command
occurred. No receipt, query, namespace, content, result, command output, raw
error, credential, or private path was retained. Correction diagnostics and all
temporary validator/test outputs were deleted.

**CANDIDATE-DUAL-MODEL-PREPARED.** The exact immutable candidate is provider-
free prepared for the two production models and remains active pending a fresh
independent exact-candidate PASS/GO. This record is not that review or GO. The
dependent reviewer must bind this supplemental evidence commit/tree, the exact
wheel, both cache manifests, and the retained harness/summary identities before
phase 2 can become eligible.

This evidence proves only provider-free filesystem, package, fake receipt, and
construction-guard behavior. It proves no provider behavior, physical wire
send, SDK retry, billing, cost, or rate-limit effect.
