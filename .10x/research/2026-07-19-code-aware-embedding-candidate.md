Status: done
Created: 2026-07-19
Updated: 2026-07-20

# Code-Aware Embedding Candidate

## Question

Is there a credible open-source, locally runnable, native 384-dimensional code-aware embedding model that can use Buoy's installed `sentence-transformers` path without `trust_remote_code`, and therefore unblock C4 without a vector-dimension migration?

## Conclusion

No. The complete 14-result discovery roster and three additional authoritative candidates did not yield a credible native 384-dimensional candidate satisfying the local/open-source/SentenceTransformer/no-remote-code boundary. C4 MUST remain blocked under its existing stop condition. A separate user decision is required before shaping dynamic content-vector dimensions; this research does not authorize or design that migration.

Two models are retained only to inform that later decision, not as C4-compatible or user-approved models:

1. Primary: `nomic-ai/nomic-embed-code@11114029805cee545ef111d5144b623787462a52` — Apache-2.0, standard SentenceTransformer/no remote code, 3,584 dimensions, query-only prefix, last-token pooling, normalized, 32,768-token maximum, and 28,298,426,837 listed bytes.
2. Fallback: `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af` — Apache-2.0, standard SentenceTransformer/no remote code, single 768-dimensional CLS vector, no prefix, 1,024-token maximum, and 611,525,163 listed bytes.

Both fail C4's exact 384-dimensional requirement.

## Sources and methods

