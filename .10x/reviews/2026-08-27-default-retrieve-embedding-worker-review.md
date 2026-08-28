Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Target: src/buoy_search/cli/main.py; docs/retrieval.md; tests/cli/test_cli.py; tests/retrieval/test_automatic_routing.py; tests/telemetry/test_retrieve_command_telemetry.py; .10x/tickets/done/2026-08-27-default-compatible-retrieve-embeddings-to-worker.md
Verdict: pass

# Default Retrieve Embedding Worker Review

## Scope

Independent review of default eligibility, retrieve-only opt-out, lazy import/dormancy, command-wide visible fallback, error taxonomy, provider-operation boundaries, documentation/tests, and retained provider-free evidence under `.10x/specs/default-retrieve-embedding-worker.md`.

## Initial finding

### Significant — double failure lost established model-phase taxonomy

The first review found that worker failure followed by in-process fallback construction or encoding failure could escape into generic routing/provider handling. Explicit retrieval could label a pre-content model failure as `provider_call_error`; automatic routing could label fallback model failure as `routing_error`. Focused double-failure coverage was absent.

## Resolution

The implementation added a bounded `_InProcessEmbeddingFallbackError` boundary. Fallback construction and encoding failures are redacted and recorded before generic handlers:

- automatic double failure becomes `model_error` before content-retriever construction;
- explicit double failure becomes `model_error` before content operations;
- exactly one bounded fallback warning is emitted;
- raw worker and fallback details do not enter stderr or telemetry; and
- catalog/provider wrapper work is not replayed and content operations remain zero.

Focused explicit, automatic, and telemetry regressions cover these properties. Final full suites report 1,243 tests passing on each Python 3.11 and 3.13. Parent additionally observed 133 focused Python 3.13 tests passing, clean diff hygiene, and no staged files.

## Other verified behavior

- Exact compatible POSIX default configuration selects the worker lazily.
- `--no-embedding-worker` exists only on retrieve and forces the established in-process path.
- The experimental parser flag is removed without alias.
- Custom model, float16, unsupported capability, explicit dry-run, help/version, and non-retrieve paths remain worker-free where required.
- Fallback success switches the whole command in-process with one warning and no duplicated provider content operation.
- Provider credentials/clients remain outside the worker; no telemetry schema or result marker was added.
- No live provider operation was performed for default activation.

## Verdict

Pass. Independent rereview found no unresolved significant or minor finding. The default-compatible-worker ticket is suitable to close.

## Residual risk

- Real-model validation is limited to Darwin arm64.
- Default latency authority is the prior three-command live experiment, not a distribution or provider-adjusted estimate.
- Same-effective-user processes remain inside the Unix-socket trust boundary.
- Offline validation is procedure/source-controlled rather than packet-traced.
- A failed worker followed by in-process fallback may make one command slower.
