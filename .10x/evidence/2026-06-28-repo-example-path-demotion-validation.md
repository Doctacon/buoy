Status: recorded
Created: 2026-06-28
Updated: 2026-06-28
Relates-To: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md, .10x/decisions/namespace-ranking-defaults.md, .10x/knowledge/repo-search-ranking-defaults.md

# Repo Example/Demo Path Demotion Validation

## What was observed

A ranking-only hypothesis passed the five-repo no-regression policy: demote repository example/demo paths in the `repo_code` profile when the query is not asking for examples/tutorials/samples/demos.

The demoted path families are:

- `examples/`
- `docs_src/`
- paths containing `example_scripts/`
- paths containing `/example/` or `/examples/`

Queries containing example intent tokens (`example`, `examples`, `sample`, `samples`, `tutorial`, `tutorials`, `demo`, `demos`) do not receive the demotion.

This is retrieval/ranking-only. It does not change indexing, namespaces, row schema, embeddings, or live writes.

## Procedure

Exploration before the passing result:

- Tuned file-card metadata multipliers offline against cached live retrieval candidates; no variant removed the turbo-search regression.
- Tested candidate-depth/ranking-pool/aggregation grids on baseline namespaces; no global knob improved without regression.
- Tested `repo_code` profile-weight variants; broad coefficient changes did not pass no-regression.
- Tested an example/demo path demotion, which improved Click/pytest/Typer while leaving turbo-search and Requests unchanged.

Live validation command shape:

```bash
uv run turbo-search evals --live --dataset <repo-seed-dataset> \
  --namespace <existing-baseline-namespace> \
  --top-k 10 --candidates 200 --json
```

Namespaces:

- `github-doctacon-turbo-search-v2-clean`
- `github-psf-requests-v1`
- `github-pallets-click-v1`
- `github-pytest-dev-pytest-v1`
- `github-fastapi-typer-v1`

Artifacts:

- `autoresearch/runs/repo-example-path-demotion-20260628/example-path-demotion-summary.json`
- `autoresearch/runs/repo-example-path-demotion-20260628/example-path-demotion-report.md`
- per-repo eval JSON files under `autoresearch/runs/repo-example-path-demotion-20260628/`

No plan/apply, row writes, stale deletion, or namespace deletion was run for this validation.

## Result

| Repo | Baseline score | New score | Δ score | Baseline P@5 | New P@5 | Δ P@5 |
|---|---:|---:|---:|---:|---:|---:|
| turbo-search | 87.760 | 87.760 | +0.000 | 0.540 | 0.540 | +0.000 |
| Requests | 84.426 | 84.426 | +0.000 | 0.420 | 0.420 | +0.000 |
| Click | 72.474 | 72.816 | +0.342 | 0.400 | 0.420 | +0.020 |
| pytest | 84.742 | 86.042 | +1.299 | 0.640 | 0.660 | +0.020 |
| Typer | 59.423 | 59.710 | +0.287 | 0.380 | 0.400 | +0.020 |

Averages across the five-repo basket:

- Score: `77.765 -> 78.151` (`+0.386`)
- P@5: `0.476 -> 0.488` (`+0.012`)

## What this supports or challenges

Supports:

- Example/demo paths are a recurring retrieval distractor for implementation-oriented repository queries.
- A conditional demotion is safer than broad doc/test/source coefficient changes.
- The current five-repo basket supports promoting the demotion into the default `repo_code` profile because no repo regressed by composite score or P@5.

Challenges/limits:

- The eval labels are still assistant-drafted.
- This does not address oversize source blind spots; central oversized files remain skipped in default indexes.
- This does not make file-card metadata or metadata preambles default-safe.

## Conclusion

Promote conditional example/demo path demotion inside the default `repo_code` ranking profile. It is the next valid no-regression improvement found after the metadata/file-card and ranking-grid hypotheses.
