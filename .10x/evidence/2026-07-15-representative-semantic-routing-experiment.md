Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Relates-To: .10x/tickets/done/2026-07-15-run-representative-semantic-routing-experiment.md, .10x/specs/representative-semantic-namespace-routing-experiment.md

# Representative Semantic Routing Experiment

## What was observed

Commit `a15bc686a645d1081f78272058a8da02751ff479` implemented the bounded evaluator and initial guarded run artifacts under `autoresearch/runs/semantic-routing-representative-20260715/`. Independent review then found that the initial artifacts reported full semantic and hybrid rankings despite the specified fixed route fan-out of five, overstated hard-coded zero counters as observation, under-covered escape APIs, and did not quantify benchmark source-revealing bias.

Corrective commit `d4bef7873c0f281aa1b4d5cc693464234ecf44fa` enforced top-five recording/scoring, hardened guards, replaced counters with factual completion/configuration checks, quantified source-revealing bias, and regenerated `plan.json`, `result.json`, and `report.md` with the pinned cached model. Neither commit changed production files under `src/buoy_search/` or added dependencies.

The evaluator loaded the exact 13 tracked dataset paths and mappings listed in `.10x/specs/representative-semantic-namespace-routing-experiment.md` and `plan.json`: Black 5, Buoy 10, Click 10, Django 5, Flask 5, HTTPX 5, MkDocs 5, Pydantic 5, pytest 10, Requests 10, Rich 5, Ruff 5, and Typer 10, totaling 90 questions. Dataset-local identity is retained as separate `repo_key` and `case_id` fields and as composite `repo_key:case_id` identity. File judgments were not loaded into evaluation cases.

## Corrected measurements

Every recorded route ranking is truncated to five before its home rank and metrics are calculated. A separate recalculation from all committed per-question ranks reproduced these authoritative aggregate source-attribution values:

| Strategy | MRR | Recall@1 | Recall@3 | Recall@5 | Unranked | Evaluated |
|---|---:|---:|---:|---:|---:|---:|
| oracle | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0 | 90 |
| lexical | 0.864815 | 0.822222 | 0.911111 | 0.911111 | 8 | 90 |
| semantic | 0.906481 | 0.877778 | 0.933333 | 0.944444 | 5 | 90 |
| hybrid RRF | 0.927778 | 0.900000 | 0.955556 | 0.955556 | 4 | 90 |

The initial semantic MRR `0.913246` with zero unranked and hybrid MRR `0.933153` with zero unranked are superseded because they included home ranks beyond the fixed fan-out. Recall@1/3/5 did not change, but those initial MRR and unranked values must not be used.

## Benchmark source-revealing bias

Complete normalized phrase matching against each question's home-card title and aliases found:

- `79/90` questions contain their home title or alias;
- `11/90` are descriptor-free.

The descriptor-free identities are:

- `buoy:github-local-acquisition`
- `buoy:repo-file-selection-corpus`
- `buoy:plan-command-local-only`
- `buoy:apply-preflight-approved-safety`
- `buoy:plan-artifacts-github-metadata`
- `buoy:chunking-code-and-markdown`
- `buoy:evals-composite-metrics`
- `buoy:evals-cli-safety`
- `click:command-context-invocation`
- `requests:prepared-request-response-models`
- `requests:case-insensitive-dict-lookup`

This basket is therefore largely an explicit-name source-attribution test. The 11 descriptor-free cases have cross-home ambiguity and are not a clean semantic-routing benchmark. `result.json` records the matching descriptors and complete descriptor-free case content; `report.md` lists the descriptor-free questions.

## Model and guard completion

The corrected run used open-source `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` with the exact revision and `local_files_only=True` passed to `SentenceTransformer`. It produced normalized float32 384-dimensional embeddings. Cards were encoded as deterministic labeled passages; questions used the documented BGE query prefix.

Before model import/construction, the process set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_DATASETS_OFFLINE=1`, `HF_HUB_DISABLE_IMPLICIT_TOKEN=1`, and `HF_HUB_DISABLE_TELEMETRY=1`, and removed `HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN`, `TURBOPUFFER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `COHERE_API_KEY` from its environment.

