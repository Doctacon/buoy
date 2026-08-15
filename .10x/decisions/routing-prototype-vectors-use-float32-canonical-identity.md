# Routing prototype vectors use float32 canonical identity

Status: accepted

Routing prototype coordinates with non-empty examples MUST be rounded through a
finite IEEE-754 binary32 encode/decode before their vector hash and containing
card revision are computed.  The remote reader MUST apply the same transform
before validation.

This is an identity boundary, not a ranking-precision change: the routing model
and base ANN vector already use the float32 contract, and observed provider
round-trip error was at most `2.7755575615628914e-17`.  Canonicalization removes
transport-only last-bit differences while retaining the normalized 384-value
projection.

Schema-v1 cards and cards with no routing examples retain their exact legacy
base projection and hashes.
