Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md, .10x/decisions/one-time-live-provider-invocation-receipt-canary.md, .10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md

# Provider Invocation Receipt Canary Preflight Failure

## What was observed

Preparation began only after the owning ticket was activated in separate commit
`929e4db8f798148cabe45070cb1350e9c183844f`, tree
`87f9462052d6b6bd3c8a1c5373617d4d354bca93`. The exact done fake-only
dependency remained bound to independently reviewed source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`.

One owner-private mode-0700 temporary root outside the repository received one
no-hardlink local source clone detached at that exact source commit/tree. Source
status was clean. Exact pre-build checks accepted:

- `pyproject.toml` SHA-256
  `f80f4c53b5a6e1fe15e79abf31b40cdf529336a28144cec085ef1c7749861c22`;
- `uv.lock` SHA-256
  `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254`;
- final `cli.py` SHA-256
  `c6b575e160c5379b8a7214b3434a06d47864f0414e1478f44bcddeff313609ce`;
- private receipt source SHA-256
  `73361cde0ad7fad2906d01c10a7044f1a7ff34d28425e987f4265e7f60404349`;
- remote-catalog source SHA-256
  `3d859a21c257f7edaf113593aa486defdc78d1c89d45367811d0ac9ce991399d`;
- retriever source SHA-256
  `89aeb5db61a1997f127db2ebe651beb9f184d4358e0e0cd3d98921713c9b613d`;
- routing artifact SHA-256
  `79c780a5c3ffebfe5569d463663c30d681cf224aec3ddfb1e03202641b97ed1e`;
  and
- approved dataset SHA-256
  `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`.

The frozen offline lock check passed. Exactly one wheel build was invoked once
and succeeded without a build retry. It produced exact version
`0.5.2.dev87+g0b27c4eaa`, one 730,602-byte wheel with 78 members, and SHA-256
`42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`.

Candidate acceptance did not complete. A post-build wrapper included an
unrequired assertion that the output directory contain no auxiliary build-tool
file; the build tool had created its normal output-directory ignore marker, so
the wrapper returned nonzero after the wheel was already built. A subsequent
read-only candidate inspector also returned nonzero because its routing-identity
check expected a revision field at an unverified JSON location. No inspector or
build was rerun. The sanitized failure category is
`candidate_identity_validation_failure`.

The incomplete inspector had already accepted the exact wheel digest/size/name,
78 unique traversal-safe nonsymlink members, exact metadata version, sole entry
point `buoy = buoy_search.entrypoint:main`, and exact source-to-wheel hashes for
the CLI, private receipt, remote catalog, retriever, routing artifact, and
approved dataset. Those partial checks do not promote the wheel to an accepted
candidate because the required complete identity/preflight ledger did not
finish.

## Stop boundary and cleanup

No isolated runtime was created and no package was installed. Provider-free
help/import/strict-receipt validation did not run. The current 159-entry model
cache manifest and exact revision/assets were not accepted; no model was
constructed or imported through the candidate. The intended ignored repository
credential source was checked for file presence only and was not opened,
sourced, or read. No credential value was retrieved.

No real telemetry store/database was opened or queried, and no telemetry
command, writer, migration, flush, queue, receipt, or backup operation ran. No
automatic command began, so the one-time live provider authority remains
unconsumed. No provider client, catalog/content operation, model download,
network operation, global install, release, deployment, publication, push, or
repository ref mutation occurred.

The complete owned temporary root was deleted, including the source clone,
wheel, logs, scripts, and partial reports, and filesystem absence was verified.
The repository worktree was clean at the activation commit before this bounded
failure record was written.

## What this supports or challenges

This supports only that activation preceded preparation, one exact reviewed
source was exported, one offline wheel was built once, candidate validation
failed closed without rebuild or retry, no live command or external operation
began, and owned temporary artifacts were removed.

It challenges every canary-preparation acceptance criterion that depends on a
fully accepted installed candidate, current cache/ref/assets equality, bound
telemetry filesystem state, executable guarded harness, or executor handoff.
The ticket cannot resume under its no-rebuild/no-retry preparation contract.

## Limits

No live receipt exists, and no raw or partial receipt was produced or retained.
This evidence does not prove an accepted candidate, installed-package identity,
current model-cache equality, telemetry-store identity, provider behavior,
application-boundary invocation counts, physical sends, billing, cost, or
rate-limit use. A fresh candidate or preparation attempt requires separately
shaped and owner-ratified authority; this failure grants none.