The successful run recorded all credential variables absent, all offline controls set, no forbidden `turbopuffer`, `openai`, `anthropic`, or `cohere` client module imported, and the 12-file pinned model snapshot SHA-256 manifest identical before and after model construction/evaluation. The manifest includes `model.safetensors` SHA-256 `3c9f31665447c8911517620762200d2245a2518d6e7208acc78cd9db317e21ad` and `onnx/model.onnx` SHA-256 `828e1496d7fabb79cfa4dcd84fa38625c0d3d21da474a00f08db0f559940cf35`. `plan.json` records all model and input hashes.

Configured Python guards rejected:

- 8 socket APIs, including connect/address resolution and `send`, `sendall`, `sendto`, and `sendmsg`;
- 14 process APIs, including `subprocess.Popen`, `os.system`, available `os.spawn*`/`posix_spawn*`, `fork`, and `forkpty`;
- 19 path-mutation surfaces, including write-mode opens, write-flag `os.open`, `ftruncate`, `truncate`, symlink, hard link, node/FIFO/directory creation, replacement/rename/deletion, permission/owner/time changes, and the other exact platform APIs listed in the artifacts.

Writes were allowed only under the experiment directory and process-owned `.semantic-routing-tmp`; the model cache remained outside that allowlist. The run completed without a guard violation and removed the temporary directory. These are concrete Python guard configuration/completion facts, not instrumentation or a claim to have observed every OS activity. No downstream cross-namespace retrieval ran and absent cross-namespace hits were not fabricated.

## Procedure

Corrected guarded rerun:

```text
env -u HF_TOKEN -u HUGGING_FACE_HUB_TOKEN -u TURBOPUFFER_API_KEY -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u COHERE_API_KEY HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 HF_HUB_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 uv run python autoresearch/runs/semantic-routing-representative-20260715/evaluate.py --replace-result
exit 0; loaded 199/199 cached weights; emitted the corrected aggregate metrics above
```

Focused tests:

```text
uv run python -m unittest tests.test_semantic_routing_representative
Ran 18 tests in 0.040s
OK
```

Full suite and mechanical validation:

```text
uv run python -m unittest discover -s tests
Ran 292 tests in 6.925s
OK

git diff --check
exit 0; no output
```

A separate local recalculation loaded committed `plan.json` and `result.json`; asserted fan-out five, 13 cards, 90 cases per strategy, all recorded rankings at most five, all non-null home ranks in `[1, 5]`, `79/11` bias counts, successful guard completion, absent forbidden modules/credentials, and equal before/after model manifests; and recomputed each MRR, recall, unranked count, and evaluated count from per-question ranks. It exited 0 with the corrected metrics above. The process-owned temporary directory was absent afterward, and the corrective diff contained no `src/buoy_search/` path.

## What this supports or challenges

Supports:

- Exact lexical card aliases leave eight home namespaces unranked at fan-out five.
- On this source-attribution proxy, semantic cards improve MRR and recall@1/3/5 over lexical cards.
- Equal-weight hybrid RRF using production `RRF_K = 60` gives the strongest measured non-oracle aggregate values.
- The pinned cached model can complete under the documented offline, credential, socket, process, path-write, client-module, and snapshot-integrity controls.

Challenges and limits:

- `79/90` questions explicitly reveal their home project's title or alias, substantially limiting evidence for semantic routing beyond project-name attribution.
- The 11 descriptor-free questions have cross-home ambiguity and do not establish clean alternative relevance.
- Dataset membership labels only the originating repository namespace. Other namespaces are unlabeled, not known negatives.
- The assistant-drafted questions are not human-approved product ground truth.
- This experiment does not establish route precision, answer quality, downstream same-query multi-namespace retrieval quality, ACL correctness, latency, or production readiness.
- No comparable cross-namespace hit lists exist, so cached home-namespace hits were not reused and absent hits were not fabricated.

## Conclusion

The accepted closure blockers were corrected and reproducible artifacts are ready for independent re-review. The owning ticket remains active pending that separate review; this evidence does not close it.
