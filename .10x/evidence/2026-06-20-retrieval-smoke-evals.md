Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-retrieval-smoke-evals.md, .loom/evidence/2026-06-20-jellyfish-live-indexing.md, .loom/evidence/2026-06-20-jellyfish-live-retrieval.md

# Jellyfish retrieval smoke/eval validation

## Scope validated

Added and ran a lightweight retrieval smoke/eval harness against the indexed Jellyfish docs namespace with non-secret runtime configuration:

- `TURBOPUFFER_REGION=gcp-us-central1`
- `TURBOPUFFER_NAMESPACE=jellyfish-site-docs-v1`
- Embedding model: `BAAI/bge-small-en-v1.5`
- Retrieval: existing hybrid retriever using turbopuffer `multi_query`, ANN over `vector`, boosted BM25 over `title`/`section_path`/`content`, and RRF fusion
- Eval limits: `--top-k 5 --candidates 30`
- Dataset: `src/turbo_search/data/retrieval_smoke_evals.json`, 5 hand-authored smoke questions

Secret handling boundaries maintained:

- The turbopuffer API key was retrieved from Proton Pass into shell memory only.
- The API key value was not printed.
- The API key value was not written to repository files or a project `.env`.
- Live eval output was captured to a temporary file outside the repo, checked for the in-memory key value, and only then printed.
- Recorded output below is sanitized and includes only non-secret titles, URLs, sections, and scoring metadata.

## Commands and procedure

1. Ran no-credential tests and syntax checks:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m compileall src tests
```

Result: passed, 16 tests.

2. Ran the no-credential eval listing command:

```bash
PYTHONPATH=src uv run --no-sync python -m turbo_search evals --dry-run --top-k 5 --candidates 30 --json
```

Result: listed 5 eval cases with expected URL/topic hints, `credentials_required=false`, `turbopuffer_api_calls=false`, and no live API calls.

3. Followed the Proton Pass session check rule before `pass-cli` access. An isolated session at `/tmp/pass-agent-retrieval-smoke-evals` was used. The accessible vault was `<private Proton Pass vault>`, and the credential item title was `<private turbopuffer credential item>`.

4. Retrieved only the `API Key` field into shell memory without printing it. Sanitized command shape:

```bash
pass-cli info >/dev/null
TURBOPUFFER_API_KEY="$(PROTON_PASS_AGENT_REASON="Live retrieval smoke evals against indexed Jellyfish docs namespace jellyfish-site-docs-v1" \
  pass-cli item view --vault-name "<private Proton Pass vault>" --item-title "<private turbopuffer credential item>" --field "API Key")"
