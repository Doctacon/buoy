Status: recorded
Created: 2026-09-10
Updated: 2026-09-10
Relates-To: .10x/tickets/done/2026-09-10-implement-buoy-mcp-server.md

# Buoy MCP runtime implementation evidence

Review readiness: ready for independent review (ticket remains active)
Owner: `.10x/tickets/done/2026-09-10-implement-buoy-mcp-server.md`
Branch: `work/buoy-mcp-server`
Base: `db5e8e1597e908c30fff76ec2aba565f1e2fbcbc` + approved record `6c9b6d8`
Raw evidence: `.10x/evidence/.storage/buoy-mcp-runtime/`

## Implemented boundary

One optional module, lazy entrypoint dispatch, top-level help registration, three
strict typed tools, fixed same-interpreter shell-free subprocess argv, captured
pipes/DEVNULL input, object JSON structured/text parity, no retry, generic errors,
and exact-line allowlisted worker fallback warning once. Retrieval/catalog source
semantics are unchanged. No consumer documentation is implemented in this phase.
CI explicitly installs/requires the extra on Python 3.11/3.13 and preserves the
base-wheel smoke, including absent-extra launch/help checks.

## SDK compatibility repair authorized by supervisor

Official SDK 2.2.0 default stdio uses a non-cancellable AnyIO AsyncFile reader.
Actual SIGTERM/SIGINT tests reaped command children but hung server interpreter
exit with client stdin still open (`mcp-first.log.gz`). A threadpool-abandon repair
let main finish but still hung interpreter shutdown (`mcp-second.log.gz`,
`signal-debug.log.gz`: faulthandler shows `threading._shutdown`).

Supervisor explicitly approved preserving official MCPServer/tools and SDK stdio
framing via its one `_lowlevel_server` serving seam, with consumer dependency
pinned to tested **mcp==2.2.0**, not merely a lock pin. No governing spec was edited.
The final input reader owns a duplicated **unbuffered raw fd** with UTF-8 universal
newline decoding and a daemon read thread, avoiding buffered-stdin finalization
locks. SDK stdout descriptor protection remains intact. CLI children explicitly
receive DEVNULL stdin and captured output, never the wire. No SDK globals are
patched in production. Remove the private serving workaround/pin only after an
SDK release supplies cancellable stdio and the same real-process tests pass.

SDK JSON-string pre-parsing would turn a literal catalog search `"null"` into null.
A small FuncMetadata subclass disables that convenience conversion. Raw strict
model validation rejects coercions/unknown fields before SDK validation can echo
caller input. Tests retain `null`, `[]`, `{}`, quotes, shell/option syntax as data.

## Exact environment and limits

`versions-packaging-preservation.json` is authoritative:
- CPython 3.11.10 and 3.13.0, macOS arm64; uv 0.11.7.
- mcp / mcp-types 2.2.0; AnyIO 4.14.0; Pydantic 2.13.4.
- Earlier coordination shorthand naming Python 3.11.14/AnyIO 4.13 was inaccurate;
  these captured values supersede it.
- Virtualenvs, dependency cache, HOME, runtime artifacts, and distribution output
  are under isolated temporary directories recorded in `environment-path.txt`
  and `short-home.txt`. Test environments use `env -i`, explicit PATH/HOME,
  `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and no credentials.
- No live provider call, model download, `.env` load, global install, client config
  edit, publication, push, merge, or task-repository tag occurred. Existing package
  tests create disposable fixture repositories/tags only.
- No original-checkout edits: every preservation-manifest hash matched. This
  check read only the specifically listed original files, never credentials.
- No new exact-real-model parity campaign was run: routing/ranking/worker code
  is untouched; real orchestration with fake provider/model parity and the full
  existing protective suites ran. No cached model was warmed for acceptance.

## Commands and outcomes

Let `T=$(cat .10x/evidence/.storage/buoy-mcp-runtime/environment-path.txt)` and
`H=$(cat .10x/evidence/.storage/buoy-mcp-runtime/short-home.txt)`.
All dependency commands used isolated `HOME` and `UV_CACHE_DIR=$T/cache/uv`.

1. `uv venv --python 3.13 "$T/venv"`; initial
   `uv pip install --python "$T/venv/bin/python" 'mcp>=2.2,<3'`: passed;
   inspected installed official SDK signatures/source before implementation.
2. `uv lock`, then after approved pin `uv lock`: passed; 171 resolved packages;
   `uv lock --check`: passed. Existing package versions retained; optional SDK
   dependency closure added. Logs `lock*.log`.
3. `UV_PROJECT_ENVIRONMENT="$T/venv" uv sync --locked --extra mcp --python 3.13`
   and equivalent `venv311` / `3.11`: passed (`sync*.log`).
4. Initial `python -m unittest cli.test_mcp -v` with tests/src PYTHONPATH:
   first 12 tests failed with 8 errors (same-task AnyIO client context ownership
   in unittest setup/teardown, plus two signal shutdown timeouts). Repaired
   tests to enter/exit Client in each test task. Second run: only two signal
   failures. Third run: all 12 passed. Original logs retained.
5. First full discovery exceeded the 120-second command bound because the
   long temporary HOME exceeded existing POSIX worker socket-length guards.
   No guard was changed; reran with short isolated HOME (`short-home.txt`).
   The next full run completed 1339 tests with four failures: expected command
   inventory needed the approved `mcp` addition, and source PYTHONPATH shadowed
   three installed-version fixture checks. Added only `mcp` to the exact-set
   assertion and removed global PYTHONPATH for full-suite runs.
6. Final full command, once per interpreter:
   `env -i PATH="$PATH" HOME="$H" XDG_CACHE_HOME="$T/cache" HF_HOME="$T/cache/hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 "$P" -m unittest discover -s tests -p 'test_*.py' -q`
   where P is `$T/venv/bin/python` or `$T/venv311/bin/python`:
   **1339/1339 pass on each**, 113.612s / 141.531s, no skips reported.
   Logs `full-313-final.log`, `full-311-final.log`.
