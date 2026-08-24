Status: recorded
Created: 2026-08-23
Updated: 2026-08-23
Relates-To: .10x/tickets/2026-08-23-reconcile-stale-ci-release-automation-calls.md

# Stale CI Release-Automation Call Reconciliation

## What was observed

The bounded workflow repair was validated at this exact identity:

- branch: `work/reconcile-stale-ci-release-automation-calls`
- initial clean aggregate HEAD: `7437007ed995f247ebe2be87dccddafaa932be7c`
- workflow implementation commit: `33a6d8eb60319f074ee0a5139957cd8353b174c0`
- implementation tree: `6fe239332c866613acd7185df1124744639fd1e7`
- implementation parent: `7437007ed995f247ebe2be87dccddafaa932be7c`
- merge base and inspected `develop`: `0c669c5ea52a7dd1adf060c9197a395a2d05e21d`

The implementation commit changes only `.github/workflows/ci.yml`, with
`0` additions and `2` deletions. The exact deleted lines are:

```text
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/release_automation.py validate-source
uv run python scripts/release_automation.py validate-distribution dist
```

No shell syntax became redundant: both `run: |` blocks still contain multiple
commands. A repository inventory found zero references from any current
`.github/workflows` file to either deleted `scripts/release_automation.py` or
deleted `scripts/release_checks.py`.

A byte comparison proved the post-change workflow is exactly the parent
workflow with those two complete lines removed. The pre-change workflow SHA-256
was `424d80b24f12bdddf9cf2b295c5bdc63e86090b3ac316e206290296f70d89b74`;
the post-change workflow SHA-256 is
`aa2b5443971a61b6b236061a6ad1eb22706a1979c6124f74ea266422f8a33100`.
PyYAML parsed both documents. Parsed comparison proved the workflow name,
triggers, permissions, concurrency, jobs, job keys, Python 3.11/3.13 matrix,
step count/order/names, pinned actions and action inputs are equivalent. Every
non-`run` value is equivalent, and every command other than the two listed
removals is equivalent. Ranking/C6 validation, unfiltered tests, build, clean
wheel install, CLI/module help, tokenizer, routing-canary, and routing-authority
smoke remain.

## Removed and unreplaced coverage

Cleanup commit `0c669c5e` intentionally deleted the implementation behind both
commands. This ticket removes its dead consumers and adds no replacement.
Consequently, CI no longer directly runs the deleted source validator's checks
for Hatch-VCS/package metadata and lock shape, generated-version wiring,
changelog/README/SECURITY release alignment, read-only/release workflow policy,
or routing authority/canary receipt coherence. CI also no longer directly runs
the deleted distribution validator's exact two-artifact, archive-member,
metadata/version/name, console-entry-point, tokenizer/routing asset, receipt,
and wheel-versus-sdist coherence checks.

Existing retained tests, ranking/C6 validators, build, and wheel smoke continue
to cover their own narrower live contracts. Their successful execution is not
claimed as replacement coverage for the deleted release source/distribution
invariants. No deleted validator, release workflow, publication path, job,
action, check, dependency, runtime behavior, or test was restored or replaced.

## Procedure and results

Validation used disposable local clones detached at implementation commit
`33a6d8eb60319f074ee0a5139957cd8353b174c0`. Python 3.11, Python 3.13, and build
runs had separate project environments, homes, temporary directories, XDG
directories, and `BUOY_HOME` paths. Runs set `UV_OFFLINE=1`,
`UV_PYTHON_DOWNLOADS=never`, `PIP_NO_INDEX=1`, `HF_HUB_OFFLINE=1`,
`TRANSFORMERS_OFFLINE=1`, and `PYTHONDONTWRITEBYTECODE=1`, unset common provider
and credential variables, and used only the existing local uv cache. No
provider, model, content, credential, network, real-home, GitHub, publication,
tag, Release, or installed-tool operation was run.

For each of `/opt/homebrew/bin/python3.11` (CPython 3.11.10) and
`/opt/homebrew/bin/python3.13` (CPython 3.13.0), the disposable clone ran:

```text
uv sync --offline --frozen --python <exact interpreter>
uv run --offline --frozen --python <exact interpreter> python scripts/validate_ranking_contract.py
uv run --offline --frozen --python <exact interpreter> python scripts/c6_syntax_forecast.py validate
uv run --offline --frozen --python <exact interpreter> python -m unittest discover -s tests -p 'test_*.py' -q
```

