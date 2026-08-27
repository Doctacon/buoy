Status: recorded
Created: 2026-08-25
Updated: 2026-08-25
Relates-To: .10x/decisions/one-time-provider-invocation-receipt-final-recovery.md, .10x/tickets/2026-08-25-provider-invocation-receipt-final-recovery-plan.md
Review: .10x/reviews/2026-08-25-provider-invocation-receipt-final-recovery-activation-review.md

# Provider Invocation Receipt Final Recovery Authorization

## What was observed

The repository owner explicitly authorized one final forward-only recovery that
supersedes the consumed one-time successor without reopening any consumed
attempt:

- provider-free preparation is repeatable and MUST use exact reviewed source
  commit `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
  `9017c4a335938faca80cdded54545df8b79c12f8`, in a local VCS-aware clone or
  checkout so Hatch-VCS can derive the reviewed version;
- preparation MUST use an owner-private UV cache, seeded only by read-only copy
  from the existing cache, and MUST keep every build/runtime write in owned
  temporary state;
- preparation MAY rebuild and correct provider-free harnesses until it produces
  the exact reviewed wheel and passes package, routing, and receipt checks, or
  establishes a real product defect;
- preparation MUST NOT access a credential value, construct a model, reach DNS,
  TLS, provider or other network behavior, open or invoke telemetry storage/API/
  commands, retrieve content, install or replace a global tool, mutate a ref, or
  change source, tests, specifications, locks, or routing data;
- the complete immutable candidate and runtime MUST be retained privately for
  independent candidate review, and no private path may enter durable records;
- only an independent candidate **PASS/GO** tied to the exact evidence and
  immutable candidate can authorize the dependent live child;
- after that GO, the already prepared candidate may run exactly one automatic
  live command with the established case, dataset, and model, telemetry off,
  provider activity read-only, catalog invocation count at most 5, content
  invocation count at most 18, and no preview, explicit command, substitution,
  provider retry, command retry, receipt retry, or second command; and
- command start consumes the live authority. PASS requires a truthful successful
  original outcome, one strict canonical content-free all-success receipt,
  exact post-state equality, bounded retention and cleanup, and independent
  final review, without claims about wire sends, SDK retries, billing, cost, or
  rate limits.

The shaping baseline was clean repository HEAD
`da928dd1ef339e16d525ba6c95f2bf42e90ab667`, tree
`5eaf0f3ec6d7ee3a77cec04f5711782ceb5ad0ad`.

## What this supports

This supports the linked active decision, one non-executable parent plan, one
open/inactive provider-free preparation child, and one dependent blocked/
inactive live-command child. It expressly supersedes only the consumed
one-time decision; all three consumed attempt tickets remain blocked, consumed,
and ineligible.

## Limits

This authorization records and shapes future authority only. It does not
activate either child, export or clone source, access or seed a cache, build or
install a package, run a validator or test, inspect a credential value, construct
a model, open telemetry, access provider/network behavior, issue GO, or start a
live command. It contains no query, namespace, content, result, credential
value, provider/account identifier, private operational path, raw diagnostic,
or receipt bytes.
