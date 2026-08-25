Status: active
Created: 2026-08-25
Updated: 2026-08-25

# Exact Reproduced Package Digests Inherit Reviewed Safety

## Exact-byte inheritance

When an immutable package candidate reproduces the exact cryptographic digest
of package bytes already covered by a focused package review, the reviewed
member inventory, path containment, link safety, metadata, entry-point, and
source-to-package evidence applies to the reproduced bytes. The operational
preflight must bind the governing source identity, filename, size, and SHA-256
before relying on that evidence. A digest, size, filename, or source mismatch is
not inheritance and must fail closed.

For the provider-invocation receipt wheel, the governing package evidence is
`.10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md`
and its independent PASS review is
`.10x/reviews/2026-08-24-provider-invocation-receipt-integration-review.md`.
Those records cover the exact 78-member wheel at SHA-256
`42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`.

## One-shot operational preflight

A one-build, no-rebuild operational preflight must not author or run a novel,
stricter archive member-type classifier after exact digest reproduction. Such a
classifier adds a new acceptance premise after reviewed byte identity is known
and can turn a harness disagreement into a false candidate defect. Verify the
exact candidate identity and reuse the reviewed package-safety evidence
cryptographically. Output-directory checks remain separate from archive
classification and may admit only the exact wheel plus an explicitly approved
build-tool marker.

## Provider-free harness correction

A provider-free validator, isolated installer, or harness can fail because of
its own environment, dependency discovery, or assertion logic while the exact
candidate remains immutable. Correcting and rerunning that provider-free
harness against the same source and wheel is separate from live authority. It
must not rebuild, mutate, or substitute candidate bytes, and it must not read a
credential value, construct the model, access provider/network, open telemetry
storage/API, or touch global state. Keep only bounded nonsensitive diagnostics
while correcting the harness and delete them before any live-access gate.

A demonstrated candidate defect still fails closed. Harness correction never
activates a ticket, supplies independent GO, starts a command, or creates retry
authority after live command start.
