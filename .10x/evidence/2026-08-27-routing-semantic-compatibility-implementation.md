Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/done/2026-08-27-implement-routing-semantic-compatibility.md, .10x/specs/routing-semantic-compatibility.md, .10x/decisions/buoy-validates-routing-semantics-not-python-bytes.md

# Routing semantic compatibility implementation

## What was observed

The active automatic-routing artifact now uses strict schema version 4 and contains the exact 18-field semantic compatibility descriptor from `.10x/specs/routing-semantic-compatibility.md`. Runtime parsing and constructed-object validation require exact field names, types, and values.

The active artifact and `RoutingActivationReceipts` removed exactly these current implementation-byte receipts:

- `evaluator_runner_sha256`
- `evaluator_scorer_sha256`
- `routing_module_sha256`
- `cli_module_sha256`
- `evidence_module_sha256`

Eight non-source provenance fields remain, including original/dormant report and Git identities plus the collect-artifact hash. Prior source receipts remain in historical Git/10x evidence and reports; they are no longer compared to installed Python bytes by runtime or package validation.

Artifact semantic comparison against `HEAD` proved these values unchanged:

- calibration ID/revision and active/approval mode;
- score floor `-10.167728424072266` and margin floor `1.0735645294189453`;
- all prior routing/model/projection/catalog bindings;
- threshold-calibration and certification receipts;
- all eight retained non-source provenance receipts.

The new artifact raw SHA-256 is `448e46d9522b6267b5db46a5f38e635f41c68e54514cc0b0e12c4d47bdb7a4b4`.

The evaluator activation gate now checks the semantic descriptor instead of evaluator source receipts. Source hashes may still be emitted in evaluator report provenance, but they are not active runtime/package authority and are not copied into the schema-v4 calibration artifact.

## Changed implementation and tests

- `src/buoy_search/evals/routing_quality.py`
  - canonical descriptor function and strict semantic dataclass/parser/validator;
  - schema-v4-only active loading;
  - source-receipt removal and no installed-byte hashing;
  - existing v1 collect mode retained.
- `src/buoy_search/data/automatic_routing_confidence_calibration.json`
  - schema 3 -> 4;
  - exact semantic descriptor added;
  - five implementation-byte receipt fields removed.
- `scripts/evaluate_routing_quality.py`
  - activation readiness uses semantic compatibility;
  - artifact serialization emits semantic compatibility and reduced receipts.
- `tests/test_routing_quality.py`
  - every one of 18 descriptor fields is independently mutated and rejected;
  - schema/strictness/receipt tests migrated to v4.
- `tests/test_automatic_routing.py`
  - production schema-v4 fixture and semantic-mismatch-before-model regression.
- `tests/test_routing_activation_cli.py`
  - evaluator gate semantic mismatch coverage and production provenance assertions.

## Procedure and results

### Compilation

```sh
PYTHONPATH=.:src uv run python -m compileall -q src scripts tests
```

Passed.

### Focused routing tests

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q \
  tests/test_routing_quality.py tests/test_automatic_routing.py \
  tests/test_routing_activation_cli.py tests/test_routing_quality_runner.py
```

Passed: `117 passed, 135 subtests passed`.

### Broad routing/CLI/telemetry/provider-receipt compatibility basket

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q \
  tests/test_automatic_routing.py tests/test_automatic_routing_after_apply.py \
  tests/test_multi_namespace_retrieval.py tests/test_routing_activation_cli.py \
  tests/test_routing_quality.py tests/test_routing_quality_runner.py \
  tests/test_retrieve_command_telemetry.py tests/test_local_retrieval_telemetry.py \
  tests/test_provider_invocation_receipt_core.py \
  tests/test_provider_invocation_receipt_catalog.py \
  tests/test_provider_invocation_receipt_content.py \
  tests/test_provider_invocation_receipt_integration.py
```

Passed: `271 passed, 345 subtests passed`.

### Full suite

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q
```

Result: `10 failed, 1167 passed, 57 warnings, 1222 subtests passed`. All ten failures are the already-governed next-child dependency in `tests/test_evals.py`: historical v1 Buoy judgment paths are still checked against the reorganized `HEAD`. No routing, semantic-contract, telemetry, CLI, provider-receipt, or package test failed. `.10x/tickets/done/2026-08-27-version-buoy-repository-evaluations.md` owns that path-contract migration; this ticket did not widen into it.

### Distribution and isolated installation

```sh
rm -rf dist && uv build
```

Passed, producing wheel and sdist. Inventory inspection found schema-v4 artifact bytes in both distributions, all 18 descriptor fields, and none of the five removed source receipts. Wheel inventory had 86 entries; sdist inventory had 167 entries.

The wheel was installed into a fresh temporary `uv` environment. Installed `load_routing_confidence_calibration()` returned schema 4 and a dataclass projection exactly equal to `routing_semantic_compatibility_descriptor()`. Installed `buoy retrieve q --namespace site-example-v1 --plan --json` also passed, proving the explicit-namespace bypass from the isolated wheel.

### Diff hygiene and authority comparison

```sh
git diff --check
# deterministic Python comparison of HEAD/new artifact
# git diff --cached --name-only
```

Passed. Artifact comparison proved only schema/descriptor/source-receipt changes plus preserved authority listed above. No files are staged.

## Review follow-up: truthful schema-v4 test names

The aggregate review `.10x/reviews/2026-08-27-evidence-layout-aggregate-review.md` identified a minor routing finding: several current active schema-v4 tests retained stale schema-v2/v3 names. Renamed seven current-active tests to schema-v4 terminology and renamed the schema-mode fixture/label from `schema_two_collect` / `schema-two collect` to `schema_four_collect` / `schema-four collect`. The explicit `test_obsolete_schema_v2_active_artifact_is_rejected` regression remains unchanged and continues to prove fail-closed rejection of the obsolete active schema.

Focused validation after the rename:

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q \
  tests/test_routing_quality.py tests/test_automatic_routing.py \
  tests/test_routing_activation_cli.py tests/test_routing_quality_runner.py
```

Passed: `117 passed, 135 subtests passed`.

Collection audit:

```sh
PYTHONPATH=.:src uv run --with pytest pytest --collect-only -q \
  tests/test_routing_quality.py | rg 'schema_v[234]|schema_mode'
```

Passed. It listed nine truthful schema-v4/current tests plus the one intentional obsolete-schema-v2 rejection test; no stale schema-v3 or current-active schema-v2 test name remains. `git diff --check` passed and no files are staged.

## What this supports or challenges

This supports the routing-semantic ticket's implementation, strict descriptor mutation matrix, behavior parity, package inclusion, installed validation, removal of source-byte runtime coupling, and resolution of the routing P2 naming finding. Aggregate acceptance still requires fresh independent review of this repair and the separately owned significant findings.

## Limits and residual risk

- The first aggregate independent review failed on separately owned significant findings and this minor routing test-name finding. The minor routing finding is repaired here; fresh independent review remains required.
- Later aggregate integration evidence reports the full suite green; this focused follow-up reran the routing basket rather than duplicating the complete aggregate validation.
- No live route collection, provider/model call, credential access, namespace/catalog/content mutation, release, publication, or deployment occurred.
- Source hashes remain in newly generated evaluator report provenance for reproducibility, but no runtime/package check binds calibration authority to them.
