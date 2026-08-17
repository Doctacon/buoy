Status: pass
Created: 2026-08-17
Updated: 2026-08-17
Target: work/authorize-user-global-home-main-and-tool-replacement pre-review candidate
Ticket: .10x/tickets/done/2026-08-17-promote-user-global-home-defaults-and-replace-tool-once.md
Evidence: .10x/evidence/2026-08-17-user-global-home-main-promotion-and-tool-replacement.md
Decision: .10x/decisions/one-time-user-global-home-main-promotion-and-tool-replacement.md
Review: .10x/reviews/2026-08-17-user-global-home-main-promotion-and-tool-replacement-review.md
Verdict: pass

# User-Global-Home Main-Promotion Authority Review

## Exact reviewed candidate

Independent review bound exact base
`D0 = cd3f1bef4c9c4856c727f4891512278eafd82841`, sole parent
`B = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`, and tree
`8c6790ac8be55601b25c7b79aad17994b790a533`. The exact three-record
pre-review candidate was:

- decision blob `71f7fffb1252ba213aa55f16362fde95f6fbfd47`;
- active ticket blob `045df6afb74fb89348b69454228aed1717363e0f`;
- provisional evidence blob `83a9cebf70118108e9683b8778fee50a0c7bbf75`.

This review path is the sole permitted fourth record and is not self-hashed in
its own contents. No tracked or forbidden surface differed from `D0` before
this record was added.

## Findings

- PR #129 had exact base `B`, head
  `c1b76f329496358198af6a9af1a80a095418af1d`, successful CI run
  `32039880977` with jobs `95417652397`, `95417652864`, and `95417935994`,
  empty hosted comments/reviews/requests/threads, and squash result `D0` with
  the exact reviewed head tree.
- Current main `M = 7f7ddfe245e1e5b57946eb6ac10dcc01358559fc` has ordered parents
  `[4d1efc458fd13b270bf84984ffeb550d5b24fd04, B]` and tree
  `98cb3e56af4d867987d4e23f279f68fcf912e666`, exactly equal to
  `tree(B)`. `merge-base(M,D0) == B`; divergence is two main-only / one
  develop-only commits; neither tip is an ancestor of the other; `B..M` has
  no content diff; and the reviewed merge construction equals exact
  `tree(D0)` without conflict. The candidate correctly requires no ancestry
  bridge and no false `M`-ancestor predicate.
- Governing blobs remain unchanged: paused-publication decision
  `c94273e0978e53ca12ba47b22b68eb7634e22823`, protected-branch spec
  `041a02f0cbc8bc0e6a8539f21cbfba0712f0b7b3`, `AGENTS.md`
  `c58e599bad8ebe2e858c07d2199ea70af85b47aa`, global-home decision
  `8967497ff6cd531bf5dd0f4ebe98bff183c903ea`, global-home spec
  `0dd467b8e5431b2922a1410ca8c9dc43b64cdec7`, CI workflow
  `ff1aebdf2dd3dc7d1a6dd178bdf78a97e8d00630`, readiness workflow
  `ad8b8516d5c0961cda12664f6dac9c275935e202`, and paused Release workflow
  `e528e7501a86021ef1ad28174873647b911b04f2`. The prior one-time promotion
  decision is consumed/superseded at blob
  `ea837d1ba8544a57be3cf2248bb1c89ac79cc34b` and is not reused.
- The owner's later instruction is represented as a narrow single-use
  exception for one authority PR, one exact same-repository release merge, and
  one exact-main local `buoy-search` replacement. It does not resume
  publication or any unrelated authority.
- Final `D` stays unbound until this authority set squash-integrates normally.
  Release then fails closed on exact `M/B/D/P`, seven checks, independent GO,
  merge-commit method, `[M,D]` parents, tree equality, empty `D..R`, post-main
  CI/paused Release, and unchanged hosted inventories.
- The preliminary installed baseline independently matches the record:
  symlinked uv `buoy-search`, CPython 3.13.0, 104 distributions, version
  `0.5.2.dev33+g7f7ddfe24`, exact-M `direct_url.json` SHA
  `7d181c6d8d00e3d04682f95082ad93b062f47fdf18cbafb6b5a5e021f2908047`,
  CLI receipt
  `92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`,
  no installed `local_paths.py`, and absent real `~/.buoy`. Every fact must be
  freshly rebound before replacement.
- Exact-R build, one hash-bound wheel, locked runtime constraints, isolated-
  home smoke, precise command, and independent INSTALL-GO precede the one
  `uv tool install --force` invocation. Beginning it consumes authority;
  failure or uncertainty grants no retry, rollback, uninstall, or second
  invocation.
- Publication/tag/Release/provider/catalog/content/model/credential/protection/
  direct-push/force-push/old-asset/real-home/other-tool effects remain excluded.
  Closure is develop-only and grants no second main merge or installation.

## Validation

The source validator passed with dynamic versioning, paused publication,
`staged_release = null`, active routing artifact
`745cdb76c894ef1770f6daf3d303f2b6d0ba6905098924f1cb1a8fa40e738fea`,
and exact CLI receipt. Offline lock validation resolved 154 packages. Exact
scope, links/statuses, whitespace, diff hygiene, and forbidden-surface checks
passed. Review made no GitHub, provider, credential, build, or install mutation.

## Verdict

PASS for adding this review as the sole fourth record, committing only the
exact four-record candidate, pushing its task branch, and ordinary PR handoff
to `develop`.

This verdict does not itself authorize opening or merging the authority PR,
creating or merging the release PR, replacing the tool, publication, or any
excluded effect; every later phase remains conditional on the executable
ticket's exact gates. Any pre-review blob or path drift beyond this review
would require independent rereview.

## Time scope and closure backlink

This review's verdict remains scoped to the exact pre-PR authority candidate
and the then-future conditional gates described above. It is not retroactively
expanded into a review of PR #130, PR #131, the main merge, or the installation.
Their actual identities, effects, caveat, and final PASS are recorded by the
linked evidence and final execution review. Those later facts consume the
authority; they do not make this earlier verdict reusable.
