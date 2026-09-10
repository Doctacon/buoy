Status: recorded
Created: 2026-09-10
Updated: 2026-09-10
Target: .10x/tickets/done/2026-09-10-document-and-verify-buoy-mcp-installation.md
Verdict: pass

# Independent Buoy MCP installation review

## Target

Reviewed all three governing MCP specs, the installation ticket, substrate research, runtime ticket, installation evidence, saved `installation-source.diff`, current implementation/docs/tests/CI, and retained installed-package files. The worktree Git HEAD reference resolves to `work/buoy-mcp-server` at `9efef60db26031eb628b8e3bfcc808720989ec38`. Installed acceptance is explicitly bound to implementation commit `89cecb2ed0bf5279b0bbedb5cc42cd342d2885a0`, not the later evidence commit.

Evidence directory below: `E = .10x/evidence/.storage/buoy-mcp-installation/`.

## Findings

No issues found.

- **Correct — installation and consumer guidance.** `docs/mcp.md:6–46` documents unreleased-source installation, the optional exact SDK pin, the approved agent-neutral configuration, absolute executable resolution, client environment differences, and no credential interpolation or automatic dotenv loading. `README.md:36` adds the single focused link without changing its release-pinned quick start. `tests/core/test_mcp_documentation.py:15–59` checks the example, link, discoverable fields, required arguments, and defaults.
- **Correct — current strict interface and data containment.** `src/buoy_search/mcp.py:68–142` exposes only the three approved signatures, rejects unknown/wrong-type arguments, preserves literal JSON-looking strings, validates namespace restrictions, and binds option values and positional `--` boundaries. `tests/cli/test_mcp.py:107–150` covers automatic/null/empty and explicit mappings, boolean/noninteger rejection, reserved/duplicate/excess namespaces, hidden flags, and shell-like data. Installed discovery and sanitized invalid-call responses are retained in `E/installed-extra-311.json` and `E/installed-extra-313.json`.
- **Correct — subprocess, results, and privacy.** `src/buoy_search/mcp.py:37–66` invokes the same interpreter with fixed CLI argv, DEVNULL stdin, separately captured pipes, and no adapter retry. It preserves successful JSON objects as structured/text content, sanitizes failures, and forwards only the exact safe worker warning once. `tests/cli/test_mcp.py:153–174` exercises malformed/non-object output, secret-bearing exceptions/stderr, nonzero exits, and warning deduplication.
- **Correct — actual CLI parity and catalog exclusions.** `tests/cli/test_mcp.py:177–304` compares real fake-backed CLI rendering and operation observations against tool results for retrieval hits, empty results, partial failure, abstention, inconclusive outcomes, and total failure, plus catalog default/all/search/show behavior. This is not merely fixture passthrough. CLI rendering remains authoritative at `src/buoy_search/cli/main.py:2343–2349`. Catalog filtering/exact lookup and passage-bank suppression remain at `src/buoy_search/cli/catalog.py:714–818`; `src/buoy_search/catalog/local.py:419–454` removes vectors while retaining reviewed examples. Consumer explanations at `docs/mcp.md:54–127` match these boundaries and disclose read costs, incomplete evidence, workers, and opt-in local telemetry.
- **Correct — real lifecycle and inert protocol checks.** `tests/cli/test_mcp.py:353–449` exercises real stdio framing, split UTF-8, cancellation followed by continued service, EOF/SIGINT/SIGTERM, owned-child reaping, shared-process survival, and interpreter exit. The clean-wheel helper independently waits for console-entrypoint exit and checks empty trailing stdout/stderr at `tests/core/mcp_installation_smoke.py:88–150`. Its guard and temporary environment at lines 25–56 and 172–187 detect forbidden provider/model/dotenv imports, network operations, child launch, dotenv reads, and runtime assets during discovery/invalid calls. The approved pinned-SDK/private cancellable-input repair is unchanged, not a new behavioral authorization.
- **Correct — exact installed artifact identity and optionality.** `tests/core/mcp_installation_smoke.py:59–85` checks wheel origin rather than editable installation, installed adapter bytes, metadata/module version agreement, extra metadata, and actual SDK presence/absence. The four installed reports identify Buoy `0.5.2.dev131+g89cecb2ed`, Python 3.11.10/3.13.0, MCP/mcp-types 2.2.0, AnyIO 4.14.0, and Pydantic 2.13.4. Base reports retain the actionable missing-extra diagnostic. I also read the retained extra313 installed adapter, direct URL, and console entrypoint. `E/artifacts-preservation.json:6–35` records wheel SHA-256 `189dc4da39dc5a602f9e59483e6bf9188437bbf1255d1bcd599102d97f2bca60` and sdist SHA-256 `b87cf4eb5e078b9e16292a973b21f61e386a689ebdc2711a068773faf7917418`; retained metadata/member listings support adapter inclusion, optional dependencies, source docs, and internal-artifact exclusions.
- **Correct — bounded tests and CI.** `.github/workflows/ci.yml:19–53` requires MCP coverage on Python 3.11/3.13; lines 74–137 retain base tokenizer/data assertions and add clean-wheel base/extra acceptance. The saved source diff contains additive docs/tests/CI changes, not protective-test weakening or runtime abstraction changes. `E/full-311.log:9–11` and `E/full-313.log:9–11` record 1342 tests passing each, without reported skips. Raw lock, ranking, promotion, and C6 logs agree with the evidence; C6 explicitly retains tokenizer readiness=false. `E/inspect.py` supplies the recorded artifact/exclusion and original-worktree preservation assertions rather than redefining the baseline.

## Verdict

**pass — Merge verdict: OK for this ticket's reviewed scope.** No required corrections or behavioral decisions identified. This review does not close tickets or authorize integration, release, or live execution.

## Residual risk

This was read-only inspection, not an independent rerun. Process outcomes, artifact digest calculations, preservation hashes, and diff hygiene rely on the inspected retained scripts/logs/reports; binary archives were not independently rehashed or unpacked, and Git cleanliness was not independently recomputed. Installed acceptance and source/fake-backed parity are distinct evidence layers, not a claim that every parity case ran through an installed subprocess.

No hosted CI, Windows execution, live provider access, real-model retrieval, or model download is claimed. The approved SDK-private serving seam remains compatibility debt requiring renewed lifecycle verification when dependencies change. Exact-head hosted CI and any integration actions remain parent-controlled gates.

## Report provenance

Captured from the pi-subagents independent reviewer report at
`/Users/crlough/.pi/agent/sessions/--Users-crlough-Code-personal-turbo-search--/subagent-artifacts/outputs/6fcdfacb-b899-4e07-ba15-43d170274dee/reviews/installation-1.json`. Workflow `6fcdfacb-b899-4e07-ba15-43d170274dee`,
child key `installation-review-1`. Ticket pointers may be mechanically repaired
when records move; the original report is unchanged. Capture is not new testing.
