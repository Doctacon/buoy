# Jellyfish turbopuffer namespace reference

## Purpose

Answer Jellyfish questions using the existing live turbopuffer-backed hybrid RAG prototype.

## Live namespace

- Region: `gcp-us-central1`
- Namespace: `jellyfish-site-docs-v1`
- Indexed rows/chunks: `12,721`
- Embedding model: `BAAI/bge-small-en-v1.5`
- Vector type: `[384]f16`
- Source corpus: `jellyfish-site-docs/`

## Credential retrieval

Do not persist or print the API key. Retrieve it into shell memory only when live retrieval/write has been approved.

Do not record private Proton Pass vault names, item titles, share IDs, or field values in skills, Loom records, docs, code, or shell history. Use the user's private credential procedure from the active conversation/session, or ask the user to provide the lookup details again if needed.

Set the key only in the active shell environment:

```bash
export TURBOPUFFER_REGION=gcp-us-central1
export TURBOPUFFER_NAMESPACE=jellyfish-site-docs-v1
export TURBOPUFFER_API_KEY="<retrieved into shell memory only>"
```

## Retrieval

Use live retrieval for Jellyfish questions when the user is asking about Jellyfish and credentials are available:

```bash
uv run turbo-search retrieve \
  "<question>" \
  --live \
  --top-k 5 \
  --candidates 100 \
  --json
```

Default dry-run retrieval plan, no credentials/API calls:

```bash
uv run turbo-search retrieve \
  "<question>" \
  --dry-run \
  --json
```

## Answering requirements

- Answer from retrieved context, not memory alone.
- Cite each substantive claim with retrieved page title/URL.
- If retrieval does not support the answer, say what is missing rather than guessing.
- Public Jellyfish docs may be product/marketing-level and may not disclose exact internal implementation details.

## Write/eval guardrails

Do not run these unless the user explicitly asks in the current conversation:

- `uv run turbo-search evals --live ...`
- namespace deletion/replacement/cutover
- reindexing or replacing the existing Jellyfish namespace

## Cost notes

Observed billing signal suggested the invoice was likely the prorated Launch-plan minimum rather than metered usage. Still avoid unnecessary writes, live evals, and broad query experiments.
