Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Relates-To: .10x/tickets/done/2026-07-15-backfill-live-namespace-catalog.md, .10x/specs/production-local-namespace-catalog.md, .10x/specs/superseded/automatic-production-namespace-routing.md

# Live Namespace Catalog Backfill

## What was observed

The documented namespace discovery path returned four namespace IDs in `gcp-us-central1`:

- `site-dagster-io-benchmark-v1`
- `site-dagster-io-v1`
- `site-oscilar-com-v1`
- `site-www-thistle-co-v1`

Inspection of `src/buoy_search/namespaces.py` established that this command constructs a Turbopuffer client and calls only `client.namespaces()`. It does not query namespace rows or expose a mutation path. Inspection of `src/buoy_search/catalog_cli.py` established that `catalog upsert` calls the local atomic `mutate_catalog` path and explicitly does not read Turbopuffer credentials or modify remote data.

The pre-mutation machine-checkable match table is stored at `.10x/evidence/.storage/2026-07-15-live-namespace-catalog-backfill-match.json`. It matched all four live IDs to exact local DuckDB state, found 62 total locally applied namespace IDs, and classified:

- register (2): `site-dagster-io-benchmark-v1`, `site-oscilar-com-v1`;
- exclude for incomplete canonical compatibility provenance (2): `site-dagster-io-v1`, `site-www-thistle-co-v1`;
- unmatched live (0);
- historical local-only (58), enumerated in the stored table.

The two excluded live namespaces have exact local state, source URL, plan/apply IDs, and active row counts, but the canonical checkout retains no authoritative plan or sanitized apply evidence proving embedding precision and the complete schema-v1 retrieval contract. Registering them would have invented compatibility values from namespace IDs/current defaults.

The eligible records were grounded as follows:

| Namespace | Live existence | Applied state | Contract/source authority |
| --- | --- | --- | --- |
| `site-dagster-io-benchmark-v1` | read-only inventory | `.turbo-search/state/dagster-io/site-dagster-io-benchmark-v1/state.duckdb`, 25,322 active rows | `.10x/evidence/.storage/2026-07-13-live-dagster-throughput-benchmark-command-output.json` |
| `site-oscilar-com-v1` | read-only inventory | `.turbo-search/state/oscilar-com/site-oscilar-com-v1/state.duckdb`, 6,763 active rows | `artifacts/site-crawls/oscilar-com-conditional-baseline-20260715-a010c673/plan.json` and `.10x/evidence/2026-07-14-oscilar-site-index-and-recruiter-brief.md` |

Both are website cards in `gcp-us-central1` with model `BAAI/bge-small-en-v1.5`, precision `float32`, plan schema 1, and active website ranking defaults `page` / `none` / pool 20 / `max`. Semantic fields use source-backed website/product language from the retained evidence and crawl content. The pinned routing revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` was already present in the local Hugging Face cache.

Local upserts created two enabled cards in `/Users/crlough/Code/personal/turbo-search/.turbo-search/catalog.json`. The resulting catalog is schema 1 with revision:

`cd77c5ce97dd7f8df82b191b9e534d0c5535c7fa5224ef81edcbacb7732b01e6`

Catalog validation observed sorted cards, 384-dimensional persisted vectors, vector norms `0.99999998` and `1.00000013`, and successful hash validation through `buoy catalog list --all` and routing load. Catalog/list/route JSON did not expose vectors.

The user's exact local query succeeded:

```text
uv run buoy retrieve "what is the purpose of oscilar?" --auto-route --dry-run \
  --catalog /Users/crlough/Code/personal/turbo-search/.turbo-search/catalog.json --json
```

Observed route order:

1. `site-oscilar-com-v1` — lexical rank 1, semantic rank 1, hybrid score `0.03278688524590164`;
2. `site-dagster-io-benchmark-v1` — semantic rank 2, hybrid score `0.016129032258064516`.

The output reported `dry_run=true`, `credentials_required=false`, `turbopuffer_api_calls=false`, and `api_calls_occurred=false`.

## Procedure

1. Ran `git status --short --branch` and `git worktree list`; operational tracked records live on `work/backfill-live-namespace-catalog`, while the ignored canonical user state remains under the main checkout.
2. Inspected `buoy namespaces --help`, `buoy catalog upsert --help`, `src/buoy_search/namespaces.py`, and `src/buoy_search/catalog_cli.py` before any remote or local operation.
3. Ran `uv run buoy namespaces --json` once using the inherited API key/region. Output was captured without printing or persisting credential values.
4. Read local DuckDB state and tracked plan/evidence files only; generated the pre-mutation match table.
5. Ran two `buoy catalog upsert ... --catalog /Users/crlough/Code/personal/turbo-search/.turbo-search/catalog.json --json` commands with `TURBOPUFFER_API_KEY` removed from each subprocess environment. No other live namespace was registered.
6. Ran `catalog list --all` and the exact dry routed query with the canonical catalog path and with `TURBOPUFFER_API_KEY` removed.
7. Re-ran the user's two commands verbatim from the main checkout, again with the API key removed: `uv run buoy catalog list --all` reported two enabled cards, and `uv run buoy retrieve "what is the purpose of oscilar?" --auto-route --dry-run` selected Oscilar first. Both resolved `.turbo-search/catalog.json`; the expected legacy-root warning remained.
8. Read the local catalog JSON to verify vector dimensions and norms; no vector values were copied to records or output.

## What this supports or challenges

This supports that the pre-release Oscilar and benchmark Dagster namespaces can be safely backfilled from exact live existence plus trustworthy local provenance, and that the production auto-router now works for the user's Oscilar question without credentials or Turbopuffer calls.

It challenges the prior closure claim that routing was immediately ready after integration: prospective apply registration did not backfill pre-existing namespaces, and no operational population had occurred.

## Remote-side-effect attestation

Exactly one authorized read-only namespace-list operation contacted Turbopuffer. No apply, live retrieval, row query, namespace write, namespace deletion, or row mutation was invoked. Both catalog mutations and all post-mutation checks ran with `TURBOPUFFER_API_KEY` removed from the subprocess environment.

## Limits

- `site-dagster-io-v1` and `site-www-thistle-co-v1` remain intentionally absent from the catalog until authoritative compatibility metadata is recovered or a newly approved apply registers them.
- Fifty-eight locally evidenced historical namespace IDs were absent from the live inventory and were not registered.
- Manual backfill cards have manual semantic provenance and no catalog `last_plan_id`/`last_apply_id`; their exact applied lineage remains in the cited DuckDB/evidence records. A future approved apply will refresh system lineage while preserving manual semantics.
- No live routed retrieval or content quality judgment was authorized or performed. The successful check proves local selection, not remote retrieval quality or freshness.
