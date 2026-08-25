Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/2026-08-24-recover-one-time-live-provider-invocation-receipt-canary.md, .10x/decisions/one-time-live-provider-invocation-receipt-canary-recovery.md, .10x/evidence/2026-08-24-provider-invocation-receipt-canary-preflight-failure.md

# Provider Invocation Receipt Canary Recovery Preparation Failure

## What was observed

Recovery preparation began only after the separate activation commit
`52cd91dc16299dbe93b751628581ef39802edf95`, tree
`25f05aa5aae1f786a9f736e4d5225703ef82f45e`. That activation bound the
independently passed recovery-authorization candidate commit
`4ea0ff771f0d5559ecb04e32f105c76ed0d5148c`, tree
`941360b413c28e5b6781c8e6abd60f4f50443ff3`, and exact reviewed source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`.

One owner-private mode-0700 temporary root outside the repository received one
archive export of the exact source without Git metadata, refs, a checkout, or a
worktree. Exact pre-build source SHA-256 checks passed for `pyproject.toml`,
`uv.lock`, private receipt, retriever, remote catalog, CLI, routing artifact,
and approved dataset. The frozen offline lock check passed with 157 resolved
packages.

Content-free pre-state checks also accepted:

- exact approved dataset SHA-256
  `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`
  and private extraction of approved case `m01-dagster-turbopuffer-quality`;
- intended credential source presence as a regular nonsymlink file without
  opening or sourcing it;
- the complete established three-root model-cache manifest at exactly 159
  entries and SHA-256
  `c395f5807452ede94efade87f5be77c0492911e6ac5936a85ce9aaf72ac4263f`;
- exact cached model ref
  `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, complete 14-entry snapshot,
  float32 configuration, and unchanged production automatic-device source
  posture without constructing or importing the model;
- a filesystem-only real telemetry identity with 37 entries, 11 directories,
  26 regular files, 9,468,291 regular-file bytes, and complete manifest SHA-256
  `058c392aef67a563d0b7c450f95c50650eb7d4267e25adda7d8063bc2df63402`;
  no telemetry database or API was opened; and
- zero independent candidate harness, telemetry writer/migration/flush, or uv
  tool-install process under the bounded process guard.

Exactly one wheel-only offline build command began once and exited zero. It was
not retried. Before the validator failure, independent wheel enumeration
accepted exactly one regular nonsymlink wheel, exact filename
`buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl`, exact size 730,602
bytes, and exact SHA-256
`42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`.
Complete output-directory enumeration accepted only that wheel and one regular
nonsymlink uv-generated `.gitignore`; the marker matched uv's established
one-byte `*` output behavior and was not counted as a distribution artifact.
The archive enumeration observed exactly 78 unique members before a mandatory
member-type assertion returned nonzero. No alternate inspector, corrected
assertion, validator rerun, build retry, or candidate substitution ran. The
sanitized failure category is `archive_member_type_validation_failure` within
`candidate_identity_validation_failure`.

## Stop boundary and cleanup

Preparation stopped immediately at the first nonzero candidate validator.
Complete wheel acceptance did not finish. No routing production loader or
validator, isolated runtime, package install, installed-package validator,
help/import/preview gate, private strict-receipt gate, device probe, model
construction, credential open/source/value read, telemetry store/database/API,
provider/network access, automatic command, global tool, release, deployment,
publication, push, or repository-ref mutation occurred.

The complete owned temporary root was removed, including the source export,
wheel, scripts, harness candidate, private manifests, and raw logs. Filesystem
absence was verified. No candidate/runtime/harness handoff exists and no live
GO may be sought. The blocked predecessor and its immutable failure evidence
were not changed.

## What this supports or challenges

This supports only that recovery activation preceded one exact source export,
one frozen offline lock check, one wheel-only offline build, one forward-only
candidate-validation failure, and complete owned-root cleanup before any live
or operational access. It also supports that the corrected independent wheel
and output-marker enumeration passed before the later member-type check failed.

It challenges every recovery criterion requiring complete 78-member type/safety
acceptance, metadata/entry-point/source/routing validation, isolated
installation, installed provider-free gates, complete preparation evidence,
retained immutable handoff, independent GO, or live execution. Under the
ratified no-retry recovery contract, the preparation attempt is consumed and
cannot resume.

## Limits

The partially checked wheel is not an accepted or retained candidate. This
evidence does not prove complete archive safety, package/routing authority,
installed identity, a live provider receipt, application-boundary invocation
counts, provider behavior, physical sends, SDK retries, billing, cost, or rate-
limit use. No receipt or partial ledger exists.
