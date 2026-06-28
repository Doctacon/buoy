Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-agent-answering-workflow.md, .loom/specs/turbopuffer-jellyfish-rag.md, .loom/evidence/2026-06-20-jellyfish-live-retrieval.md

# Agent answering workflow validation

## Scope validated

Documented the future-agent procedure for answering user questions using Jellyfish docs context retrieved from turbopuffer.

Safety boundaries maintained:

- No Proton Pass access.
- No secret access.
- No live turbopuffer retrieval.
- Only no-credential CLI help and retrieval dry-run commands were executed.
- No proprietary service was added.

## Changed files

- `docs/agent-answering-workflow.md`
- `README.md`
- `.loom/tickets/2026-06-20-agent-answering-workflow.md`
- `.loom/evidence/2026-06-20-agent-answering-workflow-validation.md`

## Tests added or updated

- None. Documentation-only change; no code was changed.

## Validation commands run

### CLI help

```bash
PYTHONPATH=src uv run --no-sync python -m turbo_search --help
```

Result: passed.

```text
usage: turbo-search [-h] [--version] {index,retrieve} ...

Local Jellyfish docs RAG utilities. Indexing is dry-run by default.

positional arguments:
  {index,retrieve}
    index           parse and chunk Markdown docs; write only when --write is
                    passed
    retrieve        retrieve relevant chunks; dry-run plan by default unless
                    --live is passed

options:
  -h, --help        show this help message and exit
  --version         show program's version number and exit
```

### Retrieval dry-run

```bash
PYTHONPATH=src uv run --no-sync python -m turbo_search retrieve "What are DORA metrics according to Jellyfish?" --dry-run --top-k 3 --candidates 30 --json
```

Result: passed; no credentials and no API calls.

```json
{
  "api_calls_occurred": false,
  "candidates": 30,
  "command": "retrieve",
  "credentials_required": false,
  "doc_kind": null,
  "dry_run": true,
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "live_execution": "pass --live to embed the query and call turbopuffer",
  "namespace": "jellyfish-site-docs-v1",
  "plan": true,
  "query": "What are DORA metrics according to Jellyfish?",
  "region": "gcp-us-central1",
  "retrieval": {
    "fallback": "client-side reciprocal-rank fusion if server RRF is unsupported or separate lists are returned",
    "request": "turbopuffer multi_query",
    "rerank_by": [
      "RRF"
    ],
    "subqueries": [
      {
        "include_attributes": [
          "title",
          "url",
          "section_path",
          "content",
          "path",
          "doc_kind",
          "chunk_index"
        ],
        "limit": 30,
        "name": "ann",
        "rank_by": [
          "vector",
          "ANN",
          "<query embedding>"
        ]
      },
      {
        "include_attributes": [
          "title",
          "url",
          "section_path",
          "content",
          "path",
          "doc_kind",
          "chunk_index"
        ],
        "limit": 30,
        "name": "bm25",
        "rank_by": [
          "Sum",
          [
            [
              "Product",
              2.0,
              [
                "title",
                "BM25",
                "What are DORA metrics according to Jellyfish?"
              ]
            ],
            [
              "Product",
              1.5,
              [
                "section_path",
                "BM25",
                "What are DORA metrics according to Jellyfish?"
              ]
            ],
            [
              "content",
              "BM25",
              "What are DORA metrics according to Jellyfish?"
            ]
          ]
        ]
      }
    ]
  },
  "top_k": 3,
  "turbopuffer_api_calls": false
}
```

### No staged files

```bash
git diff --cached --name-only
```

Result: passed; command produced no output.

## Acceptance checks

- `docs/agent-answering-workflow.md` tells future agents to retrieve context before answering and gives safe dry-run plus approved live retrieval commands.
- The doc lists required environment variables and gives a safe Proton Pass command shape with placeholders and no secret values.
- The doc defines expected live output fields, including `hits[]`, citation metadata, content, score info, and the no-vector default.
- The doc makes citation behavior explicit: cite material claims with source `title` and `url`.
- The doc distinguishes retrieval failure, weak retrieval, and answerable questions.
- The example question uses the existing live retrieval evidence for DORA metrics and includes an answer sketch with a source title/URL citation.

## Residual risks

- This validation did not run live turbopuffer retrieval by design; it relies on existing live retrieval evidence for the example.
- Future agents still need approved runtime credentials before using `--live`.
- The workflow is documentation-only; no prompt-bundle helper command was added because the existing `retrieve --json` output already provides the required context fields.
