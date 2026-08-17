Status: active
Created: 2026-08-17
Updated: 2026-08-17
Amends: .10x/specs/buoy-local-compatibility.md, .10x/specs/buoy-package-and-cli-identity.md, .10x/specs/plan-artifact-lifecycle-cleanup.md, .10x/specs/database-document-relation-indexing.md, .10x/specs/duckdb-document-relation-indexing.md

# User-Global Buoy Home Defaults

## Scope

This specification governs only implicit local path selection for new Buoy
runs. It preserves the compact DuckDB schema, compact plan formats, source and
namespace identities, explicit path flags, provider boundaries, and existing
plan cleanup verification.

## Canonical implicit paths

The canonical application home is the absolute path returned by
`Path.home() / ".buoy"`. With no relevant explicit flag:

- applied state is
  `~/.buoy/state/<source-id>/<namespace>/state.duckdb` with its existing
  `apply.lock` sibling;
- crawl output is beneath `~/.buoy/artifacts/site-crawls/` using the existing
  source-derived crawl leaf;
- plan output is beneath `~/.buoy/artifacts/site-crawls/` using a deterministic
  source-derived `*-plan` leaf for every source kind; and
- plan discovery searches only that canonical global artifact tree.

Every implicit path MUST be absolute and independent of the process working
directory. Failure to resolve or create the user home MUST fail clearly; Buoy
MUST NOT fall back to a working-directory path.

## Explicit precedence and forward-only compatibility

`--state-root`, `--out-dir`, and `--plan` continue to override their respective
defaults. One flag MUST NOT silently redirect another path class. Explicit
relative paths retain their current working-directory-relative meaning.

When no override is supplied, Buoy MUST NOT inspect or select noncanonical working-directory
`.buoy`, `.turbo-search`, or `artifacts/site-crawls` paths. Their presence,
absence, combination, contents, or validity MUST NOT alter implicit path
selection. Buoy MUST NOT copy, move, merge, import, rewrite, archive, delete,
backfill, or garbage-collect those existing paths. An operator may still use an
old state root with `--state-root` and an old plan with `--plan`; once selected,
normal state writes and verified success-only plan cleanup apply. A working
directory equal to `Path.home()` necessarily names the canonical `.buoy`
itself, not a separate ignored project root.

This contract supersedes only the implicit `.turbo-search` fallback and
dual-root refusal clauses of the older local-compatibility records. It does
not revive obsolete JSON state or any removed compatibility surface.

## Plan discovery and lifecycle

Implicit apply validates supported schema-v3 plan metadata only under the
canonical global artifact root. Exactly one supported pending plan may be
selected automatically. Zero candidates produces the existing actionable
missing-plan failure; two or more candidates MUST fail before credential,
model, state mutation, provider, or cleanup work and require explicit
`--plan` selection.

The canonical artifact root is the only managed cleanup exception inside the
application home. Cleanup MAY remove a plan directory strictly below that
root only after all existing verification, identity, race, and lifecycle
conditions pass. It MUST retain and warn for:

- the application-home root or canonical artifact root itself;
- any target beneath `~/.buoy/state`;
- any other application-home subtree;
- any plan beneath an explicit/custom state root unless it is outside that
  root under the preexisting rule;
- malformed, legacy, corrupt, replaced, raced, or symlink targets; and
- every failed, cancelled, dry-run, partial-success, or otherwise incomplete
  apply covered by the active lifecycle specification.

Race resistance is bounded to cooperative Buoy concurrency and to rejecting
ancestor, symlink, and whole-plan replacement before the fd/symlink-safe final
removal begins. POSIX does not provide this Python implementation with an
atomic compare-and-unlink primitive for child entries. An actively malicious
same-UID process that discovers and rewrites names inside the private random
quarantine after its final binding is outside this contract; no universal
adversarial-race guarantee is claimed.

## Privacy and ownership

The application home contains source URLs, operational metadata, and pending
plan content. The implementation MUST create a new canonical home with
user-only directory permissions where the platform supports POSIX modes and
MUST reject a symlink or non-directory at the canonical home boundary before
writing managed assets.

Turbopuffer credentials, BigQuery ADC, Snowflake profiles, source credentials,
raw provider output, and environment values MUST NOT be persisted there by
this change. The `uv` tool environment and Hugging Face/Sentence Transformers
cache retain their standard ownership and paths.

## Acceptance criteria

1. Two unrelated working directories resolve identical absolute implicit
   state, crawl, plan, and apply-discovery paths under a temporary user home,
   and neither working directory gains `.buoy` or `artifacts` output.
2. Working-directory `.buoy`, `.turbo-search`, both together, and historical
   artifact trees remain byte-identical and have no effect on implicit paths.
   Explicit old roots/plans remain usable.
3. Website, GitHub, local-document, DuckDB, BigQuery, and Snowflake defaults
   use the canonical global prefix without changing source-derived identity;
   every plan leaf uses `-plan` and remains distinct from its crawl leaf.
4. Implicit apply selects exactly one valid global plan and rejects ambiguous
   global candidates; explicit `--plan` still accepts a valid path anywhere.
5. Planning without prior global state creates no DuckDB. A mocked fully
   successful approved apply writes only the canonical global state path.
6. Successful and supersession cleanup can remove exact verified managed
   plans, while state, noncanonical home paths, malformed targets, symlinks,
   replacements, and all historical project-local assets survive.
7. README, changelog, and indexing/migration documentation describe the new
   forward-only defaults and explicit legacy opt-in without promising or
   performing migration. The exact active-routing receipt keeps
   `src/buoy_search/cli.py` byte-identical, so its legacy default-path option
   help strings remain a disclosed compatibility limitation pending a
   separately authorized routing recertification; no receipt is silently
   rewritten or bypassed by this task.
8. Focused and complete tests on Python 3.11 and 3.13, source/distribution
   validation, lock validation, clean-wheel CLI smoke tests, and diff hygiene
   pass without provider, credential, model, publication, or existing-asset
   mutation.
