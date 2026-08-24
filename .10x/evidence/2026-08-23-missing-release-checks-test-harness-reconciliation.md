Status: recorded
Created: 2026-08-23
Updated: 2026-08-23
Relates-To: .10x/tickets/2026-08-20-reconcile-missing-release-checks-test-harness.md, .10x/specs/buoy-package-and-cli-identity.md, .10x/decisions/annotated-tag-triggered-github-releases.md

# Missing Release Checks Test Harness Reconciliation

## What was observed

The bounded implementation was validated with this exact identity:

- branch: `work/reconcile-missing-release-checks-test-harness`
- implementation commit: `b212ebb69052820b4c74caeebe49fdb6c0fcbfc2`
- implementation tree: `0b2792db7286d9635b7793eeec6c1c8d62d7e988`
- merge base and inspected `develop`: `0c669c5ea52a7dd1adf060c9197a395a2d05e21d`
- activation commit before the implementation: `effe0c4a9c909a177834d5a5620beaa0b244c153`

Cleanup commit `0c669c5e` intentionally deleted `scripts/release_checks.py`,
`scripts/release_automation.py`, the release workflows, and release-automation
tests. The implementation removes the one remaining test whose sole subject was
`scripts.release_checks`, together with that deleted module's import and the
now-unused `unittest.mock.patch` import. It restores no script, workflow,
publication path, package behavior, runtime behavior, or telemetry behavior.

### Removed coverage

`test_legacy_checker_requires_override_and_rejects_stale_version` constructed a
temporary package only to patch the deleted `scripts.release_checks.ROOT` and
exercise deleted `verify_tag` behavior. Its three assertions covered a missing
`SETUPTOOLS_SCM_PRETEND_VERSION`, disagreement with a stale generated version,
and agreement with that generated version. No live implementation now owns
those assertions, so retaining them would require reconstructing intentionally
deleted release-check behavior.

### Retained live coverage

All three retained tests independently exercise current dynamic package-version
behavior governed by `.10x/specs/buoy-package-and-cli-identity.md` and configured
in `pyproject.toml`:

- a clean editable install derives a PEP 440 development version from VCS and
  agrees across installed metadata, `buoy_search.__version__`, and
  `buoy --version`;
- an exact local annotated tag derives one stable package/module/CLI version;
- the supported Hatch-VCS exact-version override agrees across wheel and sdist
  names, archive metadata, generated `_version.py` files, installed metadata,
  module identity, and CLI identity.

Focused runs passed `3/3` tests on Python 3.11 and Python 3.13. Default unfiltered
`unittest` discovery imported the complete test surface and collected `1009`
tests on each version. Complete unfiltered suites passed `1009/1009` on each
version.

## Procedure

Each version was validated from a disposable local clone detached at the exact
implementation commit. Each clone used a separate virtual environment, home,
temporary directory, and XDG directories. The environment set
`UV_OFFLINE=1`, `UV_PYTHON_DOWNLOADS=never`, `PIP_NO_INDEX=1`,
`HF_HUB_OFFLINE=1`, and `TRANSFORMERS_OFFLINE=1`; used only the existing local
uv cache; removed common provider/credential variables; and set
`PYTHONDONTWRITEBYTECODE=1`. No provider, model, content, credential, network,
GitHub, live-service, publication, tag-push, or installed-tool operation was
run. The dynamic-version tests' builds, installs, clone, commit, and annotated
tag operations were local and confined to temporary directories.

Commands were run for both `/opt/homebrew/bin/python3.11` (CPython 3.11.10) and
`/opt/homebrew/bin/python3.13` (CPython 3.13.0):

```text
uv sync --offline --frozen --python <exact-python>
uv run --offline --frozen --python <exact-python> python -m unittest -q tests.test_dynamic_version
uv run --offline --frozen --python <exact-python> python -c "import unittest; suite = unittest.defaultTestLoader.discover('tests', pattern='test_*.py'); print(f'collected {suite.countTestCases()} tests')"
uv run --offline --frozen --python <exact-python> python -m unittest discover -s tests -p 'test_*.py' -q
```

Additional checks from the clean task worktree:

