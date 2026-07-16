Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commits `a15bc686a645d1081f78272058a8da02751ff479`, `d4bef7873c0f281aa1b4d5cc693464234ecf44fa`, and `ea488bf3c75aeab16077e3afc7c7d9f2531f3bb1`
Verdict: pass

# Representative Semantic Routing Experiment Review

## Target

Independent adversarial review of the experiment implementation, corrected run artifacts, tests, evidence, and ticket against `.10x/specs/representative-semantic-namespace-routing-experiment.md`.

Two fresh reviewers separately examined algorithmic/spec correctness and safety/provenance. The parent independently inspected the committed diff and recalculated top-five aggregate metrics from `result.json`.

## Findings

### Significant — fixed fan-out was initially applied only to recall cutoffs

Initial commit `a15bc686a645d1081f78272058a8da02751ff479` retained all 13 semantic/hybrid ranks. MRR included homes below the fixed top-five route, and those homes were not counted as unranked. Initial semantic MRR `0.913246` / unranked `0` and hybrid MRR `0.933153` / unranked `0` therefore conflicted with the specified route fan-out.

Resolved by `d4bef7873c0f281aa1b4d5cc693464234ecf44fa`. Every strategy ranking is now truncated before home-rank and metric calculation. Independent recomputation over all 90 cases and all 13 per-repository groups matched the corrected artifacts:

| Strategy | MRR | Recall@1 | Recall@3 | Recall@5 | Unranked |
|---|---:|---:|---:|---:|---:|
| lexical | 0.864815 | 0.822222 | 0.911111 | 0.911111 | 8 |
| semantic | 0.906481 | 0.877778 | 0.933333 | 0.944444 | 5 |
| hybrid RRF | 0.927778 | 0.900000 | 0.955556 | 0.955556 | 4 |

Regression tests cover a home below fan-out becoming unranked and verify truncated semantic/hybrid results.

### Significant — initial safety fields overstated what hard-coded counters proved

The initial result encoded zero-value activity counters and the first evidence wording called them observed. The first Python guards also omitted several direct socket-send, process-launch, and path-mutation escape APIs.

Resolved by `d4bef7873c0f281aa1b4d5cc693464234ecf44fa`. The corrected evaluator:

- rejects the enumerated socket connect/send APIs;
- rejects subprocess and available `os` process-launch APIs;
- path-checks the enumerated write, creation, link, truncation, rename, deletion, permission, ownership, and timestamp APIs;
- verifies credential variables absent and forbidden hosted/Turbopuffer client modules unimported;
- compares the pinned model snapshot manifest before and after execution;
- reports exact configured Python guard coverage and successful no-violation completion rather than claiming OS-wide instrumentation.

Focused tests exercise UDP send, process launch, cache mutation, links, truncation, and allowed in-root writes. The residual Python-level-versus-OS-wide boundary is stated in machine-readable and human-readable artifacts.

### Significant experimental limit — most questions reveal the source name

The corrected artifact measures that 79 of 90 questions contain a complete home-card title or alias. Only 11 are descriptor-free, and those include materially cross-home-ambiguous Click/Typer, Requests/HTTPX, and generic Buoy questions.

The report and evidence now characterize the basket primarily as explicit-name source attribution. They do not claim route precision, answer quality, same-query cross-namespace retrieval quality, ACL correctness, latency, or production readiness.

### Correct

- All 90 composite `repo_key:case_id` identities are unique.
- Card/input validation is fail-closed and no direct benchmark question, case ID, or file locator appears in card text.
- Lexical normalization, complete phrase matching, descriptor deduplication, scoring, and tie order match the specification.
- Semantic ranking uses normalized float32 cosine scores and deterministic repository-key ties.
- Hybrid routing imports production `RRF_K`, requires 60, and uses equal-weight reciprocal-rank fusion.
- Model identity, revision, input hashes, and 12-file resolved snapshot manifest are recorded.
- The final run completed with pinned local-only model loading under the corrected guards.
- The narrow `.gitignore` exception tracks only this experiment directory; unrelated run outputs remain ignored.
- No production package file, dependency, lockfile, live service, remote state, applied state, or graph changed.
- Eighteen focused and 292 full-suite tests passed; `git diff --check` passed.

## Verdict

Pass. The initial correctness and evidence defects were repaired, artifacts regenerated, metrics independently reproduced, and both fresh re-reviewers reported no blocker.

## Residual risk

- Python-level guards are not OS-wide activity instrumentation.
- Questions and cards were visible to the same author.
- The 79/90 source-name exposure and unlabeled alternatives sharply limit generalization.
- The experiment does not justify production routing or graph implementation.
- No automatic follow-up is opened from this review because no promotion threshold or production interface is ratified. A later production or human-reviewed benchmark slice requires a new user-approved specification/ticket rather than widening this completed experiment.
