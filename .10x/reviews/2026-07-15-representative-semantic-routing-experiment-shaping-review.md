Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commit `9fe6ed305de4e31cb7154fa094a2fa1bede302b3`
Verdict: pass

# Representative Semantic Routing Experiment Shaping Review

## Target

Independent adversarial review of the replacement for the cancelled five-stage synthetic routing pilot:

- `.10x/specs/representative-semantic-namespace-routing-experiment.md`
- `.10x/tickets/done/2026-07-15-run-representative-semantic-routing-experiment.md`
- superseded synthetic specs and cancelled synthetic tickets
- the terminal research parent and repaired record references

The reviewer compared commit `9fe6ed305de4e31cb7154fa094a2fa1bede302b3` with parent `8144165bfacb7a2c7e04d27f0376442de815d4b9` and inspected the tracked datasets, `.gitignore`, model revision contract, source constants, and record graph.

## Findings

### Correct

- The experiment now consumes 13 tracked seed datasets directly. Their specified counts total exactly 90 questions; it no longer depends on the absent, ignored 28 MB raw-basket artifact.
- The single executable ticket owns the future narrow `.gitignore` exception for its run directory. This shaping commit does not create experiment files or modify `.gitignore`.
- The four-track research parent is terminal under `.10x/tickets/done/`, all four children and research outputs are complete, and the independently owned experiment does not pretend to be unfinished research-plan scope.
- The model contract pins `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, matching the inspected local cache. Exact local-only/offline variables, credential removal, socket rejection, path-based write restrictions, read-only cache treatment, and snapshot hashing are specified.
- Lexical descriptors are normalized and deduplicated across title, aliases, and tags. Repeated question occurrences do not increase scores, and tie-breaking is deterministic.
- Historical references point to superseded, cancelled, or done locations; no obsolete active-path reference remains.
- The executable ticket is bounded and cold-start-ready. It names inputs, behavior, tests, artifacts, evidence, exclusions, and failure handling without adding production semantics.
- The reviewed commit changes only `.10x/` records. No source, tests, dependencies, `.gitignore`, or experiment artifacts were implemented. `git diff --check` passed.

### Blockers

None.

## Verdict

Pass. The representative route-attribution experiment is sufficiently specified and bounded for a cold-start executor. Implementation remains deferred to the separately named open ticket and a new `work/*` worktree from integrated `develop`.

## Residual risk

- The questions are assistant-drafted and visible to card authors, not human-approved product ground truth.
- Alternative relevant namespaces are unlabeled; home-source rank must not be reported as route precision.
- The experiment does not measure same-query cross-namespace retrieval, answer quality, production ACLs, latency, or production readiness.
- Buoy, Click, and Requests derive exact home namespace from the active spec mapping rather than a dataset `metadata.namespace`; implementation evidence should keep that provenance visible.
- Case IDs are only dataset-local. Results must retain repository key plus case ID; HTTPX and Requests both contain `top-level-request-api`.
