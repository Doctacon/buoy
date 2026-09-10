Status: recorded
Created: 2026-09-10
Updated: 2026-09-10
Relates-To: .10x/tickets/done/2026-09-10-buoy-mcp-server-plan.md, .10x/tickets/done/2026-09-10-implement-buoy-mcp-server.md, .10x/tickets/done/2026-09-10-document-and-verify-buoy-mcp-installation.md

# Buoy MCP Parent Acceptance Evidence

## Target and procedure

Parent inspection and provider-free verification on 2026-09-10 in
`/Users/crlough/Code/personal/turbo-search.worktrees/buoy-mcp-server`, branch
`work/buoy-mcp-server`. Inspected head was
`9efef60db26031eb628b8e3bfcc808720989ec38`; tested product commit is
`89cecb2ed0bf5279b0bbedb5cc42cd342d2885a0`, tree
`39c1cde1da1d60cbe3b3465465bb6f80fc798d96`. Later changes are record-only.

The parent re-read the three active MCP specs, both child acceptance lists,
current adapter, CLI/help/packaging/CI/README diff, consumer docs, material
fake-backed parity/input/lifecycle assertions, installed-smoke implementation,
both independent reviews, child evidence, and final raw suite logs.

Read-only `git ls-remote --heads origin develop` reconfirmed
`db5e8e1597e908c30fff76ec2aba565f1e2fbcbc` as current develop. The task is based on
that commit. `git diff --exit-code 89cecb2 HEAD -- src tests docs README.md
pyproject.toml uv.lock .github` was empty; saved final-source validation has not
been invalidated by later evidence commits. No commit/tag/version override,
integration, push, release, or client registration was part of these checks.

## Parent-observed artifacts and reruns

Raw parent evidence: `.10x/evidence/.storage/buoy-mcp-parent/`.

- Independently recomputed SHA-256 and sizes of retained wheel/sdist bytes;
  compared them with the original disposable build outputs; inspected archive
  members without extracting them; verified packaged adapter bytes equal current
  source and sdist MCP docs equal current docs.
- Wheel: `189dc4da39dc5a602f9e59483e6bf9188437bbf1255d1bcd599102d97f2bca60`,
  773337 bytes. Sdist:
  `b87cf4eb5e078b9e16292a973b21f61e386a689ebdc2711a068773faf7917418`,
  1420298 bytes. Both are development version `0.5.2.dev131+g89cecb2ed`,
  bound to the tested product commit, not the later record-only closure head.
- Recomputed all nine original-worktree preservation entries from the original
  preparation manifest: eight hashes match and the former ticket remains absent.
- Directly read final suite logs: CPython 3.11.10 reports 1,342 tests OK in
  135.455s; CPython 3.13.0 reports 1,342 tests OK in 134.217s. These are retained
  worker command results, not a claim the parent repeated both broad suites.
- Independently reran the source-inspected installed smoke against the same
  wheel in all four existing isolated environments: base/extra on both Python
  versions. Command shape (all values fixed to the recorded disposable roots):

  ```text
  env -i PATH=/usr/bin:/bin HOME=/tmp/bmi.FsHuj7/h HF_HUB_OFFLINE=1
    TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
    /tmp/bmi.FsHuj7/{base,extra}{311,313}/bin/python
    tests/core/mcp_installation_smoke.py --mode {base,extra}
    --wheel /tmp/bmi.FsHuj7/dist/buoy_search-0.5.2.dev131+g89cecb2ed-py3-none-any.whl
  ```

  Every command exited 0. Reports identify correct non-editable wheel origin,
  matching installed module/metadata/protocol version, base absence of MCP,
  exact optional SDK 2.2.0 in extra installs, and no runtime assets. Separate
  stderr files are empty. Temporary per-smoke homes were absent afterward.
  Extra runs used the fail-closed provider/model/network/child/dotenv guard and
  real SDK/raw-wire discovery, invalid calls, EOF/SIGINT/SIGTERM shutdown.
- `git diff db5e8e1 HEAD --check` and current `git diff --check` passed.

