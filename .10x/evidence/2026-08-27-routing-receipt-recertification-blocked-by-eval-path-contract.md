Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/cancelled/2026-08-27-recertify-routing-receipts-after-subpackage-migration.md, .10x/tickets/done/2026-08-27-reorganize-buoy-search-subpackages.md, .10x/decisions/superseded/buoy-recertifies-routing-receipts-for-subpackage-migration-field-correction.md

# Routing receipt recertification blocked by immutable eval-path contract

## What was observed

The four receipt-bound source deltas were compared directly against their pre-migration bytes from `HEAD`. Every change was relocation-required:

- `evals/routing_quality.py`: imports moved modules from their new subpackages; package-data and receipt-source lookups resolve through the package root and new exact paths.
- `retrieval/routing.py`: imports moved modules from their new subpackages.
- `cli/main.py`: imports moved modules from their new subpackages, including the same lazy relation imports.
- `retrieval/evidence.py`: imports the moved cross encoder and resolves packaged evidence calibration through the package root.

No function bodies, thresholds, routing policy, scoring expressions, evidence semantics, or public call signatures changed in these four modules.

The corrected authority names `receipts.evaluator_scorer_sha256` as the routing-quality receipt. The packaged active artifact was updated from its source-tree-measured old receipts to exactly these values:

| Receipt | New source path | New SHA-256 |
|---|---|---|
| `evaluator_scorer_sha256` | `src/buoy_search/evals/routing_quality.py` | `6b4961fe797d076c9443ef0aceafdf57f656d1850dfc0b5dca49bac93a30521c` |
| `routing_module_sha256` | `src/buoy_search/retrieval/routing.py` | `7dda8102ec2dde7646f446f706f60b1251cd46a651aa25de01640f42b480454f` |
| `cli_module_sha256` | `src/buoy_search/cli/main.py` | `33ff5390ec48c48469fbdcdecc49297fe2e1e9042437c5ef675ae4fa932142b4` |
| `evidence_module_sha256` | `src/buoy_search/retrieval/evidence.py` | `421b4b08a4e63cb579a3d6620dbc56296575768d8333c3d35f0cf3d2a013f604` |

The artifact changed from SHA-256 `79c780a5c3ffebfe5569d463663c30d681cf224aec3ddfb1e03202641b97ed1e` to `0e6b6db93260a75eb9f6e3fa99a3b2decc9267aca6c983144c3079e28b8e19f3`. A recursive parsed comparison found exactly these changed paths:

```text
receipts.evaluator_scorer_sha256
receipts.routing_module_sha256
receipts.cli_module_sha256
receipts.evidence_module_sha256
```

A unified text comparison found exactly eight changed lines: one removed and one added line for each authorized value. Keys, ordering, whitespace, and all other text were unchanged. The production loader accepted the artifact in active mode after rebinding.

The focused routing suite passed. The first full-suite run then exposed three stale source-path audit assertions and a separate immutable repository-evaluation path contract. The static audit assertions were updated only to the specified new module paths and their focused tests passed.

The prior structural worker had changed judged `repo_path` strings in `src/buoy_search/data/buoy_search_repo_search_seed_evals.json`. Those changes made paths truthful after the move, but changed an immutable dataset hash and caused ranking-contract and fixture-autoresearch failures without corresponding governed derived updates. Because the current decision authorizes only four routing receipts, the dataset was restored byte-for-byte to `HEAD`. The next full-suite run passed every ordinary test but failed ten subtests that require every judged repo path to exist; the restored old flat paths no longer exist.

Completing the structural migration therefore requires separate owner authority for a narrow eval-path contract migration: judged path strings, corresponding fixture candidate paths, and mechanically derived immutable dataset/bundle hashes. The supervisor directed that this immutable contract must not be revised without that authority. Both tickets remain blocked and package/installed-wheel validation was not continued.

## Procedure and command results

### Source delta audit

For each receipt-bound module, the pre-migration file was extracted with `git show HEAD:<old-path>` and compared with `diff -u` to the relocated file. The output contained only import-path, package-data path, and receipt-source path changes described above.

### Receipt measurement and exact artifact comparison

A standard-library Python script measured each source with `hashlib.sha256`, replaced the four exact old key/value pairs once each, recursively compared parsed before/after JSON, and compared unified text lines. It asserted exact changed-path equality and exactly eight changed text lines. All assertions passed and emitted the hashes recorded above.

### Production artifact validation

Command:

```sh
PYTHONPATH=.:src uv run python - <<'PY'
from buoy_search.evals.routing_quality import load_routing_confidence_calibration, validate_routing_confidence_calibration
calibration = load_routing_confidence_calibration()
validate_routing_confidence_calibration(calibration)
print(calibration.mode)
PY
```

Result: passed; mode was `active`.

### Focused routing validation

Command:

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q \
  tests/test_automatic_routing.py \
  tests/test_routing_quality.py \
  tests/test_routing_quality_runner.py \
  tests/test_routing_activation_cli.py \
  tests/test_evals.py
```

Result before restoring the immutable dataset: `135 passed, 148 subtests passed in 1.77s`.

### First full suite

Command:

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q
```

Result: `6 failed, 1161 passed, 57 warnings, 1214 subtests passed in 91.21s`.

Failures comprised three stale static source-path audit assertions, one fixture autoresearch score mismatch, and two immutable ranking-contract dataset hash failures. The static assertions were updated to new paths. The dataset was restored to avoid unauthorized contract mutation.

### Focused relocation follow-up

Command:

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q \
  tests/test_autoresearch.py \
  tests/test_provider_invocation_receipt_catalog.py \
  tests/test_provider_invocation_receipt_integration.py \
  tests/test_ranking_contract.py
```

Result with the restored immutable dataset: `37 passed, 74 subtests passed in 0.83s`.

### Final stopped full suite

Command:

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q
```

Result: `10 failed, 1167 passed, 57 warnings, 1213 subtests passed in 90.41s`.

All ten failures were subtests of `test_buoy_search_seed_repo_eval_judgments_are_graded_and_draft`; each failure identified an old flat `repo_path` that no longer exists. No routing, production behavior, ranking-hash, or fixture-score test failed in this final stopped run.

## What this supports or challenges

This evidence supports acceptance criteria 1–4 for the narrow routing receipt operation: source changes are relocation-only, exactly four receipt values changed, the production artifact validator accepts them, and focused routing checks pass. It also supports that static provider-receipt source audits now follow the new layout.

It challenges full migration acceptance criteria 5, 7, and 8. The full suite cannot pass while both the immutable old eval-path dataset and the breaking no-forwarder package layout are retained. Package and installed-wheel validation were stopped after the unapproved contract seam was identified, and independent review cannot pass a known failing suite.

## Limits and residual risk

- The full suite is not passing: ten path-existence subtests fail on frozen old eval paths.
- No wheel or installed-wheel validation was run after recertification because execution stopped at the new authorization boundary.
- No independent review has yet occurred.
- The routing artifact rebind remains present and locally validates, but neither related ticket may close until the separate eval-path issue is governed and all remaining acceptance checks pass.
- No credential, model, provider, catalog, namespace, release, publication, or deployment operation occurred.
