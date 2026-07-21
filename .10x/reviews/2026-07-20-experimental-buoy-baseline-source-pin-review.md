Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Target: PR #73 at `f7694940d3b02e6a59d613270881e8fef29a0af5`
Verdict: pass

# Experimental Buoy Baseline Approval A Source-Pin Review

## Target

Step 1 source-pin implementation at PR #73 head `f7694940d3b02e6a59d613270881e8fef29a0af5`.

## Findings

Independent review confirmed:

- the only executable-source change pins the exact Approval A grant SHA-256 `46a44e9440425ef73c66e69d64d7e83a7c098ce0fa3f85f2caf7f8d7685cc5ec` and exact three-field provenance;
- Approval A text/hash, executor behavior and budgets, SDK/dependencies, lockfile, CLI, defaults, and ordinary paths remain unchanged;
- validation requires exact grant fields/text, raw-byte hash, and provenance, with no alternate or caller-provided authority;
- tests validate the checked-in grant, every byte-position mutation, provenance mutation, and text mutation;
- no live route, credential read, model load, provider construction/call, or retained/domain-state operation occurred;
- exact-head Python 3.11, Python 3.13, ranking-contract, 495-test, distribution, diff, mergeability, and current-develop gates pass.

## Verdict

Pass. Step 1 may integrate. Step 2 remains ineligible until a separate integration session merges the exact reviewed source pins into `develop` and a fresh preflight satisfies every ticket stop condition.

## Residual risk

Real model/provider/local-state behavior remains intentionally unexecuted. Approval B and C3 remain blocked.
