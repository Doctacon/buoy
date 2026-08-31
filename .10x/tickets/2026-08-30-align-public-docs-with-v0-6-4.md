Status: active
Created: 2026-08-30
Updated: 2026-08-30
Parent: None
Depends-On: .10x/tickets/2026-08-30-minimize-readme-to-basic-workflow.md

# Align public docs with v0.6.4

## Scope

Align the newcomer installation and focused retrieval/telemetry documentation
with the published `v0.6.4` Git tag.

- Replace the README's v0.6.1 wheel URL with the user-approved immutable Git-tag
  installation:

  ```bash
  uv tool install "git+https://github.com/Doctacon/buoy.git@v0.6.4"
  ```

- Add explicit README Learn more links for automatic routing and local retrieval
  telemetry without expanding the quick-start workflow.
- Make `docs/retrieval.md` and `docs/telemetry.md` describe v0.6.4 behavior rather
  than post-v0.6.4 changes on `develop`.
- Preserve useful v0.6.4 retrieval and telemetry guidance, command examples,
  safety/privacy boundaries, and detailed operational reference material.

## Source authority

- Git tag `v0.6.4` resolves locally to
  `42ec57198f4a8b2cda886e4a43e97b3d49ab81ba`.
- `docs/retrieval.md` and `docs/telemetry.md` at that tag are the behavioral
  documentation baseline for this ticket.
- GitHub release `v0.6.4` exists but has no downloadable assets, so a fabricated
  `buoy_search-0.6.4-py3-none-any.whl` URL is prohibited.
- The user explicitly approved the immutable Git-tag installation form.

## Acceptance criteria

- README installs exactly from `git+https://github.com/Doctacon/buoy.git@v0.6.4`.
- README retains the exact three-command quick start from
  `.10x/tickets/2026-08-30-minimize-readme-to-basic-workflow.md`.
- README Learn more includes clearly labeled links for automatic retrieval
  routing and local retrieval telemetry.
- `docs/retrieval.md` matches v0.6.4 retrieval behavior, including its default
  embedding-worker boundary, automatic routing, explicit override, ranking,
  evidence, catalog, and evaluation guidance; it does not claim post-v0.6.4
  cross-encoder worker behavior.
- `docs/telemetry.md` matches v0.6.4 schema-v2 command telemetry and v1-to-v2
  migration behavior; it does not claim post-v0.6.4 schema-v3 inference or
  provider-invocation telemetry.
- All local Markdown links resolve, displayed relevant CLI help surfaces parse
  using the v0.6.4 source/tag where safely checkable, and `git diff --check`
  passes.

## Exclusions

Publishing or modifying a GitHub release, adding release assets, changing code,
changing CLI behavior, modifying package metadata or dependencies, live source
access, provider calls, model loads, live retrieval, index/catalog mutation,
and release deployment are excluded.

## Evidence expectations

Record changed files, version/source comparison, local-link validation, safe
command/help checks, `git diff --check`, and residual risks. Validation must not
perform live source, model, provider, retrieval, indexing, catalog, publication,
or deployment operations.

## Blockers

None. The user ratified v0.6.4 alignment and the immutable Git-tag install after
being informed that the GitHub release has no wheel asset.

## Progress and notes

- 2026-08-30: Inspected current README, retrieval and telemetry docs, release
  tags, GitHub release asset metadata, changelog, source references, and active
  retrieval/telemetry records.
- 2026-08-30: Confirmed post-v0.6.4 `develop` changes currently add
  cross-encoder worker and telemetry-v3 details beyond the requested release
  baseline.
- 2026-08-30: Updated the minimal README to install from the approved immutable
  `v0.6.4` Git tag, preserved the exact three-command workflow, relabeled the
  retrieval guide for automatic routing, and added the focused local telemetry
  guide link.
- 2026-08-30: Restored `docs/retrieval.md` and `docs/telemetry.md` byte-for-byte
  to their `v0.6.4` tag versions. Exact `cmp` checks pass; no post-v0.6.4
  cross-encoder-worker or telemetry-v3 claims remain.
- 2026-08-30: Safe validation found eight README local links and zero local
  links in each focused guide; all resolve. `plan`, `apply`, `retrieve`, and
  `telemetry` help parsed from an archived `v0.6.4` source tree using the
  current environment and a temporary generated-version shim. The initial help
  attempt without that build-generated `_version.py` failed as expected; the
  corrected isolated check passed all four commands. `git diff --check` passes
  and no files are staged. No live source, model, provider, retrieval, indexing,
  catalog, publication, or deployment operation ran. Independent review remains
  for the parent workflow.