```

5. Ran live evals with the key in shell memory only, captured output to a temporary file, checked the output did not contain the in-memory key, then printed sanitized output:

```bash
TURBOPUFFER_API_KEY="$TURBOPUFFER_API_KEY" \
TURBOPUFFER_REGION=gcp-us-central1 \
TURBOPUFFER_NAMESPACE=jellyfish-site-docs-v1 \
uv run turbo-search evals --live --top-k 5 --candidates 30 --json
```

Non-secret note: the local embedding model emitted a Hugging Face Hub warning about unauthenticated downloads/rate limits and loaded successfully.

## Sanitized live eval summary

```json
{
  "api_calls_occurred": true,
  "candidates": 30,
  "command": "evals",
  "credentials_required": true,
  "dry_run": false,
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "failed": 0,
  "namespace": "jellyfish-site-docs-v1",
  "not_run": 0,
  "pass_rate": 1.0,
  "passed": 5,
  "region": "gcp-us-central1",
  "top_k": 5,
  "total": 5,
  "turbopuffer_api_calls": true
}
```

## Per-query results

| Eval | Query | Status | Match | Top titles/URLs |
| --- | --- | --- | --- | --- |
| developer-productivity | What does Jellyfish say about measuring developer productivity? | passed | Expected URL at rank 1: `https://jellyfish.co/library/developer-productivity/` | 1. The Modern Approach to Measuring Developer Productivity — `https://jellyfish.co/library/developer-productivity/`<br>2. The Modern Approach to Measuring Developer Productivity — `https://jellyfish.co/library/developer-productivity/`<br>3. The Modern Approach to Measuring Developer Productivity — `https://jellyfish.co/library/developer-productivity/`<br>4. 21 Developer Productivity Metrics That Actually Matter — `https://jellyfish.co/library/developer-productivity/metrics/`<br>5. SPACE Framework Metrics for Developer Productivity — `https://jellyfish.co/library/space-framework/` |
| dora-metrics | What are DORA metrics according to Jellyfish? | passed | Expected URL at rank 1: `https://jellyfish.co/blog/dora-metrics-101/` | 1. DORA Metrics 101 \| Jellyfish Blog — `https://jellyfish.co/blog/dora-metrics-101/`<br>2. DORA Metrics 101 \| Jellyfish Blog — `https://jellyfish.co/blog/dora-metrics-101/`<br>3. 8 Top-Rated Tools for Measuring DORA Metrics — `https://jellyfish.co/blog/dora-metrics-tools/`<br>4. DevOps Metrics \| Jellyfish — `https://jellyfish.co/platform/devops-metrics/`<br>5. DORA Metrics 101 \| Jellyfish Blog — `https://jellyfish.co/blog/dora-metrics-101/` |
| devfinops | What does Jellyfish DevFinOps do? | passed | Expected topic at rank 1: `devfinops`; expected URL also appeared at rank 2 | 1. Announcing Jellyfish DevFinOps \| Jellyfish Blog — `https://jellyfish.co/blog/announcing-jellyfish-devfinops/`<br>2. DevFinOps \| Jellyfish — `https://jellyfish.co/platform/devfinops/`<br>3. DevFinOps Archives - Jellyfish — `https://jellyfish.co/blog/value-category/devfinops/`<br>4. What is DevFinOps? How Does It Help Track R&D Costs? — `https://jellyfish.co/blog/what-is-devfinops/`<br>5. What is DevFinOps? How Does It Help Track R&D Costs? — `https://jellyfish.co/blog/what-is-devfinops/` |
| claude-code-cursor-integrations | What integrations does Jellyfish mention for Claude Code or Cursor? | passed | Expected topic at rank 1: `claude code adoption`; expected Claude Code integration URL also appeared at rank 3 | 1. Platform Integrations \| Jellyfish — `https://jellyfish.co/integrations/`<br>2. Claude Code Dashboard \| Jellyfish — `https://jellyfish.co/platform/claude-code-dashboard/`<br>3. Claude Code Integration with Jellyfish — `https://jellyfish.co/integration/claude-code/`<br>4. Claude Code Integration with Jellyfish — `https://jellyfish.co/integration/claude-code/`<br>5. Claude Code Integration with Jellyfish — `https://jellyfish.co/integration/claude-code/` |
| ai-coding-tool-adoption | What does Jellyfish say about AI coding tool adoption? | passed | Expected URL at rank 1: `https://jellyfish.co/blog/ai-coding-tool-adoption-best-practices/` | 1. Guiding AI Coding Tool Adoption with Intention: Best Practices for Engineering Teams - Jellyfish — `https://jellyfish.co/blog/ai-coding-tool-adoption-best-practices/`<br>2. 2025 AI Metrics in Review: What 12 Months of Data Tell Us About Adoption and Impact - Jellyfish — `https://jellyfish.co/blog/2025-ai-metrics-in-review/`<br>3. Guiding AI Coding Tool Adoption with Intention: Best Practices for Engineering Teams - Jellyfish — `https://jellyfish.co/blog/ai-coding-tool-adoption-best-practices/`<br>4. Guiding AI Coding Tool Adoption with Intention: Best Practices for Engineering Teams - Jellyfish — `https://jellyfish.co/blog/ai-coding-tool-adoption-best-practices/`<br>5. From Hype to Impact: A Conversation on AI Tool Adoption, Agent Usage, and Engineering Productivity - Jellyfish — `https://jellyfish.co/blog/ai-tool-adoption-agent-usage-engineering-productivity/` |

## Validation result

Live retrieval smoke/evals met the ticket acceptance criteria:

- 5/5 live smoke questions ran against `jellyfish-site-docs-v1` in `gcp-us-central1`.
- Pass rate: 100%.
- Every eval returned relevant Jellyfish titles/URLs in top-k.
- Output reported top titles/URLs and per-query pass/fail scoring.
- The harness supports no-credential dry-run listing and live execution through `turbo-search evals`.
- Unit tests cover eval dataset loading and URL/topic scoring without live credentials.

## Limits and residual risks

- This is a small smoke set, not a comprehensive relevance benchmark.
- Topic matching is substring-based over retrieved title, URL, section, content, and path; it is intentionally simple and may not catch nuanced relevance failures.
- The Claude Code/Cursor eval matched topic text at rank 1 and expected integration URL at rank 3; acceptable for smoke top-k, but a deeper benchmark could add separate Cursor-specific evals.
- The local embedding model used unauthenticated Hugging Face Hub access, which may be rate-limited in future runs unless configured separately.
