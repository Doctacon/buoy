Status: recorded
Created: 2026-08-25
Updated: 2026-08-25
Relates-To: .10x/tickets/2026-08-25-prepare-provider-invocation-receipt-final-recovery-candidate.md, .10x/decisions/one-time-provider-invocation-receipt-final-recovery.md, .10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md

# Provider Invocation Receipt Final Recovery Candidate Preparation

## Activation and repository authority

Preparation began only after separate activation commit
`38e3e1448259c64012efd743de68e80b1b4da361`, tree
`b74875eb4b034b67efc263fbc4c4b54d635c5a96`. That activation bound clean
pre-activation HEAD `68ee19ffcca3bc9178a5c7335f6d8747f925728d`, tree
`54dcb5e9a1b00f7b38e5635da59acc3c5044c58f`, branch ref
`refs/heads/work/provider-invocation-receipts-execution`, and the complete
67-worktree inventory.

Provider-free preparation finished against the clean activation commit on that
same branch and registered task worktree. Its final pre-evidence worktree
inventory had 67 entries and SHA-256
`9790dd9be47bd168a023afb3e041fe79415badf6627ffb4a6f66c9186c549110`.
The task status was empty. No source-repository ref or registered worktree was
created, moved, or changed by preparation.

## Exact VCS-aware source

