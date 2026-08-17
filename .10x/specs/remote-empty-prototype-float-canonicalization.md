Status: active
Created: 2026-08-16
Updated: 2026-08-16
Amends: .10x/specs/routing-prototype-float-canonicalization.md

# Remote Empty-Prototype Float Canonicalization

At the Turbopuffer row boundary, canonicalize every persisted
`routing_prototype_vector` coordinate through the same IEEE-754 binary32 round
trip already applied to the base `[384]f32` vector, including cards with no
routing examples or source passages.

This is a remote representation repair only. Local empty prototypes remain the
exact legacy base projection, their semantic/vector hashes and card revisions
remain byte-compatible, schema-v1 behavior remains unchanged, and no writer,
schema, routing, model, or content contract changes. Provider values in the
same float32 bucket must restore the exact card; values in an adjacent bucket
must still fail closed.
