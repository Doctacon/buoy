Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/evidence/2026-07-20-c3-buoy-baseline-approval-checkpoint.md, .10x/evidence/.storage/2026-07-20-experimental-buoy-baseline-approval-a.json, .10x/specs/experimental-buoy-baseline-executor.md, .10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md, .10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md

# Experimental Buoy Baseline Approval A Grant

## What was observed

The user selected `Approve baseline write (Recommended)` in Pi. That answer grants exactly the Approval A text already presented under `## Approval A — Buoy baseline write` in `.10x/evidence/2026-07-20-c3-buoy-baseline-approval-checkpoint.md`; it does not alter, abbreviate, or widen that contract.

The immutable machine-readable grant is `.10x/evidence/.storage/2026-07-20-experimental-buoy-baseline-approval-a.json`. It records:

- `status`: `granted`;
- `granted_at`: `2026-07-20T23:24:06Z`;
- `granted_by`: `user`;
- `source_system`: `pi`;
- `conversation_id`: `runtime-id-not-exposed`;
- `message_id`: `sha256:4b066f19c3331b0074d4548b691b293072a50406df6f0557fcdba8e3d3f25d74`.

The runtime exposed no native conversation or message ID. `runtime-id-not-exposed` states that limit rather than inventing an identifier. The `message_id` is a content identifier: SHA-256 of the exact UTF-8 user answer text `Approve baseline write (Recommended)`, with no quotes and no trailing newline.

## Exact granted Approval A text

The following is one UTF-8 line with no leading blockquote marker and no trailing newline in the machine-readable grant:

```text
Approve one fail-closed experimental baseline operation in `gcp-us-central1` for retained plan `plan_b6c5d128295f442f` (artifact `b6c5d128295f442fcae21472c9bcb037ecb44101ca648115e8f666ba59a6f0ce`) from `Doctacon/buoy-search@fcb7abbe1652d2eab4ee23816b6d992d893603ac` into only `github-doctacon-buoy-search-v1`. Before writes, require the target namespace to be unambiguously absent or exact-schema/cosine-compatible and verified empty. Use 903 offline local float32 embeddings from MIT-licensed `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` only after cache manifest `5f783ebce23b6ac957d2741399b46e19502b1751acfd3c744b8c41103b138f35` and README/license hash `ddb964361a55c6e5dfca6361615854b260c9c960205d04c7520151aaa1d75837` revalidate. Set the `turbopuffer==2.4.0` SDK to `max_retries=0`; permit at most 26 physical provider attempts: 10 bounded reads and 16 writes, comprising exactly 15 content upserts (14 × 64 rows plus 1 × 7 rows), at most one conditional catalog-card upsert, at most 904 attempted write-row positions, and at most 1,817 returned read-row positions. Capture every content/catalog attempt and response with request counts, exact or explicitly absent `rows_affected`, redacted billing or explicitly absent billing, and partial/indeterminate outcomes. Permit zero row/namespace/card deletes and no retry, pagination, schema/signature fallback, cleanup delete, other namespace/card, or reassignment of unused request slots. After writes, require two bounded strong reads to match exactly all 903 intended rows before the catalog mutation, then two exact-card reads to match the intended stable card revision before local DuckDB applied-state success commit. Abort on any source/artifact/model/license/cache/state/schema/distance/row/card/count/budget mismatch; on content mismatch make no catalog-card or local-state commit, and on catalog mismatch make no local-state or card-success commit while reporting any possible remote partial effect. Provider/account dollar pricing is unknown, so this approval binds operational exposure rather than a dollar ceiling. It does not authorize C3 retrieval, a recrawl/replan, another namespace, a default change, or promotion.
```

## Immutable byte pins

- Approval text encoding: UTF-8, no BOM, one line, no trailing newline.
- Approval text bytes: `2206`.
- Approval text SHA-256: `bafc2500292bc8fcfc4aa806873782d43689330c704620f8981684a3796bfa10`.
- Grant record encoding: canonical compact JSON, UTF-8, no BOM, keys sorted recursively by Python `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"))`, no trailing newline.
- Grant record bytes: `2627`.
- Grant record SHA-256: `46a44e9440425ef73c66e69d64d7e83a7c098ce0fa3f85f2caf7f8d7685cc5ec`.
- User-answer content bytes: `36` UTF-8 bytes, no trailing newline.
- User-answer content SHA-256: `4b066f19c3331b0074d4548b691b293072a50406df6f0557fcdba8e3d3f25d74`.

These pins are suitable for the separately reviewed source change required by `src/buoy_search/experimental_baseline.py`. This record-only change intentionally leaves `APPROVAL_A_GRANTED_RECORD_SHA256` and `APPROVAL_A_GRANTED_PROVENANCE` set to `None`.

## Approval B exclusion

Approval B is explicitly excluded and remains ungranted. This Approval A grant authorizes neither C3 retrieval nor any raw-candidate capture, ANN/BM25 query, other namespace/card operation, duplicate baseline attempt, recrawl/replan, delete, retry, cleanup delete, fallback, default change, or promotion. Approval B cannot be requested as satisfied until this exact Approval A grant is source-pinned, independently reviewed and integrated, and the one authorized live baseline operation produces independently reviewable compatible-baseline evidence.

## Procedure and boundary

1. Read the existing checkpoint Approval A block and parsed the checked-in `APPROVAL_A_TEXT` literal without importing project code.
2. Verified the checkpoint text and source literal are byte-identical.
3. Recorded the exact user selection, timestamp, actor, truthful runtime-limited provenance, exact expanded contract, and byte hashes in the immutable JSON grant.
4. Opened the bounded sequential source-pin/review/integration/live-execution ticket and updated only C3/parent blockers and references.
5. Performed record/reference/diff validation only.

No grant constant was set. No credential or retained state was read, no model was imported/loaded/downloaded, no provider client or resource was constructed, no network/provider call occurred, and no namespace, card, catalog, pending record, DuckDB applied state, source corpus, dataset, default, or other domain state was mutated.

## What this supports

This supports only that Approval A is now exactly granted and durably source-pinnable. It does not establish that reviewed integrated source contains the grant pins, that the retained plan/cache/state or remote target is compatible, that any live attempt occurred or succeeded, that Buoy is compatible, or that C3 is executable.

## Limits

The Pi runtime did not expose native conversation/message identifiers, so provenance binds the exact answer content rather than a native message object. The current repository still mechanically rejects live execution because both source grant constants are `None`. C3 remains `blocked` pending reviewed integration of the exact pins, one and only one authorized live operation with complete success/partial-state evidence, compatible-baseline review, and separate Approval B.