One owner-private mode-0700 root received one no-hardlink local VCS-aware clone.
The clone retained Git metadata, was detached and clean at exact commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`, before every build and at final
retention. No version override, synthesized tag, ref creation/update,
metadata-free export, source patch, or alternate source was used.

Exact source SHA-256 checks passed:

| Path | SHA-256 |
| --- | --- |
| `pyproject.toml` | `f80f4c53b5a6e1fe15e79abf31b40cdf529336a28144cec085ef1c7749861c22` |
| `uv.lock` | `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254` |
| `src/buoy_search/_provider_invocation_receipt.py` | `73361cde0ad7fad2906d01c10a7044f1a7ff34d28425e987f4265e7f60404349` |
| `src/buoy_search/retriever.py` | `89aeb5db61a1997f127db2ebe651beb9f184d4358e0e0cd3d98921713c9b613d` |
| `src/buoy_search/remote_catalog.py` | `3d859a21c257f7edaf113593aa486defdc78d1c89d45367811d0ac9ce991399d` |
| `src/buoy_search/cli.py` | `c6b575e160c5379b8a7214b3434a06d47864f0414e1478f44bcddeff313609ce` |
| routing calibration artifact | `79c780a5c3ffebfe5569d463663c30d681cf224aec3ddfb1e03202641b97ed1e` |
| automatic multi-corpus dataset | `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b` |

The retained read-only VCS clone has 1,630 content/type/mode/link-manifest
entries, 33,617,577 regular-file bytes, and manifest SHA-256
`1dcba3f9e99f75545bb028da305c118120c23159c415fb49adf96855c22f08d8`.

## Owned UV cache and source-cache equality

The existing UV cache was used only as a read-only seed source. Before seeding,
a content/type/mode/link manifest covered 1,314,401 entries: 170,905
directories, 1,139,272 regular files, 4,224 symlinks, zero other types, and
32,974,101,113 regular-file bytes. Its SHA-256 was
`f10cbb3e1fcc081e290078f327494bd8336d05091242a1efd152ee526b863868`.

Only platform-applicable exact locked runtime material and pinned/transitive
build-backend material were copied into the distinct owned cache. Twenty-one
lock package families that are inapplicable to CPython 3.13 on macOS arm64 were
omitted. Build, resolver, installer, runtime, bytecode, temporary, XDG, and
harness writes were directed to owned state under strict offline/no-download
controls.

After all preparation and seed reads, an independently regenerated source-cache
manifest was byte-identical to the pre-manifest: the same counts, bytes, types,
links, and SHA-256 above. This proves source-cache content/type equality. File
access times were intentionally excluded and **no atime equality is claimed**.
No source-cache lock, prune, clean, repair, index, or write operation ran.

After removing unused copied build candidates, the retained read-only owned
cache has 37,194 entries, 1,475,179,180 regular-file bytes, and manifest SHA-256
`72242bedb1fca7dc36db124c1a6608e40c63102675ac5e3b9353408ca6b2c11d`.

## Iterative preparation ledger

The frozen offline lock check passed with 157 lock packages. Provider-free
iteration was bounded as follows:

| Stage | Generic outcome |
| --- | --- |
| initial platform-aware cache seed | corrected platform-incompatible omission classification |
| wheel build 1 | isolated build index metadata incomplete |
| cache correction 1 | required simple-index metadata copied read-only into owned cache |
| wheel build 2 | isolated transitive build-backend material incomplete |
| cache correction 2 | required transitive build material copied read-only into owned cache |
| wheel build 3 | exact candidate PASS |
| installed validator 1 | corrected runtime-symlink identity assertion |
| installed validator 2 | PASS |
| version-output assertion | corrected expected program label; command itself passed |
| live-harness static assertion | corrected wrapper-literal matching; construction unchanged |
| process guard assertion | corrected unrelated command-name substring matching |

All corrections changed only owned cache, runtime, validator, or harness
material. No source, test, specification, lock, routing artifact, dataset, model
cache, telemetry filesystem, credential source, repository ref, global tool, or
candidate byte changed. All raw failure/build/install/help/test diagnostics and
correction scripts were deleted before retention. No correction diagnostic
remains.

## Exact accepted wheel and inherited package safety

The accepted output directory contains only one regular nonsymlink wheel and the
established optional regular nonsymlink one-byte uv `.gitignore` marker. It
contains no sdist, second wheel, directory, link, socket, or other entry.

| Identity | Exact value |
| --- | --- |
| Filename | `buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl` |
| Version | `0.5.2.dev87+g0b27c4eaa` |
| Size | `730602` bytes |
| Reviewed members | `78` |
| SHA-256 | `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87` |

Only archive-name count was read to confirm 78 entries. No novel archive
member-type classifier was authored or run. Exact digest, size, filename, and
source identity cryptographically inherit the reviewed inventory, path/link
safety, metadata, sole entry point, routing/source equality, and source-to-wheel
evidence from
`.10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md`
and its independent PASS review.

The retained read-only output has three manifest entries, 730,603 regular-file
bytes, and manifest SHA-256
`cad817f29d38625b99be04b6474c817dd726fea6af7f2e4e9f0d1738ff0907f0`.

## Isolated installed-package and provider-free validation

The exact wheel was installed offline and without dependencies from any ambient
checkout into a CPython 3.13.0 isolated runtime whose dependencies were first
installed from the exact frozen lock using only the owned cache. `uv pip check`
passed all 109 installed distributions. Their content-free name/version
inventory SHA-256 was
`23a3d4637cadaf265d744a5be3abe751187081b7721121347e121bf2342cdd82`.

Installed validation passed:

- exact distribution and module version `0.5.2.dev87+g0b27c4eaa`;
- sole distribution console entry point
  `buoy = buoy_search.entrypoint:main`;
- 83 installed distribution files with content-free file inventory SHA-256
  `25438f92aa5d794371382c3e6f6e9d9fb66d820bfde6bb07be479130f419f633`;
- exact installed private-receipt, retriever, remote-catalog, CLI, and routing
  artifact hashes listed above;
- production routing loader acceptance of schema version 3, revision
  `active-anchor-e559a8aa-v1`, active mode, exact CLI receipt, exact routing
  model, and exact routing-model revision;
- executable version, executable help, module help, and private receipt import;
- strict canonical empty-receipt round trip plus noncanonical, wrong-type,
  missing-key, and invalid-UTF-8 rejection;
- no user site, ambient editable source, `PYTHONPATH`, global package, or global
  Buoy supplied the imports; and
- no model library was loaded by installed validation.

The established four-module fake-only receipt suite ran against the installed
wheel, not the source package, and passed 91/91. It covered strict lifecycle,
canonicalization, invalid models, content attempt grammar, catalog source-order
validation, concurrency, caller isolation, observer faults, and private
activation without provider, model, retrieval, telemetry-store, credential, or
network access.

The retained read-only runtime has 30,750 content/type/mode/link-manifest
entries, 1,227,194,627 regular-file bytes, and manifest SHA-256
`cb87fb119b62d656ff21d5d6a53db2d76091b265531c58730bb82b41c2526faa`.

## Operational pre-state bindings without operational access

The approved dataset hash above passed and exact case
`m01-dagster-turbopuffer-quality` was privately extracted exactly once without
retaining its query, namespace, card, content, or result values.

Filesystem-only bindings passed before and after preparation:

- exact cached model root and lock content/type equality;
- exact model ref
  `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- complete 14-entry snapshot asset set (15 entries including the root), with
  manifest SHA-256
  `7a70efaebbee675b46251586579b7ebeda3e671316d31662b74298b61f0b0df4`;
- exact model-root manifest equality at 44 entries and SHA-256
  `36429cd91318e9d58bac2f794ba7525c85fefce1de6f7879c78348575d733501`;
- exact model-only hub content/type equality at 142 entries, 1,561,493,324
  regular-file bytes, and SHA-256
  `702b7ee10272448aa144a69e1dff88afd5fa745be0c2e14ad4da28731a46c4c3`;
- a complete 159-entry three-root type/target manifest with SHA-256
  `168f49fb1a90237218821ae4228c2260763a5d1662f31e924b9b77d682ae1e4e`;
  credential-bearing non-model file content was deliberately not read, while
  exact model asset content is covered by the separate model manifests above;
