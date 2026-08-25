Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/2026-08-24-install-v0-6-3-and-run-telemetry-pilot.md, .10x/decisions/one-time-v0-6-3-global-install-and-telemetry-pilot.md, .10x/evidence/2026-08-24-buoy-v0-6-3-release-and-install-preflight.md

# V0.6.3 Install and Telemetry Pilot Preparation

## Preparation boundary

Preparation ran from clean `work/v0-6-3-telemetry-pilot` at active-ticket
commit `1cae2e1b5aadbf2dc100f3fba64433420dd14ca0`. All build, validation,
rehearsal, raw output, and command-binding artifacts remain in one owner-private
mode-0700 temporary root outside the repository. The detailed canonical
preflight report is mode 0600 and has SHA-256
`c92ab3492126f13d8bfd2f4fa094874b268244a96f7ac8c573aa2d1255eefc07`.
Its private path and child artifact paths are deliberately withheld from this
record and handed only to the sequential executor.

No global-tool replacement, rollback, real-home telemetry status/database
inspection, migration, retrieval, flush, provider/model service, credential
read, model-cache mutation, ref/GitHub mutation, or release mutation occurred.
Global-install, all three retrieval, and flush authorities remain unconsumed.

## Release and source revalidation

Fresh read-only local, remote, and GitHub checks reproduced the governing
release facts:

- `develop@4171555a81376b66cf5bf8cb51b1835bbf19129f`;
- `main@4c0a04a443ddf792db9089242bca4d1e141db03d`;
- lightweight `v0.6.3` resolving directly to that exact `main` commit;
- tree `5c0da1521f4f82fb65dad12b262e2daa868242bc`;
- public non-draft/non-prerelease release with zero attached assets; and
- successful exact push CI runs `32789880349` and `32789892473`.

An owner-private no-hardlink local clone was detached at exact tag/commit/tree
and remained clean after build. Exact package source retained:

- CLI SHA-256
  `90e7b2ddf7bbde2daaf0ccd78aa2a779d9e61946a8b7f7ae8f3512dec431ebf9`;
- entrypoint SHA-256
  `dd2f8b33a3e73c051f1cd95c6478be13c71985ca3fae34b6e0daf80fce56e089`;
- telemetry-envelope SHA-256
  `e1681c4c4dab0909270127fbb7b5eeffb7ea99864ca994cda406cac9c6e76b47`;
  and
- routing-artifact SHA-256
  `62ec1fe8cb7e49247c24b633379a6b2553475bc0e25ce846998ea5dd77df8cf5`.

The approved dataset remained exact at SHA-256
`29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`.
Private workload values were not extracted or read during preparation.

## Candidate artifact and isolated acceptance

The offline build produced exactly one 721,944-byte, 77-member safe regular
wheel, `buoy_search-0.6.3-py3-none-any.whl`, SHA-256
`dc9080badd619c5b95b31853a11a8c694d79699a0a4ad177c754c15acdb51b0b`.
It has 72 package members, no duplicate/traversal/absolute/symlink member, exact
name/version `buoy-search 0.6.3`, and sole console entry point
`buoy=buoy_search.entrypoint:main`. Its complete wheel member-manifest SHA-256
is `92c1a874631db93684660ca75bc31914488b27fe4c20362aff08ab67938b2e44`.

A frozen no-project dependency export is 184,489 bytes with SHA-256
`4872cfbadf1281244d8a0c21f7abc3c68b3fc4c4c011da1a59652887c9aef1ec`.
The isolated Python 3.13 candidate environment contained 109 compatible
distributions; its content-free inventory SHA-256 is
`c8daf722468322527a152fa127024f3191db3fc0c07d55ac75f4ca6ac7563568`.
All dependencies passed `uv pip check`. Installed candidate metadata/module/CLI
reported exact `0.6.3`; all 82 installed distribution files had manifest
SHA-256
`3d2a0c53769d2baf511c12bca9227e6c7934c3b32095c9ffc9da3fd223486017`
and reproduced the four source identities above.

Version, top-level help, telemetry help, and read-only telemetry status passed
in a fresh isolated home. Status reported output schema 2, disabled collection,
absent store/queue, idle writer, and created no `.buoy` state.

## Global baseline and rollback

The user-global uv-managed baseline remained
`buoy-search 0.6.2.dev2+g796f7384e` on Python 3.13.0 with sole entry point
`buoy=buoy_search.entrypoint:main`, 82 installed package files, and 107
compatible distributions. Its complete content-free baseline JSON SHA-256 is
`2db4501818b6bd01a327d25d4a7decc965307e6912f2d5a50d184237402a6da2`;
installed distribution-manifest SHA-256 is
`86dd1192f28930d9d216d54e5e337323ef7fc1a25d9c669faa5c4cd9728d7afc`;
and complete uv-tool-list SHA-256 is
`c5b482c26a34ba5a4af40c34a8fdd9bdd06a84c79b095de59f65e08b066ca399`.
The non-Buoy tool inventory has SHA-256
`755af35f6377abfe09a308d096f136d0dd09097ca5889d8c6f5ddfaf19231386`.

The exact old source commit now naturally resolves to later tag `v0.6.2`, so
the rollback build used Hatch-VCS's supported explicit version override to
recreate the observed installed version without changing exact commit source.
The resulting 697,995-byte, 77-member wheel has SHA-256
`f14e2f8abebe4b575f30ffecf0549a19e67ece2ee4212e7436fdf9fc45d54ae8`.
All 72 package members are byte-identical to the installed old package, and
version, entry point, CLI, entrypoint, envelope, and routing-artifact identities
match the baseline.

Exact forward and conditional rollback command files remain private. Their
SHA-256 values are respectively
`4af7e81124dba21365d395af91e0c5cdd16939538d6f345953648b7883c566a4`
and
`b576b1eb20818bb22e018659c150a41b18465725b03ce23cc0f177123aab3d8b`.
Both commands were rehearsed successfully against a private uv-tool root:
forward produced exact `0.6.3`, then rollback restored exact
`0.6.2.dev2+g796f7384e`. Both rehearsals were offline and left the global tool
unchanged.

## Remaining execution gates and limits

The complete three-root model-cache manifest retained 159 entries and SHA-256
`c395f5807452ede94efade87f5be77c0492911e6ac5936a85ce9aaf72ac4263f`.
The intended repository credential source exists, but preparation neither
opened nor sourced it. A process snapshot found zero independent uv-tool
installation, telemetry writer, or telemetry migration processes.

The sequential executor must freshly rebind the private report, artifact,
command, global-baseline, model-cache, ref, and process identities before the
one global replacement. Only after exact post-install acceptance may it inspect
the real telemetry status and consider provider access. This preparation does
not prove current real-home telemetry state, future provider results, physical
transport-attempt count, or post-install invariance.