- Inspected the immutable Buoy source snapshot `7c19b7c130549ada8221efdb4e5e2a2ad16eb3b8` and lockfile. No source, tests, dependencies, lockfiles, models, credentials, namespaces, catalogs, or live services were mutated or called.
- Queried the public Hugging Face model metadata endpoint for `code` models filtered to Sentence Transformers. The contemporaneous query returned 100 results; the stated exact tag predicate selected 14. Every selected identity, immutable revision, matched tag, observed download/like count, compatibility fact, and disposition is reproduced in `.10x/research/.storage/2026-07-19-code-aware-embedding-source-snapshot.json`.
- Inspected only model cards and small configuration/module/tree metadata at immutable revisions. No weight or inference asset was fetched. The mutable discovery endpoint now returning a different roster does not alter the stored contemporaneous screen.
- Apache-2.0 is on the [Open Source Initiative approved-license page](https://opensource.org/license/apache-2-0). Both retained immutable model cards declare `license: apache-2.0`.

Authoritative Nomic sources, all pinned to `11114029805cee545ef111d5144b623787462a52`:

- [model card and usage](https://huggingface.co/nomic-ai/nomic-embed-code/blob/11114029805cee545ef111d5144b623787462a52/README.md)
- [architecture/dimension config](https://huggingface.co/nomic-ai/nomic-embed-code/blob/11114029805cee545ef111d5144b623787462a52/config.json)
- [query prompt config](https://huggingface.co/nomic-ai/nomic-embed-code/blob/11114029805cee545ef111d5144b623787462a52/config_sentence_transformers.json)
- [maximum sequence length](https://huggingface.co/nomic-ai/nomic-embed-code/blob/11114029805cee545ef111d5144b623787462a52/sentence_bert_config.json)
- [pooling config](https://huggingface.co/nomic-ai/nomic-embed-code/blob/11114029805cee545ef111d5144b623787462a52/1_Pooling/config.json)
- [standard SentenceTransformer modules, including Normalize](https://huggingface.co/nomic-ai/nomic-embed-code/blob/11114029805cee545ef111d5144b623787462a52/modules.json)
- [artifact tree and byte sizes](https://huggingface.co/api/models/nomic-ai/nomic-embed-code/tree/11114029805cee545ef111d5144b623787462a52?recursive=true&expand=false)

Authoritative Crow-Plus sources, all pinned to `96ff525a7aa3bf8bfa90d77337c2b24bd45229af`:

- [model card, Apache-2.0 declaration, usage, and retrieval evaluation](https://huggingface.co/Shuu12121/CodeSearch-ModernBERT-Crow-Plus/blob/96ff525a7aa3bf8bfa90d77337c2b24bd45229af/README.md)
- [standard ModernBERT architecture and 768 hidden size](https://huggingface.co/Shuu12121/CodeSearch-ModernBERT-Crow-Plus/blob/96ff525a7aa3bf8bfa90d77337c2b24bd45229af/config.json)
- [empty prompt contract and cosine similarity](https://huggingface.co/Shuu12121/CodeSearch-ModernBERT-Crow-Plus/blob/96ff525a7aa3bf8bfa90d77337c2b24bd45229af/config_sentence_transformers.json)
- [1,024-token maximum](https://huggingface.co/Shuu12121/CodeSearch-ModernBERT-Crow-Plus/blob/96ff525a7aa3bf8bfa90d77337c2b24bd45229af/sentence_bert_config.json)
- [single-vector CLS pooling](https://huggingface.co/Shuu12121/CodeSearch-ModernBERT-Crow-Plus/blob/96ff525a7aa3bf8bfa90d77337c2b24bd45229af/1_Pooling/config.json)
- [standard Transformer and Pooling modules](https://huggingface.co/Shuu12121/CodeSearch-ModernBERT-Crow-Plus/blob/96ff525a7aa3bf8bfa90d77337c2b24bd45229af/modules.json)
- [artifact tree and exact byte sizes](https://huggingface.co/api/models/Shuu12121/CodeSearch-ModernBERT-Crow-Plus/tree/96ff525a7aa3bf8bfa90d77337c2b24bd45229af?recursive=true&expand=false)

## Compatibility and cost table

| Role | Model contract | License provenance | ST / remote-code boundary | Prefix, pooling, normalization | Dimension / max input | Download, RAM, device estimate | C4 compatible? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Primary, dynamic-dimension decision only | `nomic-ai/nomic-embed-code@11114029805cee545ef111d5144b623787462a52`; standard `Qwen2Model`; public and ungated | Immutable card declares Apache-2.0; OSI approves Apache-2.0 | Standard Transformer/Pooling/Normalize modules; no `auto_map`, custom-code tag, or `trust_remote_code` usage | Query: `Represent this query for searching relevant code: `; documents: no prefix. Last-token pooling with prompt included, followed by Normalize. Current Buoy does not apply the query prompt. | 3,584 / 32,768 | 28,282,512,976 weight bytes; 28,298,426,837 listed bytes (28.30 GB / 26.35 GiB). **Current Buoy constructs float32 before `.half()`, so initialization requires more than 26.34 GiB plus runtime overhead. A 24 GiB accelerator estimate applies only after alternate direct-half/loading plumbing exists.** Estimate 32 GiB available RAM and a 48 GiB host for current initialization; no peak was measured. | **No:** 3,584 is not 384. |
| Fallback, dynamic-dimension decision only | `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af`; standard `ModernBertModel`; public and ungated | Immutable author card declares Apache-2.0; OSI approves Apache-2.0 | Standard Transformer/Pooling modules; no `auto_map`, custom code, or remote-code usage | No query or document prefix. Single CLS-token vector. Model has no Normalize module; Buoy's shared `encode(..., normalize_embeddings=True)` normalizes output. | 768 / 1,024 | 606,681,112 weight bytes; 611,525,163 listed bytes (611.53 MB / 583.20 MiB). Float32 initialization needs more than 0.565 GiB plus overhead; half steady weights are about 0.283 GiB. Plan at least 2 GiB RAM and, if used, 2 GiB device memory; peaks are unverified. | **No:** 768 is not 384. |

The memory figures are analytical planning estimates, not measured benchmarks. A future checkpoint needs exact approved resource bounds and a permitted local load before claiming runtime compatibility or measured peaks.

## Dependency and offline/telemetry contract

Buoy locks `sentence-transformers==5.6.0`, `transformers==5.12.1`, `torch==2.12.1`, and `huggingface-hub==1.20.1`. Both retained repositories use architectures and SentenceTransformer module types built into the locked packages, so metadata inspection found no remote-code requirement. Runtime compatibility remains unverified because C2 forbids loading weights.

For an eventually approved pinned download, the constructor MUST receive the immutable revision. After explicit caching, set `HF_HUB_OFFLINE=1` so Hub HTTP requests fail rather than silently checking/downloading, and set `HF_HUB_DISABLE_TELEMETRY=1` (or `DO_NOT_TRACK=1`) to disable telemetry. The locked Hub implementation defines these controls and treats `TRANSFORMERS_OFFLINE` as an offline alias in [`constants.py`](https://github.com/huggingface/huggingface_hub/blob/5efdca0b066740c911e59feba2f14e145ff3dbfb/src/huggingface_hub/constants.py#L202-L243). `HF_HUB_DISABLE_UPDATE_CHECK=1` additionally suppresses update checks. Both models are public and ungated; no credentials are required.

Current content embedding does not meet the pin/offline contract: `SentenceTransformerEmbedder` calls `SentenceTransformer(model_name)` without `revision` or `local_files_only`. Nomic additionally needs experiment-only query-role prefix plumbing; Crow-Plus needs no prefix. C2 does not implement any plumbing.

## Current Buoy compatibility boundary

At source snapshot `7c19b7c130549ada8221efdb4e5e2a2ad16eb3b8`:

- `src/buoy_search/chunker.py` sets `VECTOR_DIMENSIONS = 384`, content schema `[384]f16`, and constructs a model before applying `.half()`.
- `src/buoy_search/apply.py` previews content/catalog `vector_dimensions` as 384.
- `src/buoy_search/catalog.py` pins automatic routing itself to `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, normalized 384-dimensional vectors, and validates every card's `vector_dimensions` as exactly 384.
- `src/buoy_search/remote_catalog.py` fixes remote routing vectors and compatibility contracts at 384.
- `src/buoy_search/config.py` and `src/buoy_search/plan_artifacts.py` retain `BAAI/bge-small-en-v1.5` as the content/default plan model. No default change is authorized.
- Automatically selected namespaces must share one content embedding model and precision. A 768- or 3,584-dimensional content namespace cannot be represented honestly by the current 384-only card/compatibility contract, even though independent catalog-routing vectors could remain 384.

Therefore neither retained model can enter C4. Dynamic content schema/card/compatibility work is explicitly outside C2 and C4.

## Complete discovery roster and dispositions

The following is the complete 14-result roster selected by the contemporaneous exact tag predicate. Links are immutable revision trees. “Credible” means the artifact has enough authoritative/open provenance to inform a later dynamic-dimension decision; it does not mean C4-compatible or approved.

| # | Candidate | Credibility / exact C4 screen | Disposition |
| --- | --- | --- | --- |
| 1 | [`lightonai/LateOn-Code@734b659`](https://huggingface.co/lightonai/LateOn-Code/tree/734b659a57935ef50562d79581c3ff1f8d825c93) | Credible Apache-2.0 upstream, but 768-dimensional ColBERT/PyLate multi-vector, not installed single-vector ST path | Reject: wrong dimension and retrieval shape/path |
| 2 | [`Salesforce/SFR-Embedding-Code-2B_R@c73d863`](https://huggingface.co/Salesforce/SFR-Embedding-Code-2B_R/tree/c73d8631a005876ed5abde34db514b1fb6566973) | Authoritative, but 2,304 dimensions, custom `auto_map`, CC-BY-NC-4.0 | Reject: wrong dimension, remote code, non-OSI license |
| 3 | [`aigentic/LateOn-Code-ONNX@96f9ed1`](https://huggingface.co/aigentic/LateOn-Code-ONNX/tree/96f9ed1c2487900e169ec9e5d8ef24d826532e0d) | Third-party ONNX/Transformers.js quantization of 768-dimensional multi-vector LateOn-Code | Reject: non-authoritative repack, wrong dimension/shape/path |
| 4 | [`flax-sentence-embeddings/st-codesearch-distilroberta-base@65b0f39`](https://huggingface.co/flax-sentence-embeddings/st-codesearch-distilroberta-base/tree/65b0f39bfa41c59993f62b57447c942e371b7135) | Standard ST/Roberta, 768 dimensions; no immutable license field/file; card says preliminary and untested | Reject: wrong dimension and unclear license/credibility |
| 5 | [`codecompletedeployment/st-codesearch-distilroberta-base@f87e31d`](https://huggingface.co/codecompletedeployment/st-codesearch-distilroberta-base/tree/f87e31d76deeeb926a42c36fd22658ef0e97472b) | Third-party duplicate of #4, 768 dimensions, no immutable license provenance | Reject: copy adds no authority; wrong dimension and unclear license |
| 6 | [`Salesforce/SFR-Embedding-Code-400M_R@cb950dc`](https://huggingface.co/Salesforce/SFR-Embedding-Code-400M_R/tree/cb950dc80d677c6fdc00f56c8ddd20ca2642c59e) | Authoritative, but 1,024 dimensions, custom `auto_map`, CC-BY-NC-4.0 | Reject: wrong dimension, remote code, non-OSI license |
| 7 | [`nomic-ai/nomic-embed-code@1111402`](https://huggingface.co/nomic-ai/nomic-embed-code/tree/11114029805cee545ef111d5144b623787462a52) | Credible Apache-2.0 upstream, standard ST/no remote code, 3,584-dimensional single vector | Retain as primary dynamic-dimension decision candidate; C4 stopped |
| 8 | [`Shuu12121/CodeSearch-ModernBERT-Owl@282490c`](https://huggingface.co/Shuu12121/CodeSearch-ModernBERT-Owl/tree/282490cfa328e7c5f4dfc1001dcb32ffe7e30557) | Credible Apache-2.0 upstream, standard ST/no remote code, 768-dimensional single vector | Do not retain under one-fallback cap; Crow-Plus has stronger published evidence/use; C4 stopped |
| 9 | [`joe32140/codesage-small@281ec26`](https://huggingface.co/joe32140/codesage-small/tree/281ec2628b7fe72e7e6e232b755fdde9b26192ba) | Third-party packaging, 1,024 dimensions, custom CodeSage `auto_map` | Reject: remote code, non-authoritative packaging, wrong dimension |
| 10 | [`Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525`](https://huggingface.co/Shuu12121/CodeSearch-ModernBERT-Crow-Plus/tree/96ff525a7aa3bf8bfa90d77337c2b24bd45229af) | Credible Apache-2.0 upstream, standard ST/no remote code, 768-dimensional single CLS vector | Retain as fallback dynamic-dimension decision candidate; C4 stopped |
| 11 | [`Shuu12121/CodeSearch-ModernBERT-Crow-Plus-1.0@1cefdd2`](https://huggingface.co/Shuu12121/CodeSearch-ModernBERT-Crow-Plus-1.0/tree/1cefdd29a5609070c69be83c3db22d29484dbc98) | Credible Apache-2.0 upstream, standard ST/no remote code, 768 dimensions; card marks improved evaluation as unofficial/not submitted | Do not retain under one-fallback cap; retained Crow-Plus is the stronger externally legible baseline; C4 stopped |
| 12 | [`Shuu12121/CodeSearch-ModernBERT-Owl-Plus@cb0edfe`](https://huggingface.co/Shuu12121/CodeSearch-ModernBERT-Owl-Plus/tree/cb0edfeed0a7772bee61cd288f18166967e36914) | Credible Apache-2.0 upstream, standard ST/no remote code, 768 dimensions, but less observed use/evidence than retained fallback | Do not retain under one-fallback cap; C4 stopped |
| 13 | [`bartowski/nomic-ai_nomic-embed-code-GGUF@e237621`](https://huggingface.co/bartowski/nomic-ai_nomic-embed-code-GGUF/tree/e237621d1dfbaa357592ed8641a50c3db03d2dc7) | Third-party GGUF conversion of 3,584-dimensional Nomic; not installed ST path | Reject: non-authoritative repack, wrong dimension/path |
| 14 | [`lmstudio-community/nomic-embed-code-GGUF@0a296e8`](https://huggingface.co/lmstudio-community/nomic-embed-code-GGUF/tree/0a296e84ce0f6a3fe4369c04abbb67b5b30edf18) | Third-party GGUF conversion of 3,584-dimensional Nomic; not installed ST path | Reject: non-authoritative repack, wrong dimension/path |

Additional authoritative candidate-driven screening (outside the exact 14-result tag roster) also rejected:

- [`BAAI/bge-code-v1@bd678520`](https://huggingface.co/BAAI/bge-code-v1/tree/bd67852057c5d7ddcc7b8234d9d6c410117ed851): Apache-2.0, 1,536 dimensions; authoritative example requires `trust_remote_code=True`.
- [`nomic-ai/CodeRankEmbed@3c4b608`](https://huggingface.co/nomic-ai/CodeRankEmbed/tree/3c4b60807d71f79b43f3c4363786d9493691f8b1): MIT, 768 dimensions; card and `auto_map` require remote code.
- [`jinaai/jina-embeddings-v2-base-code@516f4ba`](https://huggingface.co/jinaai/jina-embeddings-v2-base-code/tree/516f4baf13dec4ddddda8631e019b5737c8bc250): Apache-2.0, 768 dimensions; card and `auto_map` require remote code.

No third-party repack or quantization was promoted over an authoritative upstream artifact.

## Required decision and stop

C4 remains blocked. The next product/architecture checkpoint is:

> No credible native 384-dimensional code-aware candidate met the open-source/local/SentenceTransformer/no-remote-code boundary. Confirm or reject opening separate shaping for dynamic **content-vector** dimensions, covering the viable 768- and 3,584-dimensional candidates, content namespace schema, card compatibility, automatic routing, migration/isolation, and resource bounds. Until confirmed, C4 performs no model download, install, inference, source change, namespace write, catalog change, or live operation.

## Limits

- This is feasibility research, not a quality benchmark. Model-card benchmark claims were not independently reproduced.
- No model/dependency was downloaded or installed; no model was loaded; no inference, credential read, namespace/catalog operation, or live retrieval/write occurred.
- Runtime compatibility and RAM/device peaks are unverified by design.
- Search cannot prove that no obscure 384-dimensional artifact exists. The conclusion is scoped to the complete contemporaneous roster plus the authoritative candidate-driven screen; mutable-only, unclear-license, custom-code, multi-vector, and low-credibility repacks were dispositioned explicitly.