Both ranking-contract runs passed with inventory SHA-256
`e6f97842ec90f0558f51e70f93ea6b8f09f82f63019a27d0738d2b1efb427608`.
Both C6 runs passed with forecast SHA-256
`d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
Python 3.11 passed all `1009` unfiltered tests in `80.342s`; Python 3.13 passed
all `1009` unfiltered tests in `77.428s`.

The separate clean Python 3.13 build clone ran:

```text
uv sync --offline --frozen --python /opt/homebrew/bin/python3.13
uv build --offline --out-dir dist
uv venv --python /opt/homebrew/bin/python3.13 <isolated-wheel-venv>
uv pip install --offline --python <isolated-wheel-python> dist/*.whl
<isolated-wheel-buoy> --help
<isolated-wheel-python> -m buoy_search --help
<isolated-wheel-python> - <<'PY'
# The unchanged workflow's exact tokenizer, routing-canary, dataset,
# calibration-mode, and conditional active-authority assertions.
PY
```

The build produced exactly one non-hidden wheel and one non-hidden sdist. The
isolated wheel install, CLI help, module help, exact tokenizer count, all three
routing-canary names and hashes, 65-case dataset and suite hash, calibration
mode, and conditional active-authority assertions passed.

Additional checks ran:

```text
git grep -nE 'scripts/(release_automation|release_checks)\.py' HEAD -- .github/workflows
# Inverted: zero matches required.
git diff --name-only HEAD^ HEAD
git diff --numstat HEAD^ HEAD -- .github/workflows/ci.yml
# Byte reconstruction and parsed YAML structural/command equivalence script.
uv lock --check --offline
uvx --offline ruff check --select F,E9 tests/test_dynamic_version.py
PYTHONPYCACHEPREFIX=<isolated> python3.11 -m py_compile tests/test_dynamic_version.py
PYTHONPYCACHEPREFIX=<isolated> python3.13 -m py_compile tests/test_dynamic_version.py
git diff --check develop...HEAD
git diff --check HEAD^ HEAD
git status --porcelain=v1 --untracked-files=all
git diff --cached --name-only
```

Inventory, exact two-line delta, YAML parsing/equivalence, frozen lock, Ruff
`F,E9` for the aggregate's changed Python test file, Python 3.11/3.13
compilation, both diff checks, clean porcelain, and no-staged-files checks all
passed. No tests were added or changed by the workflow implementation commit.

The first local build harness stopped after a successful build because its
extra artifact-count assertion included uv's generated hidden `dist/.gitignore`.
No repository or workflow validation failed. The assertion was corrected to
count non-hidden distribution files, and the complete dual-runtime and build
validation was rerun from a newly removed and recreated temporary root; the
results above are from that successful full rerun.

The suites emitted two existing plan-cleanup warning lines and one existing
lxml `strip_cdata` deprecation warning per interpreter. All tests passed.

## Artifacts and hashes

Built artifacts:

```text
679d196e0f78a9a6e178837adf63eab7dbb592858b2ce421fc3a4d1d105b8bfc  buoy_search-0.5.2.dev51+g33a6d8eb6-py3-none-any.whl
5f331970da447fe649ed2d7fe954d9587ad1e79ff32f39a66651f96b874d4cb0  buoy_search-0.5.2.dev51+g33a6d8eb6.tar.gz
```

Raw logs, artifact copies, and their manifest are under
`/tmp/buoy-stale-ci-validation-33a6d8e/`. The manifest SHA-256 is
`0c96ae7322c94c9fb811dfd09a60f378ec437d97dcbabe0985818cab3802c1e1`.
The logs-and-artifacts archive is
`/tmp/buoy-stale-ci-validation-33a6d8e-logs-artifacts.tar.gz` with SHA-256
`f243143a7430cb0a92a051f02455b3d24c2064ad05f7a5dcfd2910c080b72d36`.

```text
9bca2ad835f2318ca99287d940e802d0b12fa7519ae0320154edf6338c581611  logs/build-smoke.log
388161cbd8182cebbb976dee702727940847f322de465a21f82e4f8caf13e111  logs/checks/hygiene.log
a7ca4228bfe4b3868ea1433dbf765f2f2146684c59c7d3d80f254eb75f7c6e8e  logs/checks/inventory-diff.log
64863e1aeb04d436f234c069d153e41438c58840ded1446320fa66a3906c6a7e  logs/checks/static.log
61e99d1dd24d6317cee8133c0a5c02b708be0c961f2822d86bf64ae8c577a904  logs/checks/yaml-equivalence.log
f7ee814e348fdf1a5734983c7c30a7873ad1d6551184c2c17d277952bc5365bd  logs/python311.log
f5aba77641880b02e437b484bdd353764e946c64c59a4d6799bbd03393154bdc  logs/python313.log
```

## What this supports

This evidence supports that the workflow implementation removes exactly the two
dead script invocations without widening scope, keeps every other workflow byte
and parsed behavior, and passes all locally executable retained CI commands on
the supported interpreters in offline isolated environments.

## Limits

- Hosted GitHub Actions and exact-head checks were not run or claimed. The
  parent session owns push and hosted exact-head validation.
- An independent review has not yet been created; the parent session owns the
  required review gate. This ticket remains active.
- Offline wheel installation used packages already present in the machine-local
  uv cache. It did not prove a fresh network-backed dependency resolution.
- Temporary logs and artifacts may be removed by operating-system cleanup; the
  hashes identify the exact files observed here.
- The intentionally deleted release source/distribution validation coverage is
  not replaced, as explicitly disclosed above.
