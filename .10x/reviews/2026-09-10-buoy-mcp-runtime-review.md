Status: recorded
Created: 2026-09-10
Updated: 2026-09-10
Target: .10x/tickets/done/2026-09-10-implement-buoy-mcp-server.md
Verdict: pass

# Independent Buoy MCP runtime review

## Target

Read-only adversarial review in `/Users/crlough/Code/personal/turbo-search.worktrees/buoy-mcp-server`. Read all three MCP specs and the implementation ticket completely, the substrate research, current implementation/tests, and the saved `runtime-source.diff`. The worktree Git HEAD reference resolves to `f9ddf19c9c265fe5e3f09ff7fda166edb7d248b7`; recovery evidence identifies unchanged runtime implementation `dba28f01076f81bdad01ea46edf934abc7d15597`.

Below, `E` denotes `.10x/evidence/.storage/buoy-mcp-runtime/`; `V` denotes `/tmp/buoy-mcp-runtime.LJClud/venv/lib/python3.13/site-packages/`.

## Findings

No issues found.

### Review

- **Correct — strict inputs and containment:** `src/buoy_search/mcp.py:68-140` enforces strict strings/booleans/positive integers, rejects extra fields before SDK error rendering, validates trimmed namespace selection, and disables SDK JSON-string pre-parsing. Code-owned commands use bound options and positional `--`; no arbitrary dispatch or mutation option is exposed. `tests/cli/test_mcp.py:106-173` checks mapping, option/shell-like values, literal JSON-looking search strings, rejection without launching, sanitized failures, and one invocation without retries.
- **Correct — CLI parity:** `src/buoy_search/mcp.py:37-66` captures separate pipes with DEVNULL input, returns the complete successful JSON object as structured and equivalent text content, and converts command/non-object/malformed-output failures into bounded errors. Only the exact safe worker-warning line is forwarded once. `tests/cli/test_mcp.py:176-303` compares actual fake-backed CLI rendering and operation observations for catalog filtering/show and automatic/single/multi retrieval, including empty, partial, abstained, inconclusive, and total-failure outcomes. Query normalization remains with `src/buoy_search/cli/main.py:1932`; no retrieval orchestration is copied.
- **Correct — catalog privacy:** `src/buoy_search/cli/catalog.py:747-808` retains CLI default/all filtering, canonical search, exact card lookup, and passage-bank suppression. `src/buoy_search/catalog/local.py:419-454` removes vectors while retaining reviewed examples under existing serialization rules. The adapter never supplies `--include-vector`; fake-backed tests assert hidden source passages and retained examples.
- **Correct — protocol and lifecycle:** `src/buoy_search/mcp.py:163-221` retains official SDK framing/stdout protection while implementing the approved cancellable input seam. The installed SDK sources `V/mcp/server/stdio.py` and `V/mcp/server/mcpserver/utilities/func_metadata.py` confirm the compatibility assumptions; `V/anyio/_core/_subprocesses.py:80-115` confirms managed process/pipe lifetime. `tests/cli/test_mcp.py:308-442` exercises real SDK stdio, protocol-only stdout, inert discovery, credential-free failure, split UTF-8/CRLF, cancellation followed by another request, EOF, and SIGINT/SIGTERM interpreter exit with owned-child reaping. The shared-process sentinel is correctly not represented as a real inference worker.
- **Correct — optionality and bounded change:** Lazy dispatch is at `src/buoy_search/cli/entrypoint.py:18-21`; optional imports follow help parsing at `src/buoy_search/mcp.py:149-160`. `pyproject.toml:36-39` declares the optional exact SDK pin and imported dependencies without SDK CLI extras. `.github/workflows/ci.yml:39-53,75-82` requires MCP in both test jobs and preserves base-wheel smoke. The saved diff changes the existing command-inventory assertion only to add `mcp`; it does not remove protective assertions or modify routing/ranking/worker behavior. Tool descriptions retain citation/abstention and provider/local-effect guidance (`src/buoy_search/mcp.py:73-76,94,101`).
- **Fixed:** None; this review made no edits or executions.

## Verdict

**PASS for the runtime ticket's independent review. Merge verdict: OK with the already-recorded dependent acceptance outstanding.** No required correction or new behavior/authority decision was identified. This does not close the ticket, authorize integration, or certify the dependent consumer-documentation/installed-wheel phase.

## Residual risk

- Review inspected evidence, not rerun tests. `E/full-311-final.log:7-10` and `E/full-313-final.log:7-10` record 1,339 passing tests each. These precede the final narrow literal-search repair; `E/mcp-311-final.log:16-19` and `E/mcp-313-final.log:16-19` record all 12 focused tests passing afterward. Ranking/C6, corrected explicit-base promotion, lock, and base-smoke logs were also read. Hosted Linux CI and Windows execution are not established by these macOS results.
- Installed metadata independently confirms MCP 2.2.0, AnyIO 4.14.0, and Pydantic 2.13.4 (`V/*-*.dist-info/METADATA:1-3`). Buoy's inspected Python 3.13 installation is **editable**, version `0.5.2.dev128+g6c9b6d8fe.d20260910`; its `direct_url.json:1` points to this worktree. Its metadata still contains the pre-pin MCP range (`V/buoy_search-0.5.2.dev128+g6c9b6d8fe.d20260910.dist-info/METADATA:37-40`), whereas Python 3.11 editable metadata and current source declare the exact pin. This is not final clean-wheel acceptance and is not treated as a runtime defect.
- `E/versions-packaging-preservation.json:20-23` records a built wheel/sdist with that same development version and artifact hashes; `E/build.log:1-4` confirms the build. These are earlier build-inspection evidence, not proof of installation from the final committed artifact. Consumer docs and final isolated installed-wheel verification correctly remain with the dependent ticket.
- The exact-SDK-pin/private serving seam remains deliberate compatibility debt with its removal condition documented at `src/buoy_search/mcp.py:199-204`. No live provider/model checks, filesystem mutations, Git/test commands, or client configuration changes were performed in this review.

## Report provenance

Captured from the pi-subagents independent reviewer report at
`/Users/crlough/.pi/agent/sessions/--Users-crlough-Code-personal-turbo-search--/subagent-artifacts/outputs/6fcdfacb-b899-4e07-ba15-43d170274dee/reviews/runtime-1.json`. Workflow `6fcdfacb-b899-4e07-ba15-43d170274dee`,
child key `runtime-review-1`. Only record-location pointers may be mechanically
repaired when records move; the original report artifact remains unchanged.
No additional verification or closure is implied by capture.
