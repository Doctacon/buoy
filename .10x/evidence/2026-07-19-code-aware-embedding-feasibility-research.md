Status: recorded
Created: 2026-07-19
Updated: 2026-07-20
Relates-To: .10x/tickets/done/2026-07-19-research-code-aware-embedding-candidate.md, .10x/research/2026-07-19-code-aware-embedding-candidate.md, .10x/tickets/2026-07-19-evaluate-code-aware-embedding-pilot.md

# Code-Aware Embedding Feasibility Research Evidence

## What was observed

- Buoy source at `7c19b7c130549ada8221efdb4e5e2a2ad16eb3b8` fixes content vectors, namespace-card content dimensions, remote catalog compatibility, and catalog routing vectors at 384 dimensions. The current content/default plan model remains `BAAI/bge-small-en-v1.5`.
- The contemporaneous Hugging Face discovery query returned 100 results. The exact recorded predicate selected 14; all 14 identities, revisions, matched tags, observed use counts, credibility boundaries, C4 constraints, and dispositions now appear in `.10x/research/.storage/2026-07-19-code-aware-embedding-source-snapshot.json` and the research roster.
- Primary dynamic-dimension decision candidate `nomic-ai/nomic-embed-code@11114029805cee545ef111d5144b623787462a52` is Apache-2.0 and standard SentenceTransformer/no remote code, but emits 3,584-dimensional last-token normalized output, requires a query-only prefix, and has a 32,768-token maximum.
- Its immutable tree lists 28,282,512,976 bytes of float32 weights and 28,298,426,837 total listed bytes. Current Buoy constructs `SentenceTransformer(model_name)` before `.half()`, so current initialization requires more than 26.34 GiB for float32 weights plus runtime overhead. A 24 GiB accelerator estimate applies only after separate direct-half/loading plumbing exists; no such plumbing was implemented or authorized.
- Fallback dynamic-dimension decision candidate `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af` has an authoritative Apache-2.0 card, standard Transformer/Pooling SentenceTransformer modules, no `auto_map` or remote code, no query/document prefix, a single 768-dimensional CLS vector, and a 1,024-token maximum. It has no Normalize module, while Buoy's shared encode call requests normalized embeddings.
- Crow-Plus's immutable tree lists a 606,681,112-byte weight file and 611,525,163 total bytes. It is materially smaller than Nomic but still fails C4's exact 384-dimensional condition.
- The other 12 roster results were explicitly dispositioned. Credible 768-dimensional Shuu variants were not retained because C2 permits at most one fallback and Crow-Plus has the stronger externally legible evidence/use basis. Non-retained artifacts otherwise fail for wrong dimension plus one or more of non-OSI/unclear license, remote code, third-party repack provenance, or incompatible multi-vector/runtime shape.
- Additional candidate-driven screening rejected BGE Code v1, CodeRankEmbed, and Jina Code for wrong dimensions plus remote-code requirements.
- C4 remains blocked pending a separate decision on whether to shape dynamic content-vector dimensions.

## Procedure

1. Ran the required Git branch/worktree checks; read C2, C4, the parent, governing research/evidence, current embedding source, lockfile, and the independent review finding.
2. Reproduced the original exact discovery predicate and full 14-result roster from the contemporaneous query artifact, rather than substituting the mutable endpoint's later result.
3. Used public, read-only Hugging Face metadata/model-card/config/module/tree HTTP endpoints at immutable revisions. No weight or inference file was fetched.
4. Verified Crow-Plus's immutable model card, `config.json`, `config_sentence_transformers.json`, `sentence_bert_config.json`, `1_Pooling/config.json`, `modules.json`, and recursive tree.
5. Summed immutable tree metadata sizes and checked every roster row against authority, OSI license, installed SentenceTransformer path, remote code, vector shape, output dimension, and the exact C4 384-dimensional condition.
6. Rechecked `src/buoy_search/chunker.py`: the constructor runs before `.half()`, and `encode` requests normalized embeddings.
7. Stored normalized retained-model metadata, the full roster, and supplemental screen at `.10x/research/.storage/2026-07-19-code-aware-embedding-source-snapshot.json`; updated the research and ticket graph without source/test/dependency changes.

## What this supports or challenges

This supports the C2 conclusion that no candidate can enter C4 under the current 384-dimensional contract. It repairs the prior unsupported no-fallback claim: Crow-Plus is now retained as the smaller fallback for a future dynamic-dimension decision. This supports a stop, not a migration; dynamic dimensions, schema/card/routing changes, model downloads, resource verification, and namespaces remain unapproved.

## Safety observation

No model or dependency was downloaded/installed, no weight was loaded, no inference ran, no credentials were read, no Buoy live retrieval/service call occurred, and no namespace/catalog/source/test/lockfile mutation was performed. HTTP access was limited to public research metadata, model cards/configuration text, and authoritative package source.

## Limits

- RAM/device figures are analytical estimates from parameter/weight bytes and current precision behavior; they are not measured peaks.
- Metadata compatibility with locked packages does not prove runtime compatibility; C2 forbids the model load needed to test it.
- Model-card quality claims were not reproduced.
- The bounded search supports absence among the fully dispositioned roster and supplemental authoritative candidates, not mathematical proof that no obscure artifact exists.
