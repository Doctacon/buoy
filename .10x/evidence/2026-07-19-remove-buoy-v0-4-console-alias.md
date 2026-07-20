Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Relates-To: .10x/tickets/done/2026-07-19-remove-buoy-v0-4-console-alias.md, .10x/specs/buoy-v0-4-console-alias-removal.md

# Buoy 0.4 Console Alias Removal

## What was observed

Implementation commit `8fca87520847433fd325e82ddf4e2e487ae03d14` removes only the package console mapping `turbo-search = buoy_search.cli:legacy_main`, the dedicated `legacy_main` hook, and its alias-only unit coverage. Project, module, lock, wheel, and sdist metadata identify `buoy-search` 0.4.0. Primary parser, command, state-root, old-plan, environment/config, direct-command, and safety behavior remained covered by the unchanged full suite.

The exact-commit candidate artifacts were built outside the repository at `/tmp/buoy-console-alias-artifacts-8fca875/`:

- `buoy_search-0.4.0-py3-none-any.whl`: SHA-256 `188b3aa3c9d7e4732349890c96f96a59ee87078f47c3b9cef8e51844d1fa66bc`;
- `buoy_search-0.4.0.tar.gz`: SHA-256 `3c325d90358b13bde13a854514bd94b76c3f635c1fac78d31441c0c05dc07195`.

Wheel inspection found 45 files and 19 bundled data files. `METADATA` reported name `buoy-search`, version `0.4.0`; `entry_points.txt` was exactly:

```text
[console_scripts]
buoy = buoy_search.cli:main
```

The wheel contained `buoy_search/cli.py` and bundled `buoy_search/data/*`, contained no `turbo_search` package, and its CLI source contained no `legacy_main`. The 531-file sdist reported the same name/version and its `pyproject.toml`/CLI source likewise contained only the primary script and no dedicated hook.

### Clean candidate installation

A fresh Python 3.13 environment at `/tmp/buoy-console-alias-clean-8fca875` installed the candidate wheel normally. Installed distribution metadata reported:

```text
name=buoy-search
version=0.4.0
entry_points=[('console_scripts', 'buoy', 'buoy_search.cli:main')]
```

`buoy --version` printed `buoy 0.4.0`; `buoy --help` and `python -m buoy_search --help` both began `usage: buoy [-h] [--version]` and exited successfully. Direct inspection of the complete environment launcher directory found `buoy` and no `turbo-search`; an explicit `test ! -e .../bin/turbo-search` passed. This proves clean-install absence only.

### Same-environment released-wheel upgrade

Downloaded only from:

`https://github.com/Doctacon/buoy-search/releases/download/v0.3.0/buoy_search-0.3.0-py3-none-any.whl`

Before installation, `shasum -a 256` returned the required immutable digest `048dba11df692a7efcd7ab7269fc2eec82f6b53e57573a3de113bbd051750bab` exactly. A second fresh Python 3.13 environment at `/tmp/buoy-console-alias-upgrade-8fca875/venv` then installed that verified wheel. Before upgrade, distribution metadata reported version 0.3.0 and entry points `buoy = buoy_search.cli:main` plus `turbo-search = buoy_search.cli:legacy_main`; both launchers existed, both help commands exited successfully, `buoy --version` printed `buoy 0.3.0`, and the old launcher emitted its expected deprecation warning.

Without recreating the environment, this normal upgrade was run:

```bash
uv pip install --python /tmp/buoy-console-alias-upgrade-8fca875/venv/bin/python --upgrade /tmp/buoy-console-alias-artifacts-8fca875/buoy_search-0.4.0-py3-none-any.whl
```

After upgrade, installed metadata reported version 0.4.0 and exactly the `buoy` entry point. `buoy --version` printed `buoy 0.4.0`; `buoy --help` succeeded; launcher-directory inspection listed `buoy` and no `turbo-search`; and explicit absence testing passed. This is same-environment package-manager removal evidence, distinct from clean-install absence, and makes no claim about user-owned aliases, wrappers, copied launchers, caches, or other files.

