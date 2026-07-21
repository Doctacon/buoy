Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Target: PR #74 at `115721f2c87e9a8d9f98f46c5b31ce44f1b17928`
Verdict: pass

# Experimental Buoy Baseline Step 2 Preflight Review

## Target

Independent adversarial review of the record-only stopped-preflight evidence in PR #74 at exact reviewed head `115721f2c87e9a8d9f98f46c5b31ce44f1b17928`, governed by `.10x/specs/experimental-buoy-baseline-executor.md` and `.10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md`.

## Findings

### PASS — the mandatory pre-invocation stop was correct

The checked-in structured evidence at `.10x/evidence/.storage/2026-07-20-experimental-buoy-baseline-step-2-preflight.json` is internally consistent with the human-readable account at `.10x/evidence/2026-07-20-experimental-buoy-baseline-step-2-preflight.md` and the ticket's stop conditions:

- `preflight_passed=false`, `invocation_occurred=false`, and the outcome is `stopped_before_invocation`;
- credential reads, model import/load, provider-client construction, provider requests, physical/read/write/delete attempts, write-row positions, and returned-row positions are all zero;
- all 26 fixed slots are present in order and marked `unused`, with no reassignment or slot error;
- the two top-level stop reasons exactly identify cache/license attestation and complete-evidence enforceability mismatches;
- the immutable Approval A grant remains exactly 2,627 bytes with SHA-256 `46a44e9440425ef73c66e69d64d7e83a7c098ce0fa3f85f2caf7f8d7685cc5ec`.

Because either mismatch independently triggers the ticket's mandatory pre-invocation stop, not calling `execute_experimental_baseline` was required. The one-invocation Approval A authority was not consumed.

### Significant — defect 1: cache-manifest validation does not reproduce the approved canonical pin

`src/buoy_search/experimental_baseline.py:404-412` constructs its own entry representation and hashes it with `stable_hash`; `src/buoy_search/experimental_baseline.py:431-432` then compares that result with the already-approved `CACHE_MANIFEST_HASH`. Over the unchanged 12-file, 267,599,430-byte snapshot at the exact approved revision, the executor produced `af97aa621263b66d6740dc188958660addfa533dc1b289deceed9c3edf8d81f5`, while the governing cache pin is `5f783ebce23b6ac957d2741399b46e19502b1751acfd3c744b8c41103b138f35`. The README hash, revision, file count, and resolved-byte total still matched. This is an implementation/serialization mismatch against the approved canonical manifest contract, not authority to replace the pin or alter cache bytes.

### Significant — defect 2: the exact pinned MIT statement is rejected because it contains a Markdown link

`src/buoy_search/experimental_baseline.py:420-421` correctly recognizes the exact pinned README's `license: mit` front matter but requires the literal plain-text substring `FlagEmbedding is licensed under the MIT License`. The same immutable README, whose checked hash is still `ddb964361a55c6e5dfca6361615854b260c9c960205d04c7520151aaa1d75837`, expresses that sentence as `FlagEmbedding is licensed under the [MIT License](...)`. The literal check therefore reports `license_statement_present=false` despite the exact approved README proving the intended MIT statement. The repair must remain bound to the existing README hash and MIT front matter rather than broadening trust to arbitrary text.

### Significant — defect 3: the public evidence result cannot reproduce required verified state without extra calls

`src/buoy_search/experimental_baseline.py:236-254` stores only a returned-row count in each `Attempt`, and `src/buoy_search/experimental_baseline.py:1305-1324` validates returned row bodies but does not retain them or an immutable secret-free projection in ledger evidence. The success payload at `src/buoy_search/experimental_baseline.py:847-861` reports aggregate row count, card revision, and a boolean local-state commit, but omits the required exact target/card returned-row projection, observed target/catalog schema and distance, and local applied-state hash. The active specification requires those facts after any run, and it forbids additional provider requests beyond the fixed ledger. Therefore a caller of the four-path public entry point cannot persist complete required evidence from this source.

## Procedure

1. Compared the PR's JSON and Markdown evidence with the active specification and ticket stop conditions.
2. Ran a standard-library-only assertion harness over the checked-in JSON, source text, and immutable grant record. It passed the stop-state, zero-activity, exact 26-unused-slot, exact mismatch, exact three-defect, and unchanged-grant assertions.
3. Inspected only checked-in source and records. This review did not read a credential, inspect model/cache bytes, construct a provider client, issue a provider request, invoke the executor, or mutate local/remote domain state.
4. Confirmed PR #74 exact reviewed head `115721f2c87e9a8d9f98f46c5b31ce44f1b17928` was based on current `origin/develop` `8c7750d84ebaf846ae519ccf164f2c7b72c9ec1c`; hosted Python 3.11, Python 3.13, and Build distributions checks all passed for that head.

## Verdict

PASS for the mandatory pre-invocation stop and for the exact characterization of the three implementation defects above. This is not a pass for live execution or baseline compatibility. No source repair is present in the reviewed diff.

## Residual risk

The three significant defects remain in current source and block any invocation. A separately implemented, tested, independently reviewed, and integrated narrow repair must pass a fresh non-credential/non-model preflight before the existing one-invocation authority can be considered executable. Remote namespace/card/account state, provider response/billing behavior, model runtime, and post-write compatibility remain unobserved. Approval B remains ungranted and C3 remains blocked.
