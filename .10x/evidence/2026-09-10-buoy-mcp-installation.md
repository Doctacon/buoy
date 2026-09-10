Status: recorded
Created: 2026-09-10
Updated: 2026-09-10
Relates-To: .10x/tickets/done/2026-09-10-document-and-verify-buoy-mcp-installation.md

# Buoy MCP documentation and installed-wheel acceptance

Review readiness: ready for independent review; ticket remains active.
Branch: `work/buoy-mcp-server`
Tested source commit: `89cecb2ed0bf5279b0bbedb5cc42cd342d2885a0`
Tested source tree: `39c1cde1da1d60cbe3b3465465bb6f80fc798d96`
Runtime owner/review: implementation `dba28f0`, recovered at `f9ddf19`; parent
provided the independent runtime PASS before this dependent execution.
Raw evidence: `.10x/evidence/.storage/buoy-mcp-installation/` (below, `E`).

## Bounded changes and acceptance mapping

1. `docs/mcp.md` documents verified source-checkout `uv sync --locked --extra mcp`
   and `uv run --locked --extra mcp buoy mcp`, with optional SDK pin and launch
   behavior. It explicitly says MCP is unreleased. README differs from the
   incoming worktree by exactly one Learn more link; its v0.6.4 release example
   is unchanged. The original checkout's separate v0.6.5/portable-skill work was
   not copied, staged, edited, or overwritten.
2. The sole JSON example is the approved agent-neutral `buoy` / `["mcp"]` launch,
   with no stored credentials. Docs explain executable resolution, absolute
   checkout-venv paths, client environment differences, and no promised JSON
   shell-variable interpolation. No client files were edited.
3. All three signatures/defaults and strict validation match discovered schemas.
   Docs retain automatic/explicit routing, global top-k, cited structured/text
   JSON, partial/abstained/inconclusive outcomes, exact catalog-show lookup,
   canonical catalog search, enabled/live versus all-card filtering, safe errors,
   hidden vectors/source-passage banks and visible reviewed examples. The new
   source-named schema test compares names, fields, defaults and required fields
   against the actual SDK discovery result; runtime protective tests are intact.
4. Docs distinguish provider-free initialization/discovery from potentially billed
   valid reads and retained local inference/opt-in telemetry effects. Environment
   credentials, no auto-loaded `.env`, no added ACL/write/log/download workflow,
   one invocation/no adapter retry and owned-child versus shared-worker lifecycle
   are explicit. No filesystem-free or cost-free live retrieval claim is made.
5. Built a clean committed wheel and sdist outside the worktree, inspected both,
   and installed **that same wheel** into four new non-system-site virtualenvs:
   base/extra on CPython 3.11.10 and 3.13.0. Installed module path is under each
   environment's site-packages, direct URL is the wheel (not editable), installed
   adapter bytes equal the wheel/source, and module/metadata/protocol versions
   agree. Member lists and metadata are retained. Both artifacts contain the
   adapter/entrypoint/optional extra, exclude `.10x`, Git/environment/runtime and
   removed service/frontend assets; sdist includes the new docs. Existing package
   settings, exclusions and original-checkout skill manifest remain unchanged.
6. Base installed normal CLI/module help and MCP help pass; MCP is unimportable
   and actual launch exits 1 with empty stdout and a traceback-free
   `buoy-search[mcp]` instruction. Extra installed official SDK client and raw
   stdio checks pass initialize, exactly-three-tools discovery, invalid calls,
   empty resources/prompts, and disconnect. Raw wire additionally passes EOF,
   SIGTERM and SIGINT with stdin still open, exit 0, protocol-only stdout and
   empty stderr. These are actual console-entrypoint processes, not source-path
   substitutes. New installed coverage is a required additive CI build step;
   every previous base tokenizer/data assertion remains byte-for-byte intact.
7. Full suites on both installed-extra interpreters pass **1342 tests each**,
   including all existing MCP lifecycle/parity protections and three new docs/CI
   schema tests. Ranking contract, explicit-base promotion, C6, dependency lock
   and exact original CI base tokenizer/data smoke pass on both interpreters.
   No new real-model parity or live evaluation campaign was performed.
8. This evidence and raw artifacts support independent review; the dependent
   review itself is still the parent's required gate. No ticket is closed.

## Exact artifacts and versions

Version (unreleased development build): `0.5.2.dev131+g89cecb2ed`.

| Artifact | SHA-256 | Bytes |
| --- | --- | ---: |
| `buoy_search-0.5.2.dev131+g89cecb2ed-py3-none-any.whl` | `189dc4da39dc5a602f9e59483e6bf9188437bbf1255d1bcd599102d97f2bca60` | 773337 |
| `buoy_search-0.5.2.dev131+g89cecb2ed.tar.gz` | `b87cf4eb5e078b9e16292a973b21f61e386a689ebdc2711a068773faf7917418` | 1420298 |

Byte-for-byte copies of both artifacts are retained in `E`, in addition to the
isolated build output. `artifacts-preservation.json` binds commit/tree, hashes,
member counts (95 wheel / 202 sdist), metadata and preservation facts. Extra
versions on both interpreters: MCP / mcp-types **2.2.0**, AnyIO **4.14.0**, Pydantic
**2.13.4**. uv **0.11.7**; macOS arm64. Installed version/source facts and complete
wire transcripts are in `installed-{base,extra}-{311,313}.json`; the repeated final
runs are in the corresponding `.log` files. Both runs passed, with empty separate
stderr files for the first run.

## Reproducible commands and results

