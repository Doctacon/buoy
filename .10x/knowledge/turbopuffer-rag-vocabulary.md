Status: active
Created: 2026-06-20
Updated: 2026-06-20

# Turbopuffer RAG vocabulary

## Namespace

A turbopuffer namespace is an isolated document space. For this project, use one namespace for one indexed corpus/version unless there is a natural need to query multiple namespaces together.

## Source page

A source page is one Markdown file under `jellyfish-site-docs/`. It corresponds to one exported Jellyfish URL and usually has YAML frontmatter with `url` and `title`.

## Chunk

A chunk is a retrieval unit derived from a source page. The index should store one turbopuffer row per chunk, not one row per full Markdown file. Chunks should preserve enough title/heading context to stand alone.

## Hybrid search

Hybrid search combines dense vector search for semantic matches with full-text/BM25 search for exact term matches. In turbopuffer this is done with `multi_query`, commonly one ANN subquery plus one BM25 subquery.

## ANN

Approximate nearest neighbor vector search. Use for the vector side of retrieval unless exact kNN is specifically needed over a small filtered subset.

## BM25

A full-text ranking method that scores lexical matches using term frequency and document length normalization. In turbopuffer it must be enabled per string/array-string attribute via schema `full_text_search`.

## RRF

Reciprocal rank fusion. A rank-based method for combining result lists from multiple retrieval methods. Turbopuffer query docs support `rerank_by=("RRF",)` on multi-query responses; client-side RRF can be kept as a fallback.

## Reranker

A second-stage model that scores `(query, chunk)` pairs after first-stage retrieval. Under this project's open-source-first rule, prefer local open-source rerankers such as BGE/Qwen before proprietary hosted reranking APIs.

## Citation

A citation is the source metadata attached to retrieved chunks, especially `title`, `url`, `section_path`, and optionally local `path`. Any answer grounded in the index should cite the retrieved source URLs/titles.