`artifact-and-preservation-check.json` records static checks; the four
`installed-{base,extra}-{311,313}.json` files and empty `.stderr` companions
record parent process results. Actual valid retrieval/catalog content behavior
is supported separately by fake-backed CLI parity, not by these invalid-input
installed checks. No live account or real-model retrieval was authorized/run.

## Criterion-to-evidence map

| Ticket criteria | Evidence and inspected assertion |
| --- | --- |
| Runtime 1: launch/help/optional packaging/discovery | Runtime evidence; installed base/extra identities and parent reruns; CLI/CI diff |
| Runtime 2: exact schemas/argv and invalid-input containment | `test_fixed_argv_and_value_containment`, `test_invalid_inputs_never_launch_and_do_not_echo_values`, discovered-schema tests |
| Runtime 3: actual CLI parity and outcome preservation | `test_actual_catalog_cli_parity`, `test_actual_retrieve_cli_provider_model_parity`; current CLI orchestration remains unchanged |
| Runtime 4: real inert stdio round trip | Source raw-wire/official-client tests and four parent installed reruns with guarded extra processes |
| Runtime 5: failures/privacy/no retry/cleanup | Error/warning sentinel matrix and actual cancellation/EOF/signals/interpreter tests; installed signal reruns |
| Runtime 6: mandatory CI extra and regressions | Inspected additive CI diff, final 1,342-test logs on both versions, retained lock/ranking/promotion/C6 logs |
| Runtime 7: independent review and truthful evidence | `.10x/reviews/2026-09-10-buoy-mcp-runtime-review.md`, pass with no required corrections; final artifact layer completed by installation child |
| Installation 1–4: source setup, client example, tools, side effects | `docs/mcp.md`, one-link README diff, actual discovered-schema/doc tests, retained source-launch check |
| Installation 5–6: distributions, four installs, no hidden operations | Retained archives/digests, child installed reports, independent parent hashing and four actual installed reruns |
| Installation 7: final regression/lock/contracts/hygiene | Both final 1,342-test logs, unchanged product diff since tested commit, recorded lock/ranking/promotion/C6/base-data results, parent diff check |
| Installation 8: independent review and handoff/preservation | `.10x/reviews/2026-09-10-buoy-mcp-installation-review.md`, pass; parent hashes, branch/base/head and artifact checks |

## Review disposition and retrospective

Both independent reviews have no required findings; the parent found no material
MCP spec drift or weaker substituted assertions. The original source/full-test
and final installed-artifact evidence are correctly distinct. No residual risk
was silently converted into a passing test.

The exact SDK pin/private serving seam is retained under the already recorded
supervisor-approved compatibility repair, with upgrade/removal conditions in
`.10x/knowledge/buoy-mcp-sdk-compatibility.md`. Stale editable package metadata
and its separation from wheel identity are preserved in
`.10x/knowledge/reproducible-installed-wheel-evidence-binds-version-lock-and-cleanup.md`.
These are the useful learned constraints; no speculative cleanup/upgrade ticket
is opened merely to restate the accepted pin.

The workflow WebSocket failure happened after a committed runtime checkpoint;
Git/source/raw evidence were preserved, and recovery restored attestation before
review. Original failed workflow `0aa4ba70-e2f0-4eaa-b29a-a698ece4d229` is not
reported as successful. Successor `6fcdfacb-b899-4e07-ba15-43d170274dee` completed
both tickets' execution/review stages under mission
`93525524-681e-4ded-9441-0e2f57d52091`.

## Cleanup and limits

After independent inspection and parent reruns, checked for surviving executables
under the exact owned disposable roots, found none, removed
`/tmp/bmi.FsHuj7`, `/tmp/buoy-mcp-runtime.LJClud`, and `/tmp/bm.5e9w`, then verified
literal absence. `cleanup.json` records this. Archive bytes, raw evidence and
source helper scripts remain committed; task worktree and original checkout
remain. Earlier records saying environments were retained describe the earlier
review window and are superseded for current retention by this observation.

No hosted CI, Windows run, live provider/model validation, deterministic rebuild,
global installation, client registration, release, push, or merge is claimed.
Those actions are outside the approved delivery, not unowned incomplete work.
Any later integration must still satisfy the existing exact-head hosted-CI and
review gates; no integration action is authorized by this acceptance record.
