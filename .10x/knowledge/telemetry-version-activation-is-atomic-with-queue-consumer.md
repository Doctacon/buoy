Status: active
Created: 2026-08-28
Updated: 2026-08-28

# Telemetry Version Activation Is Atomic with Its Queue Consumer

A new telemetry observation/envelope version MUST NOT become the production command default until its distinct inbox filename/path validator and a writer capable of consuming that version exist in the same integration state.

Publishing a new envelope through an older inbox poisons work that old/new writers interpret under the old contract. Suppressing publication after constructing a new observation silently drops otherwise-enabled telemetry. Creating a new inbox without a consumer strands work and can misstate status/flush behavior.

For staged implementation:

1. implement and test the new producer/envelope behind an explicit internal test seam;
2. implement any complete summary fields required by the envelope;
3. add the versioned inbox, writer, store, migration, status, and flush support; then
4. atomically switch production command creation and publication in the integration slice.

Historical producers/views remain exact. Intermediate milestones must state that activation is deferred rather than claiming production coverage from internal fixtures.
