Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Relates-To: .10x/tickets/done/2026-07-15-prepare-buoy-v0-3-0.md, .10x/tickets/2026-07-15-buoy-v0-3-0-release-plan.md

# Buoy v0.3.0 Preparation

## What was observed

Release preparation aligns the authoritative project, module, and lock metadata on `0.3.0`. The changelog contains a pending 0.3.0 section with no release link/date claim. Exact `v0.2.1..HEAD` history is represented by source-backed entries for opt-in float16 inference, single-pass plan timing, depth-one pipelined apply, namespace discovery, explicit multi-namespace retrieval, plan/apply retrieval handoff, the canonical local catalog, apply registration/recovery, opt-in auto-routing, explicit-retrieval preservation, and state-root posture. Active identity/compatibility/precision specifications, migration/release docs, configuration docstrings and warnings, and regression tests retain deprecated command/environment aliases through 0.3 and consistently target removal in 0.4.

Both CI runtime suites passed 364 tests. Exact v0.3.0 tag and asset dry checks passed. The build produced exactly one wheel and one sdist (excluding uv's output-directory `.gitignore`) under `/tmp`, outside the repository. Machine-readable artifact observations are stored at `.10x/evidence/.storage/2026-07-15-buoy-v0-3-0-preparation-artifacts.json`.

The following digest inventory is from the validation build immediately before its durable evidence/ticket updates; names, metadata, and content checks were repeated on the final working tree, while these digests are not claimed as final-commit digests because `.10x` evidence is included in the sdist.

| Artifact | Bytes | Observed validation-build SHA-256 |
| --- | ---: | --- |
| `buoy_search-0.3.0-py3-none-any.whl` | 158125 | `048dba11df692a7efcd7ab7269fc2eec82f6b53e57573a3de113bbd051750bab` |
| `buoy_search-0.3.0.tar.gz` | 963670 | `876b371fab4457c304b20c1ceaebe8d46f1a21c2aec53c48d072d7f92a7e0e3e` |

Wheel `METADATA` and sdist `PKG-INFO` report `Name: buoy-search` and `Version: 0.3.0`. The wheel has 44 entries and sdist 432; both contain catalog/routing implementation, bundled package content, and no `turbo_search` import package. An isolated Python 3.13 wheel installation reported `buoy 0.3.0` from both console scripts; `turbo-search --version` emitted only the expected stderr deprecation warning ending `It will be removed in 0.4.` The `buoy_search` import reported 0.3.0 and `turbo_search` remained absent.

## Procedure

All commands ran from the bounded release-preparation worktree. Credential variables were unset for validation; full tests and repository checks set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` so no model lookup/download could occur.

```text
uv sync --locked --python 3.11
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q
# Ran 364 tests: OK

uv sync --locked --python 3.13
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q
# Ran 364 tests: OK

uv run --python 3.13 python -m unittest tests.test_release_automation tests.test_cli tests.test_config -q
# Ran 57 tests: OK

rm -rf /tmp/buoy-v0.3.0-dist
uv build --out-dir /tmp/buoy-v0.3.0-dist
uv run --no-project python scripts/release_checks.py tag --tag v0.3.0
uv run --no-project python scripts/release_checks.py assets --dist /tmp/buoy-v0.3.0-dist

uv venv /tmp/buoy-v0.3.0-venv --python 3.13
uv pip install --python /tmp/buoy-v0.3.0-venv/bin/python /tmp/buoy-v0.3.0-dist/buoy_search-0.3.0-py3-none-any.whl
/tmp/buoy-v0.3.0-venv/bin/buoy --version
/tmp/buoy-v0.3.0-venv/bin/turbo-search --version

uv lock --check
PYTHONPYCACHEPREFIX=/tmp/buoy-v0.3.0-pyc uv run --python 3.13 python -m compileall -q src tests scripts
rg <bounded current-authority version/deprecation consistency patterns>
git diff --check
```

A first isolated `--no-deps` wheel invocation correctly failed because CLI module import requires declared runtime dependencies (`duckdb` was first absent). The final isolated check installed declared wheel dependencies and then passed; this did not change the repository or release assets.

## What this supports or challenges

This supports the preparation ticket's local acceptance criteria: exact current version metadata/assets, complete source-backed pending changelog, retained compatibility with a 0.4 removal target, CI-equivalent runtime coverage, artifact contents, and side-effect-free release dry checks. Tests added/updated assert 0.3.0 tag/assets and required pending changelog entries, and specifically inspect the migration guide's legacy-environment section, `load_config` compatibility docstring, two exact environment warnings, CLI warning, and changelog target rather than accepting an unrelated file-wide 0.4 phrase.

## External-side-effect attestation

No GitHub mutation, tag creation/push, main/develop mutation, package publication, credential read, model construction/inference, Hugging Face model download, or Turbopuffer operation occurred. The isolated wheel dependency installation accessed ordinary Python package distribution infrastructure; it did not publish anything or access model weights.

## Limits

- Local macOS Python 3.11/3.13 validation does not replace hosted Linux CI; the ticket remains active for independent review and PR checks.
- Recorded artifact digests apply to the pre-evidence validation build, not the final commit: the sdist includes `.10x`, so writing its own digest changes the sdist. Final working-tree build/tag/assets/metadata/content checks pass without claiming a self-referential digest. The hosted release workflow rebuilds once from the eventual reviewed tag and is authoritative for published asset digests.
- The changelog intentionally remains pending and omits the v0.3.0 release link/date until the separately owned post-release finalization child.
