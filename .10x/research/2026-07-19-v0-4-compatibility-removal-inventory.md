Status: done
Created: 2026-07-19
Updated: 2026-07-19

# Buoy 0.4 Compatibility Removal Inventory

## Question

Which current Buoy compatibility surfaces have active authority scheduling removal in 0.4, which compatibility surfaces have no ratified removal release, and what contract must be confirmed before implementation or release work begins?

## Sources and methods

Inspected the current `work/shape-v0-4-compatibility-removal` checkout at integrated `develop` base `f86cfef`, including:

- active decisions and specifications under `.10x/decisions/` and `.10x/specs/`, with superseded records treated as history rather than authority;
- the owning ticket and its parent/dependency records;
- package metadata in `pyproject.toml` and release mechanics in `docs/releasing.md`, `scripts/release_checks.py`, and `tests/test_release_automation.py`;
- runtime implementation and parser/help in `src/buoy_search/{cli,config,applied_state,apply,plan_artifacts,catalog_cli,github_repo,retriever}.py`;
- user documentation in `README.md`, `docs/{migrating-to-buoy,retrieval,indexing,catalog,evaluation}.md`, and `CHANGELOG.md`;
- compatibility tests in `tests/test_{cli,config,release_automation,applied_state,apply_cli,plan_artifacts,automatic_routing,multi_namespace_retrieval,catalog_cli,github_repo,plan_cleanup}.py`;
- the active operational skill `.pi/skills/turbopuffer-site-rag/SKILL.md` and `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md`;
- repository-wide searches for `0.4`, deprecation/removal language, old branded names, state roots, old plans, compatibility flags, source aliases, and `migrate-local`.

The initial inventory changed no source behavior, package version, state, data, remote resource, release artifact, or executable ticket. After the user ratified the reviewed contract, the focused specs were activated and the bounded execution graph was created as record-only follow-through.

## Authority finding

Exactly three implemented public aliases are explicitly scheduled for removal in 0.4 by active authority:

1. console command `turbo-search`;
2. environment fallback `TURBO_SEARCH_EMBEDDING_MODEL`;
3. environment fallback `TURBO_SEARCH_EMBEDDING_PRECISION`.

The governing authority is `.10x/decisions/buoy-product-identity-and-compatibility-v0-3.md`. It moves these aliases from the rejected 0.3 removal date to 0.4, rejects permanent retention, and explicitly says future removal still requires an executable ticket, verification, and release notes. Supporting active contracts are `.10x/specs/buoy-package-and-cli-identity.md`, `.10x/specs/buoy-local-compatibility.md`, and `.10x/specs/embedding-inference-precision.md`.

No other active record assigns a removal release to another compatibility surface. The `TURBO_SEARCH_*` wording resolves to the two implemented variables above; repository-wide inspection found no other old-branded environment variable.

## Scheduled 0.4 surfaces

### `turbo-search` console alias

Current implementation and promises:

- `pyproject.toml` maps `turbo-search` to `buoy_search.cli:legacy_main` alongside primary `buoy`.
- `src/buoy_search/cli.py` defines `legacy_main`, emits one stderr warning naming removal in 0.4, then runs the same parser/behavior as `buoy`.
- `tests/test_cli.py` imports `legacy_main` and proves JSON stdout remains clean while the exact warning goes to stderr.
- `tests/test_release_automation.py` asserts that the warning, migration guide, config source, and changelog consistently name 0.4.
- `docs/migrating-to-buoy.md` tells scripts and users to replace `turbo-search` with `buoy`.
- `CHANGELOG.md` records the alias as deprecated through 0.3 and scheduled for 0.4 removal.
- `.10x/specs/buoy-package-and-cli-identity.md` currently requires the alias for 0.3, isolated install behavior, warning behavior, and identical help.
- `.10x/specs/buoy-release-validation.md` currently requires isolated installation verification of both commands.

Breakage and migration:

