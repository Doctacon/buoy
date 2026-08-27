Status: active
Created: 2026-08-27
Updated: 2026-08-27
Decision: .10x/decisions/buoy-versions-repo-evals-and-gates-only-default-promotion.md
Amends: .10x/specs/repo-search-eval-autoresearch.md

# Versioned Repository Evaluations and Promotion Gate

## Purpose and scope

Separate immutable historical repository-search evidence from current regression data, and mechanically require expensive ranking evidence only when active ranking defaults change.

## Artifact model

A repository evaluation version consists of:

- immutable `dataset_id` and integer `dataset_version`;
- immutable judgment cases;
- a dataset raw-byte hash;
- optional `derived_from` artifact identity and explicit migration metadata;
- `baseline_status`, exactly `pending` or `recorded`;
- when pending, a path-membership manifest that makes no source-snapshot or benchmark claim; and
- when recorded, a content-addressed corpus manifest with repository/source identity plus an immutable benchmark artifact identity.

A path-membership manifest MUST NOT be named, exposed, or accepted as a corpus identity. Only `baseline_status=recorded` with complete content-addressed corpus and benchmark identities may support promotion.

Promotion-eligible baskets MUST be registered in the versioned packaged registry `src/buoy_search/data/repo_ranking_promotion_baskets.json`. Each registered basket MUST contain exactly the 13 governed repositories. Every member MUST name repository-relative dataset, corpus-manifest, and recorded-benchmark artifact paths plus exact raw-byte SHA-256 identities. Validation MUST read those actual files, reject missing/non-regular/symlink/escaping paths, reproduce every hash, and validate recorded benchmark identity/config/result linkage.

Raw-byte equality alone is insufficient. Every registered dataset MUST use exact schema v1 and match its basket member's dataset ID, positive version, and repository. It MUST contain a nonempty list of unique-ID cases with bounded questions and nonempty judgments; judgments have exact path/grade/reason shape, canonical unique repository-relative paths, integer grades in `[0,3]`, and bounded nonempty reasons. Every judgment path MUST occur in the member's corpus inventory.

Every registered corpus manifest MUST use exact schema v1 and match its member's repository plus exact full Git-commit source identity. It MUST contain a nonempty, sorted, unique canonical document inventory. Every document has exact path/content-hash shape and a non-placeholder lowercase SHA-256 content identity. The canonical inventory hash and document count MUST match both the manifest and basket member. Semantically invalid JSON MUST fail even when its raw file hash and enclosing basket hash are consistently regenerated.

A promotion artifact may reference only an exact registered basket ID/version/hash; self-declared or unregistered basket members are not authority. When no complete recorded basket exists, the truthful production registry contains no basket entry.

Historical versions MUST NOT be edited. Their path membership is validated against their recorded corpus manifest/source snapshot, not the current checkout. Historical source files need not exist at `HEAD`.

## Current Buoy successor

The existing frozen Buoy dataset and source-manifest entry MUST be preserved byte-for-byte as historical v1 evidence. The reorganized package MUST use a v2 current dataset that:

- carries forward every existing query, case ID, judgment grade, reason, and non-path field unchanged;
- maps each moved path through an explicit old-to-new mapping;
- references a deterministic path-membership manifest for the reorganized local source while pending;
- records lineage to v1;
- begins with `baseline_status=pending`; and
- makes no score or promotion claim.

The v2 migration requires no retrieval, model, provider, namespace, or credential operation. A deterministic semantic comparison MUST prove only version/lineage/path/corpus metadata changed.

## Fast checks for every PR

Ordinary CI MUST remain local and deterministic. It MUST validate:

- dataset schema, IDs, grades, and matching rules;
- uniqueness and referential integrity;
- internal artifact and manifest hashes;
- historical artifact consistency against recorded corpus manifests without checking historical paths against `HEAD`;
- current pending-dataset path existence against its path-membership manifest;
- exact v1-to-v2 carried-forward judgment semantics and declared path mapping;
- ranking unit/fixture behavior; and
- promotion-authority-file schema.

Ordinary CI MUST NOT run live retrieval, load/download models, access credentials/providers, or require a recorded v2 baseline.

