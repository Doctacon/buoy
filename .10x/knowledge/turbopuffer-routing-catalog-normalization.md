Status: active
Created: 2026-07-18
Updated: 2026-07-18

# Turbopuffer Routing Catalog Normalization

Turbopuffer SDK/server round-trips do not reproduce every requested application representation byte-for-byte. Buoy's routing catalog accepts only three observed, mechanically equivalent normalizations before strict validation:

1. Absent nullable row extras `last_plan_id` and `last_apply_id` are equivalent to application `null`. Every other missing or extra card field remains invalid.
2. Returned metadata may omit `filterable:false` only for exact attribute `vector` with exact type `[384]f32`; the cosine ANN contract must still match. Scalar filterability, vector dimensions/type, and ANN remain strict.
3. `vector_encoding="float"` may render stored f32 values as nearby decimal floats. Incoming remote vector elements are round-tripped through IEEE-754 f32 before vector/card hashes are checked. Outgoing rows and local card parsing are not normalized this way. Decimal changes that round to an adjacent f32, non-finite values, overflow, stale hashes, wrong dimensions, or wrong norm remain invalid.

These are provider transport/metadata equivalences, not relaxed product semantics. New normalization must be established by bounded live evidence, encoded narrowly, independently reviewed, and retain strict negative tests.