- Shell scripts, task runners, aliases, CI jobs, and operator instructions that invoke `turbo-search` will no longer find a console entry point in a clean 0.4 installation. They must invoke `buoy` with otherwise identical arguments.
- Removing the entry point has no intended plan, DuckDB, state-root, artifact-hash, deterministic-ID, namespace, remote-row, or remote-catalog effect.
- Clean-install validation alone does not prove upgrade behavior. A 0.3-to-0.4 isolated upgrade should verify the old generated launcher is absent and `buoy` still works. Arbitrary stale launchers outside the package manager's ownership cannot be promised deleted by the package.

Candidate package/test/doc implications, not yet authorized for implementation:

- remove only the `turbo-search` script entry from `pyproject.toml` and the now-unreferenced `legacy_main` source hook;
- replace alias-presence/warning tests with clean-install and 0.3-to-0.4 upgrade absence checks;
- update the migration guide and changelog with a clear removal/migration note;
- update active identity/release-validation specifications only after ratification;
- inspect built wheel `entry_points.txt` and installed launchers, not just source text.

### Old branded embedding environment aliases

Current implementation and promises:

- `src/buoy_search/config.py` defines exactly `TURBO_SEARCH_EMBEDDING_MODEL` and `TURBO_SEARCH_EMBEDDING_PRECISION` as legacy aliases for their `BUOY_*` equivalents.
- Old-only input currently supplies the effective value and warns to stderr. Matching old/new values use the current variable without warning. Conflicting values fail with `RuntimeConfigError`. Both warnings name 0.4 removal.
- `tests/test_config.py` covers old-only fallback, matching values, conflicts, defaults, and precision validation.
- `tests/test_cli.py` covers warning/JSON separation and command-level conflict handling.
- `tests/test_release_automation.py`, `docs/migrating-to-buoy.md`, `CHANGELOG.md`, `.10x/specs/buoy-local-compatibility.md`, and `.10x/specs/embedding-inference-precision.md` promise the same 0.4 target.

Breakage and migration:

- Config files, shell profiles, CI secrets/variables, service definitions, and task runners must rename the model and precision keys to `BUOY_EMBEDDING_MODEL` and `BUOY_EMBEDDING_PRECISION` before 0.4.
- Silently ignoring an old-only model variable would select the default model. Silently ignoring an old-only precision variable would select `float32`. Automatic routing may then exclude cards as incompatible; explicit retrieval could query a namespace with a mismatched embedding contract. This makes the exact removed-variable failure behavior execution-critical.
- Approved apply derives its effective model and precision from the verified plan, but `src/buoy_search/cli.py` currently calls `load_config()` before replacing those fields. Old aliases can therefore still warn or conflict on apply even though the plan supplies the effective embedding contract.
- Removal has no reason to rewrite plans, ledgers, state roots, IDs, namespaces, rows, or cards. It must not trigger migration, re-embedding, remote reads/writes, or data deletion by itself.

Candidate implementation/test/doc implications, not yet authorized:

- remove fallback and old/new conflict-selection logic only after the user chooses whether old-variable presence is ignored or rejected;
- preserve `BUOY_*`, `TURBOPUFFER_API_KEY`, `TURBOPUFFER_REGION`, and command-specific `TURBOPUFFER_NAMESPACE` contracts;
- test old-only, old+new equal, old+new different, JSON stderr/stdout behavior, retrieve/evals/autoresearch/config consumers, and apply's plan-derived contract;
- update migration/release notes with exact config substitutions and the chosen failure behavior.

## Compatibility matrix: no 0.4 removal authority