Let `T=$(cat E/environment-path.txt)` (`/tmp/bmi.FsHuj7`),
`OLD=/tmp/buoy-mcp-runtime.LJClud` (inspected prior disposable setup),
`H=$T/h`, and `C=$OLD/cache/uv` (dependency cache only).
`prepare.sh` / `validate.sh` retain the exact commands and isolated environment.
Runtime/test commands use `env -i`, explicit PATH/HOME/cache/model-cache paths,
offline Hugging Face/Transformers flags, no credentials and no global PYTHONPATH.
The short HOME avoids the already-known POSIX worker socket path-length limit.

- `uv sync --locked --extra mcp --python 3.13` / `3.11`, with
  `UV_PROJECT_ENVIRONMENT` pointing at the prior disposable venvs: passed.
  Source command help passed. Reuse exposed uv's cached old editable VCS metadata
  (not a runtime flaw); `--reinstall-package buoy-search` refreshed the 3.13
  editable metadata to the committed version. `source-refresh.log` proves module
  and metadata agreement. Final broad acceptance uses the fresh **wheel**
  environments, not those reused editable installs.
- `uv run --locked --extra mcp buoy mcp </dev/null`: passed after refresh, exit 0,
  zero stdout/stderr bytes (`source-launch.*`). The normal documented launch is
  verified without leaving a running MCP server.
- `uv build --out-dir "$T/dist"`: passed (`prepare.log`), no version override,
  tag or release. Worktree had no tracked changes; only pending untracked evidence
  (`source-status.txt`). The ordinary ignored VCS version file was generated.
- `uv export --locked --extra mcp --no-dev --no-emit-project --output-file
  "$T/constraints.txt"`; `uv venv --python "$P" "$T/{base,extra}{311,313}"`;
  `uv pip install --python "$V/bin/python" --constraint "$T/constraints.txt"
  "$wheel"` or `"$wheel[mcp]"`: all passed (`prepare.log`). Package fetching was
  isolated and authorized; no provider/model fetching was performed.
- `"$V/bin/python" tests/core/mcp_installation_smoke.py --mode base|extra --wheel
  "$wheel"`: all four combinations passed twice. The helper's temporary
  PYTHONPATH contains only a standard-library safety hook, never Buoy source.
- `"$T/extra311/bin/python" -m unittest discover -s tests -p 'test_*.py' -q`:
  **1342 tests OK**, 135.455 seconds (`full-311.log`). Same command with extra313:
  **1342 tests OK**, 134.217 seconds (`full-313.log`). No skips reported.
- Both: `scripts/validate_ranking_contract.py` passed (`ranking-*.log`);
  `scripts/validate_ranking_promotion.py --base-ref
  db5e8e1597e908c30fff76ec2aba565f1e2fbcbc` passed (`promotion-*.log`): authority
  unchanged, zero production promotion baskets. Local develop is still that base.
- Both: `scripts/c6_syntax_forecast.py validate` passed (`c6-*.log`), preserving
  **tokenizer readiness=false** at the existing checkpoint, not claiming C6
  model/promotion readiness or warming a model.
- Both base wheel interpreters execute the CI's embedded Python **verbatim**
  (`base-data-*.log`): bundled tokenizer-only count 9, canary digests, 65-case
  routing dataset digest, calibration mode and empty promotion registry pass.
  The bundled tokenizer loader is offline; no model construction/download occurs.
- `uv lock --check` passed; explicit `--python "$T/extra311/bin/python"` and 313
  checks also passed (171 packages; `lock-*.log`). uv's initial default lock/export
  resolution selected installed CPython 3.14.7; the explicit acceptance checks
  above use the two required versions.
- `inspect.py`: passed. Proves metadata/artifacts/exclusions, exact one-link README
  diff, untouched tracked runtime/spec/packaging and preserved base-smoke code.
  Re-read only the nine authoritative original manifest paths: eight hashes and
  the old ticket's expected absence all match. No baseline recapture.
- `git diff --check`: passed. `installation-source.diff` retains the zero-context
  source/docs/test/CI delta for review. Initial focused docs run also passed all
  three tests; its unmodified padded diagnostic output is gzip-preserved as
  `docs-first.log.gz` for diff hygiene.

## Negative observations, cleanup and limits

Extra installed smoke rejects provider/model/dotenv/CLI-orchestration/worker
imports, socket connect/bind, command-child launch and `.env` reads during
initialization/discovery/invalid requests. The hook records any violation even
if an adapter catches it: no violation marker or runtime asset appeared. A fake
`.env` fixture was never read. Invalid input is not echoed. Every raw stdout line
is a protocol response; no extra bytes or finalization stderr remained. Real SDK
client disconnect and each raw-wire termination awaited process exit. Existing
runtime tests additionally prove cancellation of owned active CLI children and
retention of a separate shared-process sentinel; no shared real model was loaded.

All per-smoke HOME/guard fixtures are removed by context cleanup. The outer
isolated HOME and runtime cache are empty after validation. Disposable package
venvs/build output and the previously authorized dependency cache are retained
for independent inspection; they are not user installs or runtime assets. No
original checkout writes, credentials access, live Turbopuffer operations, model
downloads, global installs, client registration, release/tag/push/merge occurred.
Existing version tests create only their established disposable fixture repo tags.

Hosted CI and Windows execution are not claimed. The parent-approved exact SDK
pin/private cancellable-stdio serving seam remains unchanged compatibility debt.
This evidence commit changes only evidence/progress after the tested source
commit; it does not claim the VCS development version belongs to a later record
commit. Parent independent installation review and ticket closure remain required.
