# Routing prototype float canonicalization

Status: active

For a card with one or more `routing_examples`:

1. validate the 384-value normalized finite prototype vector;
2. convert every coordinate with an IEEE-754 big-endian float32 round trip;
3. validate the resulting vector again;
4. compute `routing_prototype_vector_hash` and `card_revision` only from that
   canonical vector.

The persisted reader performs the same transform before checking the stored
prototype hash and card revision.  Values which canonicalize identically are
the same persisted identity.  Values in different float32 buckets remain
different.

Cards without examples continue to use the exact legacy semantic/base vector,
hash, and omission rules.  The remote schema remains exact v2 and the
prototype field remains a nonfilterable, non-ANN `[]float`.