| Surface | Current authority/implementation | Current effect | 0.4 classification and implications |
|---|---|---|---|
| `.turbo-search` implicit state-root fallback | `.10x/specs/buoy-local-compatibility.md`; `src/buoy_search/applied_state.py`; plan/apply help in `src/buoy_search/cli.py`; `tests/test_{applied_state,cli,apply_cli}.py`; migration/indexing docs and skill | Uses the lone old root in place with stderr warning; dual roots fail; explicit root wins; no copy/move/delete | Retain. The active identity decision explicitly separates it from command/environment aliases. Any removal needs a separate state-migration/data-lifecycle decision. Keep `.turbo-search` gitignore/source exclusions in `src/buoy_search/{github_repo,retriever}.py` and related tests. |
| Old plans without `embedding_precision` | `.10x/specs/embedding-inference-precision.md`; `src/buoy_search/apply.py`; `tests/test_plan_artifacts.py` | Interprets missing precision as `float32` while preserving the old artifact hash | Retain. No removal release exists. Removing it would invalidate saved plan data and requires a separate plan-schema/lifecycle contract. |
| Plans recording `.turbo-search` paths and pre-rebrand IDs | `.10x/specs/buoy-local-compatibility.md`; `.10x/specs/apply-to-retrieval-handoff.md`; apply tests and migration docs | Continue when resolved/explicit root matches; IDs and remote identity remain unchanged | Retain. No rebrand-driven rewrite, re-upsert, or rename is authorized. |
| Retrieve `--auto-route` | `.10x/specs/default-remote-namespace-routing.md`; `src/buoy_search/cli.py`; `tests/test_{automatic_routing,cli}.py`; retrieval/migration docs and changelog | Accepted no-op affirmation of default automatic routing; conflicts with explicit namespaces | Retain. No removal date exists. |
| Retrieve `--live` | `.10x/decisions/direct-commands-execute-by-default.md`; `.10x/specs/default-remote-namespace-routing.md`; parser/precedence in `src/buoy_search/cli.py`; automatic/explicit routing tests; docs/changelog | Accepted no-op because retrieval is live by default; conflicts with preview | Retain. No removal date exists. Do not conflate it with evals `--live`, which still activates live eval execution rather than acting as a no-op. |
| Retrieve `--plan` | Same direct-command records and parser, where it aliases `--dry-run` | Requests preview | Retain. No removal date exists. Do not conflate it with apply `--plan PATH`, which selects an artifact and is not a preview compatibility alias. |
| Plan positional source and `--base-url` | `src/buoy_search/cli.py`; `tests/test_cli.py`; local-source specs | Positional `SOURCE` is preferred; `--base-url` remains backward-compatible; conflicting values fail | Retain. No removal release exists. Crawl's required `--base-url` is its current interface, not an announced 0.4 removal. |
| `buoy catalog migrate-local` | `.10x/specs/remote-routing-catalog-cli.md`; `src/buoy_search/catalog_cli.py`; `tests/test_catalog_cli.py`; `docs/{catalog,migrating-to-buoy}.md`; changelog | Preview/approved import of one validated local schema-v1 catalog; never deletes source | Retain. Active authority says it remains available for explicit legacy migration. Removal would need a separate migration-completion and operator/data contract. |
| Pre-rebrand namespace strings, row IDs, source fixtures, and historical record text | identity/local compatibility specs plus dataset/eval/history files | Stable semantic identity or historical provenance, not an executable alias | Retain. String matching on `turbo-search` is not removal authority and must not rename remote or durable identity. |
| Obsolete JSON applied state | `.10x/decisions/duckdb-only-applied-state-hard-cutover.md` | Already ignored and left byte-for-byte unchanged | Not part of 0.4 shaping. It has already been cut over and must not be rediscovered, migrated, or deleted. |

## Direct-command-default conflict check

Integrated behavior agrees across `.10x/decisions/direct-commands-execute-by-default.md`, `.10x/specs/default-remote-namespace-routing.md`, `src/buoy_search/cli.py`, `README.md`, `docs/{retrieval,migrating-to-buoy}.md`, `CHANGELOG.md`, and focused routing tests:

- plain automatic and explicit retrieval execute live;
- `--dry-run` and retrieve `--plan` preview;
- retrieve `--live` is a compatibility no-op;
- `--auto-route` is a compatibility no-op when no explicit namespace is supplied;
- plain interactive apply preflights and prompts; `apply --dry-run` previews; `apply --approve` is automation confirmation.

The scheduled command/environment alias removal does not conflict with those defaults if retained flags remain untouched.

One active skill reference contains two stale statements independently of 0.4 removal: `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md` says live retrieval and evals both require `--live`, and its apply sequence tells operators to set `TURBOPUFFER_NAMESPACE`. Evals still requires `--live`; retrieval does not. Apply takes its namespace from the verified plan: plan `--namespace` selects the recorded value, while apply `--namespace` may assert the same value and a mismatch fails. Ambient namespace setup is therefore not apply authority, and retrieval ignores the environment namespace. `.10x/tickets/2026-07-19-reconcile-scrapling-site-workflow-direct-command-guidance.md` owns both record-only corrections without treating either as authority to remove a flag or change an environment contract. `.pi/skills/turbopuffer-site-rag/SKILL.md` otherwise uses primary `buoy` commands and preserves the state-root fallback; it contains no scheduled 0.4 alias promise.

## Release boundary and required implications

The removal target is a release boundary, not authorization to mutate the current 0.3 package opportunistically. A ratified implementation should be bounded to the 0.4 release line and coordinated with:

- exact version updates in `pyproject.toml` and `src/buoy_search/__init__.py` under the separate release process;
- a `CHANGELOG.md` 0.4 removal entry and explicit script/config migration notes;
- correction of `docs/releasing.md`, which still says the next planned release is 0.3.0 and embeds 0.3.0 commands/assets;
- wheel/sdist inspection, isolated clean install, and isolated 0.3-to-0.4 upgrade verification;
- focused parser/config tests, the complete suite on supported Python versions, link/reference checks, and hosted review gates;
- zero live Turbopuffer calls, state/data mutation, namespace mutation, package publication, tag creation, or release creation during implementation validation.

The release process is GitHub-only today. `docs/releasing.md` states that no PyPI publication occurs; 0.4 shaping does not alter that policy.

## Ratified contract and disposition

On 2026-07-19 the user explicitly ratified the reviewer's exact recommended contract:

1. The first 0.4.0 release removes exactly the `turbo-search` console entry point and fallback acceptance of `TURBO_SEARCH_EMBEDDING_MODEL` / `TURBO_SEARCH_EMBEDDING_PRECISION`.
2. After successful parsing but before actual command-handler dispatch, either removed variable rejects with exit 2, empty stdout even under `--json`, and one value-redacted stderr diagnostic listing present old-to-new mappings in deterministic model-then-precision order. Help/version remain available.
3. Console removal deletes both the `pyproject.toml` script and dedicated `legacy_main` hook.
4. Clean-install validation is supplemented by same-environment upgrade validation: install the immutable released 0.3.0 GitHub wheel, then normally upgrade that isolated environment to the candidate 0.4.0 wheel and inspect installed entry points/launchers.
5. Every other compatibility surface in the matrix remains supported, and no state, data, or remote effect occurs.

The exact active contracts are `.10x/specs/buoy-v0-4-console-alias-removal.md` and `.10x/specs/buoy-v0-4-environment-alias-removal.md`. Execution is owned by the non-executable plan `.10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md` and its two bounded children. The stale retrieval-mode and apply-namespace statements in the Scrapling workflow reference are both separately owned by `.10x/tickets/2026-07-19-reconcile-scrapling-site-workflow-direct-command-guidance.md` and are not part of 0.4 implementation.

## Conclusion

Active authority and user ratification cover only one console alias and two embedding environment aliases for 0.4.0 removal. Every other inspected compatibility surface remains retained. The focused active specs and executable graph now make the command boundary, diagnostics, package upgrade proof, exclusions, and side-effect limits execution-ready without semantic invention.
