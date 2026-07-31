Status: superseded
Created: 2026-07-14
Updated: 2026-07-14

# Turbopuffer Namespace Discovery

## Purpose and scope

Provide a read-only way to discover namespace IDs visible to the configured Turbopuffer account and region before choosing retrieval targets.

## Behavior

- `buoy namespaces [SEARCH]` MUST list remote namespace IDs using Turbopuffer's namespace-list API.
- `SEARCH` is optional. When present, Buoy MUST return namespace IDs containing the term case-insensitively. Because the API exposes only ID and prefix filtering, this is identifier search—not semantic content search.
- The command MUST follow all API pages rather than silently returning only the first page.
- The command MUST use `--region` when supplied, otherwise `TURBOPUFFER_REGION`, otherwise the existing default region.
- It MUST read `TURBOPUFFER_API_KEY` only when executing the command and MUST fail clearly when absent.
- Text output MUST show one matching namespace ID per line. An empty match MUST be successful and clearly say no namespaces matched.
- JSON output MUST contain region, search term or null, count, and ordered namespace IDs.
- Results MUST be sorted deterministically by namespace ID.
- The command MUST NOT embed text, query namespace contents, mutate namespaces, or infer descriptions/models from IDs.

## Acceptance scenarios

### List

Given paginated visible namespace IDs, when `buoy namespaces` runs, then every page is consumed and all IDs are printed once in deterministic order.

### Filter

Given IDs `site-dagster-v1` and `github-owner-repo-v1`, when `buoy namespaces dagster` runs, then only `site-dagster-v1` is returned.

### Missing credential

Given no API key, when the command runs, then it returns a user-actionable error without making a request.

## Explicit exclusions

Semantic namespace search, content queries, namespace creation/deletion, local namespace registration, embedding-contract inference, and automatic retrieval selection.