## Ranking-default authority

Active runtime ranking defaults MUST be declared in exactly one packaged authority file:

```text
src/buoy_search/data/ranking_defaults.json
```

The file MUST contain the active repository and website default values currently implemented by `ranking_defaults_for_namespace`, plus an explicit authority schema/revision. Runtime code MUST read or import those values through one validated boundary; duplicate independently editable default literals are forbidden.

A pull request is a ranking-promotion PR exactly when this authority file differs from its merge base. CI MUST determine that mechanically from the merge-base diff; labels, branch names, changed implementation paths, and contributor claims are not authority. Push CI MUST compare against the event's previous commit. CI MUST fail closed when no required comparison base is available, except for one explicitly selected authority-introduction mode that proves the introduced values equal the pre-file code defaults.

## Promotion gate

A ranking-promotion PR MUST include/reference one immutable promotion artifact that:

- names the exact old and proposed authority-file hashes and values;
- references one exact ID/version/hash from the versioned 13-repository promotion-basket registry;
- uses that exact registered basket for both baseline and candidate;
- requires every registered basket member to be `baseline_status=recorded` and reproduces its actual dataset, corpus-manifest, and immutable benchmark artifact bytes/hashes;
- records complete baseline and candidate configurations/results;
- proves every non-authority input is exactly equal between baseline and candidate, including retrieval options, model/revision, corpus, dataset, and retrieval-contract identities;
- allows retrieval options only through an exact bounded safe-field schema; arbitrary objects, headers, auth fields, URLs, and credential-bearing values are invalid;
- proves the candidate passes `.10x/decisions/repo-ranking-promotion-policy.md`;
- contains no credentials or provider secrets; and
- reproduces under the repository validator.

CI validates the supplied artifact and policy result; it does not need to rerun an expensive provider-backed benchmark. Producing that artifact is a separate explicitly authorized benchmark operation before the promotion PR.

Changing ranking implementation or adding experimental options without changing `ranking_defaults.json` is an ordinary PR and cannot activate those changes as defaults.

## Acceptance scenarios

1. Given historical v1 paths absent from `HEAD`, fast validation passes when v1 remains internally consistent with its recorded snapshot.
2. Given the reorganized v2 dataset, every current judged path exists and all non-path judgment semantics equal v1 through the declared mapping.
3. Given `baseline_status=pending` and no ranking-default authority change, ordinary CI passes without benchmark execution.
4. Given a PR that changes ranking implementation but not the authority file, the promotion gate is not invoked and active defaults remain unchanged.
5. Given a PR that changes the authority file without a valid matching promotion artifact, CI fails.
6. Given a pending dataset, path-only manifest, incomplete/unregistered basket, missing/tampered member file, unequal baseline/candidate input, unsafe retrieval option, or missing comparison base, promotion validation fails.
7. Given a complete registered basket whose 13 dataset/corpus/benchmark files reproduce their identities and a valid same-basket artifact passing promotion policy, CI accepts the authority-file change without rerunning the benchmark.

## Acceptance criteria

- V1 historical bytes and identities remain preserved.
- V2 current paths and lineage validate with unchanged judgment semantics.
- Existing full-suite path checks no longer couple historical v1 paths to `HEAD`.
- `ranking_defaults.json` is the sole active-default authority and reproduces current behavior.
- Fast CI passes with v2 baseline pending and performs no external/model operation.
- The production promotion-basket registry is schema-valid and empty while Buoy v2 remains pending.
- Promotion-gate tests cover no-change, implementation-only, PR and push comparison, missing-base failure, pending rejection, incomplete/unregistered basket, missing/tampered dataset/corpus/benchmark bytes, semantically invalid consistently rehashed dataset/corpus JSON, mismatched/unequal inputs, unsafe options/values, missing artifact, policy failure, and passing complete registered-basket cases.

## Explicit exclusions

- New labels, label review, changed grades/reasons/queries, or claims of human ground truth.
- Running a new baseline or candidate benchmark in this implementation slice.
- Changing active ranking defaults while introducing the authority file.
- Provider, namespace, catalog, credential, release, publication, or deployment operations.
