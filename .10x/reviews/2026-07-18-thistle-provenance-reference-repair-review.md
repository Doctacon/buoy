Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Target: .10x/specs/website-exact-host-crawl-boundary.md
Verdict: pass

# Thistle Provenance Reference Repair Review

## Target

The provenance paragraph in the active exact-host crawl-boundary specification after retirement of the dirty `thistle-site-test` worktree and local branch.

## Findings

A post-merge audit correctly found that the specification cited:

```text
thistle-site-test@d7a37d7:.10x/tickets/done/2026-07-11-block-cross-host-crawl-redirects.md
```

The ticket had been an untracked dirty-worktree file, not a path contained in commit `d7a37d7`; after manifest-authorized deletion, the citation was not resolvable. The triage research and exact path/hash inventories remained merged and correctly documented that the historical file was inspected, user-ratified, provider-specific historical provenance.

The repair removes the false commit-addressable claim and points to the durable merged disposition research plus exact storage inventories. It explicitly distinguishes historical untracked evidence from current authority and leaves every behavioral requirement unchanged.

Repository search found no other citation using `thistle-site-test@` or the missing ticket path.

## Verdict

Pass. Provenance is now truthful and resolvable without weakening or changing the active safety contract.

## Residual risk

The retired raw untracked ticket/evidence/review payloads are no longer available. Their path/hash provenance and material behavioral findings remain summarized in merged research/evidence, which is sufficient for current execution but not a byte-for-byte historical archive.
