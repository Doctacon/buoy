Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Relates-To: .10x/tickets/done/2026-07-14-buoy-core-package-rename.md, .10x/specs/buoy-package-and-cli-identity.md

# Buoy Core Package Rename Validation

## What was observed

- The distribution is `buoy-search` 0.2.0 with Apache-2.0 metadata and a root `LICENSE` containing the standard Apache License 2.0 text.
- Implementation moved from `src/turbo_search` to `src/buoy_search`; internal imports, tests/mocks, autoresearch runner IDs/module commands, active experiment paths, user agents, and bundled self-search data now use the new technical identity.
- `buoy` is the primary console command and module help/version identify `buoy`.
- The 0.2 `turbo-search` console alias invokes a dedicated `legacy_main`, writes one removal warning to stderr, and preserves clean JSON stdout.
- Deterministic `jf_*` row IDs, namespace algorithms, plan/apply ID generation, `.turbo-search` state defaults, and `TURBO_SEARCH_*` configuration were not changed by this child. State/environment transition belongs to the next ticket.
- No Python import shim remains; an isolated `import turbo_search` fails as specified.

## Procedure and results

```text
uv sync
resolved 130 packages; built and installed buoy-search==0.2.0

PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_cli tests.test_autoresearch tests.test_apply_cli -q
Ran 72 tests; OK

PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
Ran 208 tests; OK

uv run buoy --version
buoy 0.2.0

uv run python -m buoy_search --version
buoy 0.2.0

uv run turbo-search --version
stdout: buoy 0.2.0
stderr: Warning: `turbo-search` is deprecated; use `buoy` instead. It will be removed in 0.3.

uv build --out-dir /tmp/buoy-core-package-build
built buoy_search-0.2.0.tar.gz and buoy_search-0.2.0-py3-none-any.whl
```

Wheel/sdist inspection confirmed:

- metadata name/version/license expression: `buoy-search` / `0.2.0` / `Apache-2.0`;
- `buoy_search` code and `buoy_search/data/buoy_search_repo_search_seed_evals.json` are present;
- no `turbo_search` implementation package is present;
- sdist contains the root license.

An isolated temporary environment installed the built wheel and verified `buoy`, `python -m buoy_search`, the legacy console warning/stdout behavior, and unsupported old Python import behavior.

The renamed fixture autoresearch experiment passed with score 100.0 using `python -m buoy_search.autoresearch` and no live calls.

`uv lock --check`, `git diff --check`, new-source whitespace inspection, and module compile checks passed.

## Preservation of pre-existing work

The repository already had 12 staged documentation/record paths before this child began. Their staged path list remained exactly unchanged; this child added no staged paths and did not reset or modify the index. Consequently the repository is not globally “no staged files,” but all pre-existing staged work was preserved as required.

## What this supports or challenges

Supports the core package/CLI identity specification and provides build/install evidence without implementing the separately governed state/environment or documentation/logo migrations.

## Review-blocker repair

Independent review found that the live autoresearch baseline had mechanically renamed the already-established semantic namespace to `github-doctacon-buoy-search-v1`. The repair restored `github-doctacon-turbo-search-v1`, rewrote directly coupled question/hypothesis/notes to describe the preserved pre-rebrand namespace without claiming a renamed apply, and added `test_live_sample_preserves_pre_rebrand_remote_namespace`.

```text
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_autoresearch tests.test_cli tests.test_apply_cli -q
Ran 73 tests; OK

PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
Ran 209 tests; OK

uv lock --check && git diff --check
OK

uv build --out-dir /tmp/buoy-core-repair-build.*
built buoy_search-0.2.0 wheel and sdist; both contain buoy_search and no turbo_search package
```

A direct JSON assertion confirmed the live experiment contains `github-doctacon-turbo-search-v1` and contains no `github-doctacon-buoy-search-v1`. No live experiment or remote call ran.

## Limits

- README/docs/skills still present the old command until the dependent brand-docs child.
- Default state paths and branded environment variables intentionally remain old until the local-compatibility child.
- The preserved live namespace may contain pre-rebrand source paths; the experiment notes require separately confirming compatibility with the renamed seed dataset before any live run.
- GitHub was not renamed, PyPI was not published, and no Turbopuffer operation ran.
- Independent re-review is still required before closing the child ticket.
