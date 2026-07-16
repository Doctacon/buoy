# Representative Semantic Namespace Routing Experiment

## Result

This run measures whether each assistant-drafted public-project question routes to its dataset's home namespace. It is descriptive source-attribution evidence, not product ground truth.

| Strategy | MRR | Recall@1 | Recall@3 | Recall@5 | Unranked | Evaluated |
|---|---:|---:|---:|---:|---:|---:|
| oracle | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 90 |
| lexical | 0.864815 | 0.822222 | 0.911111 | 0.911111 | 8 | 90 |
| semantic | 0.906481 | 0.877778 | 0.933333 | 0.944444 | 5 | 90 |
| hybrid_rrf | 0.927778 | 0.900000 | 0.955556 | 0.955556 | 4 | 90 |

Every recorded route ranking is truncated to the fixed fan-out of five before home-rank and metric calculation; no promotion threshold is defined.

## Benchmark source-revealing bias

- Questions containing a complete home-card title or alias: `79/90`.
- Descriptor-free questions: `11/90`.
- This basket is therefore largely explicit-name attribution. The descriptor-free subset has cross-home ambiguity and is not a clean semantic-routing benchmark.

Descriptor-free cases:
- `buoy:github-local-acquisition` — Which code clones a public GitHub repository locally and resolves branch, commit, and metadata before indexing?
- `buoy:repo-file-selection-corpus` — Where are tracked repository files selected, filtered, and rendered into the Markdown corpus for chunking?
- `buoy:plan-command-local-only` — How does the plan command fetch website and GitHub sources while keeping planning local with respect to Turbopuffer?
- `buoy:apply-preflight-approved-safety` — Where is apply preflight separated from approved live turbopuffer writes and stale deletion guardrails?
- `buoy:plan-artifacts-github-metadata` — Which code propagates GitHub repo metadata into plan manifests, chunk rows, and turbopuffer row fields?
- `buoy:chunking-code-and-markdown` — Where are Markdown docs and code files chunked for retrieval, including line-range code sections?
- `buoy:evals-composite-metrics` — Where is the repository search composite eval metric implemented and validated?
- `buoy:evals-cli-safety` — How does the evals command list cases safely by default and run live retrieval only when requested?
- `click:command-context-invocation` — Where are Command, Group, Context, command invocation, subcommand resolution, parameter sources, and main() execution implemented?
- `requests:prepared-request-response-models` — Where are Request, PreparedRequest, and Response implemented, including URL preparation, headers, body handling, json(), and raise_for_status()?
- `requests:case-insensitive-dict-lookup` — Where is the CaseInsensitiveDict structure implemented and tested for case-insensitive header lookup behavior?

## oracle per repository

| Repository | MRR | R@1 | R@3 | R@5 | Unranked | Evaluated |
|---|---:|---:|---:|---:|---:|---:|
| black | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| buoy | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 10 |
| click | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 10 |
| django | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| flask | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| httpx | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| mkdocs | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| pydantic | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| pytest | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 10 |
| requests | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 10 |
| rich | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| ruff | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| typer | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 10 |

## lexical per repository

| Repository | MRR | R@1 | R@3 | R@5 | Unranked | Evaluated |
|---|---:|---:|---:|---:|---:|---:|
| black | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| buoy | 0.500000 | 0.500000 | 0.500000 | 0.500000 | 5 | 10 |
| click | 0.900000 | 0.900000 | 0.900000 | 0.900000 | 1 | 10 |
| django | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| flask | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| httpx | 0.900000 | 0.800000 | 1.000000 | 1.000000 | 0 | 5 |
| mkdocs | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| pydantic | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| pytest | 0.933333 | 0.900000 | 1.000000 | 1.000000 | 0 | 10 |
| requests | 0.800000 | 0.800000 | 0.800000 | 0.800000 | 2 | 10 |
| rich | 0.900000 | 0.800000 | 1.000000 | 1.000000 | 0 | 5 |
| ruff | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| typer | 0.750000 | 0.500000 | 1.000000 | 1.000000 | 0 | 10 |

## semantic per repository

| Repository | MRR | R@1 | R@3 | R@5 | Unranked | Evaluated |
|---|---:|---:|---:|---:|---:|---:|
| black | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| buoy | 0.458333 | 0.400000 | 0.500000 | 0.600000 | 4 | 10 |
| click | 0.900000 | 0.800000 | 1.000000 | 1.000000 | 0 | 10 |
| django | 0.900000 | 0.800000 | 1.000000 | 1.000000 | 0 | 5 |
| flask | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| httpx | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| mkdocs | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| pydantic | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| pytest | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 10 |
| requests | 0.850000 | 0.800000 | 0.900000 | 0.900000 | 1 | 10 |
| rich | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| ruff | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| typer | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 10 |

## hybrid_rrf per repository

| Repository | MRR | R@1 | R@3 | R@5 | Unranked | Evaluated |
|---|---:|---:|---:|---:|---:|---:|
| black | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| buoy | 0.650000 | 0.600000 | 0.700000 | 0.700000 | 3 | 10 |
| click | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 10 |
| django | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| flask | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| httpx | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| mkdocs | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| pydantic | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| pytest | 0.950000 | 0.900000 | 1.000000 | 1.000000 | 0 | 10 |
| requests | 0.900000 | 0.900000 | 0.900000 | 0.900000 | 1 | 10 |
| rich | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| ruff | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 5 |
| typer | 0.850000 | 0.700000 | 1.000000 | 1.000000 | 0 | 10 |

## Safety and provenance

- Model: `BAAI/bge-small-en-v1.5` at immutable revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, loaded with `local_files_only=True`.
- The run completed without a guard violation. Configured guards blocked the exact socket, process-launch, and path-mutation APIs listed in `plan.json` and `result.json`; this is guard coverage, not OS-wide activity instrumentation.
- Credential environment variables were absent, implicit token use was disabled, and no forbidden Turbopuffer or hosted-client module was imported.
- The model snapshot SHA-256 manifest was identical before and after model construction and evaluation.
- No downstream cross-namespace retrieval ran, and no absent cross-namespace hits were fabricated.
- The model snapshot SHA-256 manifest and immutable input hashes are recorded in `plan.json`.

## Limitations

- The 90 questions and their original file judgments were assistant-drafted and are not human-approved product ground truth.
- Dataset membership supplies only the home-source label. Other namespaces are unlabeled, not known negatives, so route precision is intentionally not reported.
- The run does not measure answer quality, same-query cross-namespace hit quality, ACL behavior, production latency, or production readiness.
- Cached home-namespace hits were not used and absent cross-namespace hits were not fabricated.
- Independent review must inspect benchmark provenance and materially ambiguous home-source questions before ticket closure.