### Tests and checks

- `uv lock --check`: passed.
- Isolated Python 3.13 focused command: `UV_PROJECT_ENVIRONMENT=/tmp/buoy-console-alias-py313 PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.13 python -m unittest tests.test_cli tests.test_release_automation -q`: 48 tests passed.
- Isolated Python 3.13 full command: `UV_PROJECT_ENVIRONMENT=/tmp/buoy-console-alias-py313 PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q`: 414 tests passed.
- Isolated Python 3.11 full command: `UV_PROJECT_ENVIRONMENT=/tmp/buoy-console-alias-py311 PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q`: 414 tests passed.
- `uv build --out-dir /tmp/buoy-console-alias-artifacts-8fca875`: wheel and sdist built successfully from commit `8fca87520847433fd325e82ddf4e2e487ae03d14`.
- `uv run --no-project python scripts/release_checks.py tag --tag v0.4.0`: passed.
- `uv run --no-project python scripts/release_checks.py assets --dist /tmp/buoy-console-alias-artifacts-8fca875`: passed.
- Python zip/tar metadata, package-data, entry-point, and hook assertions: passed.
- `git diff --check`, source-reference inspection, and `uv.lock` coherence check: passed.
- Pull request #47 CI run `29707534036` at pushed head `5bfa8455f35f12aae0041f8cfec98c6bec70e22f` passed: Python 3.11 job `88246909509` (47s), Python 3.13 job `88246909505` (46s), and distribution build job `88246964840` (10s).

The full suites emitted two existing best-effort temporary plan-artifact cleanup warnings and still passed; no repository or user state was involved.

## Procedure

1. Read the executable ticket, aggregate plan, both active 0.4 removal specifications, package/local/precision/release-validation specifications, compatibility inventory research, shaping reviews, and immutable 0.3.0 release evidence.
2. Removed only the distribution console alias, dedicated source hook, and alias-only import/test; advanced coherent candidate metadata; updated bounded package/release assertions and console migration/release text.
3. Used temporary Python 3.11/3.13 project environments for focused/full tests.
4. Committed the implementation, built exact-commit artifacts into `/tmp`, inspected wheel/sdist metadata/content, and validated primary CLI behavior in a fresh wheel-only environment.
5. Downloaded the released 0.3.0 wheel into a second `/tmp` root, verified its required digest before install, proved both old package-owned launchers, normally upgraded the same environment, and inspected installed metadata and launchers after upgrade.

## Side-effect attestation

No package was published; no tag or GitHub Release was created; no PyPI operation, live Turbopuffer call, namespace operation, remote data read/write, state-root discovery, plan read, local data migration, re-embedding, user launcher deletion, or project/user state mutation occurred. Network activity was limited to dependency/package downloads and the immutable GitHub wheel download. Installations and build outputs were confined to disposable `/tmp` locations. Git branch push and pull-request creation are separately authorized delivery operations, not package publication or product/data mutation.

## What this supports

This supports the ticket's source/package/version, clean-install, same-environment upgrade, primary-CLI, focused/full-test, distribution, migration-guidance, and no-side-effect acceptance criteria at implementation commit `8fca87520847433fd325e82ddf4e2e487ae03d14`.

## Limits and residual risk

- Clean-install and upgrade checks ran locally on macOS with Python 3.13; the complete locked source suite separately passed on Python 3.11 and 3.13.
- Dependency installation resolved/downloaded open-source dependencies and, during the upgrade, reconciled the candidate's existing `scrapling==0.4.9` pin; no dependency contract was changed by this ticket.
- Hosted checks passed on the implementation/evidence head named above. This follow-up evidence update is record-only; exact final pull-request-head checks remain observable on PR #47. Independent review remains required before ticket closure.
- This branch intentionally does not implement the separately owned environment-alias removal. Aggregate integration must reconcile both child diffs and coherent 0.4.0 metadata before either lands on `develop`.
