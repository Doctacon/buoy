Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-turbopuffer-hybrid-retrieval-client.md, .loom/evidence/2026-06-20-jellyfish-live-indexing.md

# Jellyfish live turbopuffer retrieval validation

## Scope validated

Ran approved live hybrid retrieval against the indexed Jellyfish docs namespace using non-secret runtime configuration:

- `TURBOPUFFER_REGION=gcp-us-central1`
- `TURBOPUFFER_NAMESPACE=jellyfish-site-docs-v1`
- Embedding model: `BAAI/bge-small-en-v1.5`
- Retrieval: turbopuffer `multi_query` with ANN over `vector`, boosted BM25 over `title`/`section_path`/`content`, and RRF fusion
- Limits: `--top-k 3 --candidates 30`

Secret handling boundaries maintained:

- The turbopuffer API key was retrieved from Proton Pass into shell memory only.
- The API key value was not printed.
- The API key value was not written to repository files or a project `.env`.
- Live command output was checked before printing to ensure it did not contain the in-memory API key value.
- Recorded output below is sanitized and does not include vectors.

## Commands and procedure

1. Followed the Proton Pass session check rule before `pass-cli` access. An isolated session at `/tmp/pass-agent-turbo-search-live-retrieval` was used. The active accessible vault was `<private Proton Pass vault>`, and the credential item title was `<private turbopuffer credential item>`.

2. Retrieved only the `API Key` field into shell memory without printing it:

```bash
pass-cli info >/dev/null
TURBOPUFFER_API_KEY="$(PROTON_PASS_AGENT_REASON="Live retrieval approved against indexed turbopuffer namespace jellyfish-site-docs-v1" \
  pass-cli item view --vault-name "<private Proton Pass vault>" --item-title "<private turbopuffer credential item>" --field "API Key")"
```

3. Ran live retrieval with the key in shell memory only. Sanitized command shape:

```bash
TURBOPUFFER_REGION=gcp-us-central1 \
TURBOPUFFER_NAMESPACE=jellyfish-site-docs-v1 \
uv run turbo-search retrieve "<query>" --live --json --top-k 3 --candidates 30
```

Non-secret note: the local embedding model emitted a Hugging Face Hub warning about unauthenticated downloads/rate limits and loaded successfully.

## Query 1: DORA metrics

Query:

```text
What are DORA metrics according to Jellyfish?
```

Sanitized retrieval metadata:

```json
{
  "api_calls_occurred": true,
  "candidates": 30,
  "doc_kind": null,
  "dry_run": false,
  "fusion": "server_rrf",
  "namespace": "jellyfish-site-docs-v1",
  "region": "gcp-us-central1",
  "top_k": 3,
  "turbopuffer_api_calls": true
}
```

Top results:

| Rank | Title | URL | Section | Path | Score info |
| --- | --- | --- | --- | --- | --- |
| 1 | DORA Metrics 101 \| Jellyfish Blog | https://jellyfish.co/blog/dora-metrics-101/ | What are DORA metrics? | jellyfish.co_blog_dora-metrics-101_.md | `{"distance": 0.031318814, "fusion": "server_rrf"}` |
| 2 | DORA Metrics 101 \| Jellyfish Blog | https://jellyfish.co/blog/dora-metrics-101/ | Using DORA metrics to improve your DevOps practices > Interested in learning more about Jellyfish? | jellyfish.co_blog_dora-metrics-101_.md | `{"distance": 0.028665029, "fusion": "server_rrf"}` |
| 3 | 8 Top-Rated Tools for Measuring DORA Metrics | https://jellyfish.co/blog/dora-metrics-tools/ | 8 Best DORA Metrics Tools on the Market Right Now | jellyfish.co_blog_dora-metrics-tools_.md | `{"distance": 0.02736727, "fusion": "server_rrf"}` |

Citation/content checks:

- All returned hits contained citation fields: `title`, `url`, `section_path`, `content`, `path`, plus `doc_kind`, `chunk_index`, and `score_info`.
- The output did not include `vector`.
- The top hit directly answered the DORA query and listed Change Lead Time, Deployment Frequency, Change Failure Rate, and Mean Time To Recovery.

## Query 2: developer productivity

Query:

```text
What does Jellyfish say about measuring developer productivity?
```

Sanitized retrieval metadata:

```json
{
  "api_calls_occurred": true,
  "candidates": 30,
  "doc_kind": null,
  "dry_run": false,
  "fusion": "server_rrf",
  "namespace": "jellyfish-site-docs-v1",
  "region": "gcp-us-central1",
  "top_k": 3,
  "turbopuffer_api_calls": true
}
```

Top results:

| Rank | Title | URL | Section | Path | Score info |
| --- | --- | --- | --- | --- | --- |
| 1 | The Modern Approach to Measuring Developer Productivity | https://jellyfish.co/library/developer-productivity/ | What is Developer Productivity? | jellyfish.co_library_developer-productivity_.md | `{"distance": 0.030092072, "fusion": "server_rrf"}` |
| 2 | The Modern Approach to Measuring Developer Productivity | https://jellyfish.co/library/developer-productivity/ | Measure and Optimize Developer Productivity with Jellyfish | jellyfish.co_library_developer-productivity_.md | `{"distance": 0.029040404, "fusion": "server_rrf"}` |
| 3 | The Modern Approach to Measuring Developer Productivity | https://jellyfish.co/library/developer-productivity/ | Measure and Optimize Developer Productivity with Jellyfish | jellyfish.co_library_developer-productivity_.md | `{"distance": 0.027893737, "fusion": "server_rrf"}` |

Citation/content checks:

- All returned hits contained citation fields: `title`, `url`, `section_path`, `content`, `path`, plus `doc_kind`, `chunk_index`, and `score_info`.
- The output did not include `vector`.
- The top hit was plausibly relevant and states Jellyfish's systems/outcomes framing for developer productivity rather than measuring lines of code, hours, or closed tickets.

## Validation result

Live retrieval met the ticket acceptance criteria:

- At least one live retrieval query succeeded against the indexed namespace; two queries succeeded.
- The retriever returned structured chunks with citation fields and score information.
- No vectors were returned in the JSON output.
- RRF fusion was reported as `server_rrf`.
- Top results were plausibly relevant for the smoke queries.
- No code changes were required during live validation.

## Residual risks

- This is point-in-time smoke validation only; it does not measure retrieval quality across a benchmark set.
- The local embedding model still used unauthenticated Hugging Face Hub access, which may be rate-limited in future runs unless configured separately.