- static source proof of model `BAAI/bge-small-en-v1.5`, exact revision,
  float32, local-only routing load, and unchanged production automatic-device
  selection without model construction or model import;
- real telemetry filesystem content/type equality by raw filesystem reads only:
  37 entries, 11 directories, 26 regular files, 9,468,291 bytes, and manifest
  SHA-256
  `17a0d310ad26937e06c57722d058aad86971c8efffd89ad4533fc2577c1422b1`;
  no telemetry database, store, API, command, status, migration, flush, writer,
  queue, receipt, backup, export, or purge behavior was opened or invoked; and
- intended credential-source presence/type/metadata equality as a regular
  nonsymlink file without opening, sourcing, reading, copying, printing, or
  hashing its value.

The historical 159-entry content-manifest SHA-256
`c395f5807452ede94efade87f5be77c0492911e6ac5936a85ce9aaf72ac4263f`
remains record-backed historical evidence. This preparation does not falsely
claim byte comparability between that historical manifest format and the new
credential-safe type/target plus exact-model-content split above.

## Guarded live harness construction

One private live harness was constructed but not run. Construction-only
self-check and static validation passed without credential, model, provider,
network, telemetry, or retrieval access. The harness:

- requires later exact `PASS/GO` plus 40-hex evidence commit/tree bindings;
- has an exclusive one-execution guard and a distinct marker written immediately
  before its only command call;
- removes inherited provider credentials before later private credential-source
  loading and removes every telemetry enablement afterward;
- fixes exact offline model identity and float32 while preserving production
  automatic-device behavior;
- privately extracts only the exact approved case/dataset at execution time;
- contains exactly one ordinary automatic
  `retrieve <private-case-value> --json` call, no preview, explicit namespace,
  alternate case, retry, or second command;
- uses the exact reviewed read-only automatic provider path;
- preserves generic original return/raise truth separately from receipt
  acceptance;
- strictly decodes and byte-identically re-encodes the terminal receipt;
- requires successful catalog outcome with invocation count at most 5, content
  invocation count at most 18, and every represented operation/attempt outcome
  exactly `success`; and
- retains no command output and writes receipt bytes only after complete
  acceptance.

Harness and wrapper SHA-256 values are respectively
`c68a65fe9ccb161a30c3854f42537c025e24fdf081cdfa5c126d75141cc8141f`
and `6e917b270cb803ca96ded4a46f3087465a16130d18afe59b8e065f6a4431c60b`.
The retained read-only harness has three manifest entries, 6,424 regular-file
bytes, and manifest SHA-256
`2f323d5103e645600ef9aa1f0030b313889a4601abf809e9c88b8004414fcb88`.
Its one-execution and command-start markers remain absent.

## Prohibited-access and side-effect inventory

Every build/runtime command removed inherited provider credential variables and
telemetry enablement, used private HOME/TMP/XDG/bytecode roots, and enforced UV,
pip, Hugging Face, and Transformers offline/no-download controls. No preview,
explicit retrieval, automatic retrieval, live command, provider client, DNS,
TLS, network, credential-value read, model construction/load/inference,
telemetry storage/API/command, global installation/tool replacement, release,
deployment, publication, push, or source-ref mutation occurred.

Content-free command-name process guards found zero independent candidate,
telemetry writer/migration/flush, uv build/install, or owned harness survivors.
The source clone remained detached/clean, the task repository remained clean,
the existing UV cache was content/type-identical, the model cache and telemetry
filesystem were content/type-identical, and the credential source retained
presence/type/metadata identity. Provider state was not accessed. No private
command output, receipt, partial ledger, raw diagnostic, or prohibited value was
retained.

## Immutable private handoff

The same complete accepted VCS-aware source, output, owned cache, isolated
runtime/dependencies/installed package, live harness, and empty dedicated live
state remain under one owner-private mode-0700 root. Accepted source, output,
cache, runtime, and harness are owner-read-only. Writable state is restricted to
empty owner-private runtime scratch and live-state directories.

The content-free handoff summary SHA-256 is
`2c1211d5be9ac5e866a51e9cb3c99a0ea85dcd7937fd1e1506a333a271bfb4cf`.
It contains no private path. The handoff location is deliberately withheld from
durable records and is supplied only to the sequential orchestrator.

## What this supported before independent review

This originally supported provider-free candidate **PASS** for the exact wheel
and then-retained handoff, pending independent review. Independent review later
returned NO-GO. The current disposition and corrected retained harness
identities are recorded in
`.10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-candidate-repair.md`,
which supersedes this record's candidate-PASS conclusion. The source and wheel
identities recorded here remain unchanged and valid.

This evidence proves only provider-free package and application-boundary fake
behavior. It proves no live provider behavior, physical wire send, SDK-internal
retry, billing, cost, or rate-limit effect.