7. After the last narrow literal-JSON-search repair, final focused command on
   both interpreters:
   `env -i PATH="$PATH" HOME="$H" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 "$P" -m unittest discover -s tests -p 'test_mcp.py' -v`
   **12/12 pass each**, 5.356s / 5.308s (`mcp-*-final.log`). A mistaken interim
   `-s tests/cli` invocation could not import existing shared `cli` fixture
   helpers; retained as `mcp-*-wrong-discovery.log`, corrected command above.
   Broad suites were not rerun merely to address a stale long-running notice.
8. Both interpreters: `python scripts/validate_ranking_contract.py` passed;
   `python scripts/c6_syntax_forecast.py validate` passed (existing tokenizer
   readiness=false, not a fabricated readiness pass). Initial promotion call
   lacked an event/base and failed as designed. Corrected
   `python scripts/validate_ranking_promotion.py --base-ref db5e8e1597e908c30fff76ec2aba565f1e2fbcbc`
   passed both: authority unchanged, registry unchanged.
9. `UV_PROJECT_ENVIRONMENT="$T/base" uv sync --locked --python 3.13` passed.
   Actual base environment has no importable MCP; `python -m buoy_search --help`
   and `mcp --help` exit 0, `mcp` exits 1 with 0 stdout bytes and actionable,
   traceback-free optional-extra diagnostic (`base-smoke.log`).
10. `uv build --out-dir "$T/dist"` passed. ZIP/tar inspection confirms adapter
    module in both artifacts, original console entrypoint, optional extra with
    exact SDK and direct AnyIO/Pydantic requirements. Hashes/metadata captured.
    This is **not final isolated installed-wheel acceptance**; dependent phase
    owns that result.
11. `git diff --check` passed. Source/test/CI/packaging diff is saved as
    `runtime-source.diff`; no source/semantic protective assertion removed.

## Specific assertions and review handoff

12 source-named unittest methods cover 16 actual catalog CLI cases and 12 actual
retrieval CLI cases, alongside strict-input/mapping/error matrices. Fake catalog
snapshots go through actual CLI filtering/rendering (enabled incompatible live
cards retained; all/stale/disabled; canonical and reviewed-example search; missing
cards; vectors/source passage banks absent). Real Hybrid/Multi retrievers, actual
CLI routing/evidence/rendering, fake read resources and local inference prove
identical JSON and operation observations for explicit single/multi, automatic,
empty, partial, abstained, inconclusive and total-failure outcomes. Explicit paths
perform zero catalog/route model work. Exact structured/text payload equality is
asserted, not just hand-authored captured payload passthrough.

Real official Client stdio initialization/discovery and invalid calls pass; a
credential-free real catalog CLI child fails safely despite a `.env` sentinel.
Raw-wire tests parse every stdout line as JSON, assert empty non-protocol stdout
and empty stderr on shutdown, forbid provider/model/worker/dotenv imports during
discovery, and verify no runtime assets. Split UTF-8 + CRLF input passes. Protocol
cancellation leaves the server available, EOF exits, SIGTERM/SIGINT exit while
client stdin remains open: all reap the owned command child, retain an unrelated
shared-process sentinel, and emit no traceback/finalization stderr. Existing
worker lifecycle tests are untouched; the sentinel is not a real model worker.

Residual integration items: independent read-only review, final consumer docs and
clean installed-wheel acceptance belong to the parent/dependent phase. No claim
of Windows execution or hosted CI completion is made; CI is configured for Linux
3.11/3.13. The pinned SDK compatibility seam is deliberate technical debt with
an explicit removal condition. No known runtime behavioral blocker remains.

Raw failing logs with terminal trailing whitespace are preserved byte-for-byte
as gzip files so repository diff hygiene remains passing. `runtime-source.diff`
is zero-context unified diff for the same reason. `diff-check-first.log.gz` records
the initially detected evidence-only whitespace, not a source-code defect.