```text
uv lock --check --offline
uvx --offline ruff check --select F,E9 tests/test_dynamic_version.py
PYTHONPYCACHEPREFIX=<isolated> python3.11 -m py_compile tests/test_dynamic_version.py
PYTHONPYCACHEPREFIX=<isolated> python3.13 -m py_compile tests/test_dynamic_version.py
git diff --check develop...HEAD
git diff --check HEAD^ HEAD
git status --porcelain=v1
git diff --cached --name-only
```

Results:

- Python 3.11 focused: `Ran 3 tests in 15.906s` — `OK`.
- Python 3.11 collection: `collected 1009 tests`.
- Python 3.11 full: `Ran 1009 tests in 80.172s` — `OK`.
- Python 3.13 focused: `Ran 3 tests in 15.817s` — `OK`.
- Python 3.13 collection: `collected 1009 tests`.
- Python 3.13 full: `Ran 1009 tests in 77.527s` — `OK`.
- Lock check resolved the frozen lock without changes.
- Ruff `F,E9`, compilation on both requested interpreters, and both diff checks
  passed.
- Worktree porcelain and staged-file output were empty after the implementation
  commit.

The complete suites emitted two expected plan-cleanup warning lines and one
existing lxml `strip_cdata` deprecation warning per interpreter; all tests still
passed.

## Artifacts and hashes

Raw logs and their manifest are under
`/tmp/buoy-reconcile-validation-b212ebb/`. A logs-only archive is
`/tmp/buoy-reconcile-validation-b212ebb-logs.tar.gz` with SHA-256
`653fa46b58ead571b01842ca30eddf84a56fd9c48be7aa430e96befcb87cebd6`.
The relative `SHA256SUMS` manifest has SHA-256
`329cfc0790bd9abb16c7582ac6b53789e65952a16a87eb19de1654f984f2f99c`.

```text
fd39c7bb038e04215a291b0f784f6a8255b843903478ab4472c5977c8d3f59f8  checks/compile.log
73dd85896898c13351ee02b50e88e8c8f3bd3ebd81ed31eb0fe146c6e8547e93  checks/diff-check.log
555bd7bc5030ebbe1fb8049dca844d369a7428f64167bb2e2d88cc5a61355764  checks/identity.log
379dc391b3deac3643df945dfd7ea1dd2e0a62e0b723c8e2a4148feecdc2ba60  checks/lock.log
fdd013e5b389ebab5a565d3b57244eb34e26c116f5cc3e594ed5f6138251bd5c  checks/ruff.log
320b331be7aca37e7baaf29e80cbf89ba57a3dd4f065eb1da0ff0bf8c418c97e  python311/collection.log
7e2d9bfc97c86f0efedf0c7c94614e4129c30c2810ff9c7608a929f0b609f337  python311/focused.log
58b2efd395fe134e27210265921ff03fe429d48a1816b18106a1915d306ab0e8  python311/full.log
43096c6ee6e764cad132e51fa40af3148f47e735b61f2188b29e2a4bf2a2675d  python311/sync.log
2f98c0dab770e392e043f350ddba7f360792e3c5e444b48825d2a5442b0a7f65  python313/collection.log
4b95e4e0358d160f58b236f93e9a17c5ea4c8cd6a4e37089a05c63d61f7c408e  python313/focused.log
0b829933666a5cd9b96a8a804e45c419d37b492347378e696159b442d8cd5cd5  python313/full.log
23d875ce7f9e6c89de4ac13ead14717d3224bb58727e82a61228c0cbaa61aafc  python313/sync.log
```

## What this supports

This evidence supports that the stale import and sole deleted-helper-dependent
test were removed without widening scope, every retained test reaches live
Hatch-VCS/package/module/CLI behavior, default collection succeeds, and focused
and complete suites pass on both supported CI interpreters.

## Limits

- The temporary log paths are machine-local and may be removed by operating
  system cleanup; the hashes identify the exact logs observed here.
- No hosted CI, GitHub action, release workflow, publication operation, or
  installed-tool smoke was run or authorized.
- The ticket remains active pending its required independent review. This
  evidence does not perform that review and does not close or move the ticket.
