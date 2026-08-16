Status: recorded
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-activate-bounded-prototype-routing.md
Review: .10x/reviews/2026-08-15-bounded-prototype-routing-activation-review.md

# Bounded Prototype Routing PR Handoff Evidence

## Exact committed activation

The independently reviewed active authority and its final activation records
were committed as
`e85b62ed8e27565e1ca371e113ffba77ffb3dd3c`, tree
`b19d7c336fd695730db3e084eaba81dd55f86e69`, with sole parent
`d171cd887f615158a196dbeef8fa93830818ea64`. Its commit delta is exactly:

```text
.10x/evidence/2026-08-15-bounded-prototype-routing-activation.md
.10x/reviews/2026-08-15-bounded-prototype-routing-activation-review.md
.10x/tickets/2026-08-15-activate-bounded-prototype-routing.md
src/buoy_search/data/automatic_routing_confidence_calibration.json
```

The active artifact remains 2671 bytes at raw SHA-256
`3412bdb20f928de226e159344cac04ec52587da4134d6c079e9fc53a6aa75d9d`.
No production source, evaluator, test, workflow, documentation, packaged
canary, specification, or decision changed after the exact dormant
certification commit.

## Exact post-commit package validation

The clean `e85b62e` commit produced version
`0.4.1.dev141+ge85b62ed8` and these diagnostic, unpublished archives:

- wheel
  `buoy_search-0.4.1.dev141+ge85b62ed8-py3-none-any.whl`, 69 files,
  SHA-256
  `346c623edb3dfccd8ec1fa9cb7e006d60326d3df3e8efbd95c68e7fdecbc559e`;
  and
- source distribution
  `buoy_search-0.4.1.dev141+ge85b62ed8.tar.gz`, 140 files, SHA-256
  `800e8c7b5523b48906605742d8cd127ded0fce1631aa5fae78d47be5044d17f0`.

The distribution validator passed exact source/wheel/source-distribution
agreement for authority artifact SHA
`3412bdb20f928de226e159344cac04ec52587da4134d6c079e9fc53a6aa75d9d`,
the four packaged module receipts, evaluator-runner receipt, exact three-pack
canary inventory, and suite
`0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`.

A fresh no-dependencies wheel installation was then exercised with the
complete lock-identical Python 3.11 dependency runtime in isolated/no-bytecode
mode. The editable source entry was removed before import, the installed wheel
site was inserted explicitly, and every loaded `buoy_search` module was
asserted to resolve beneath that installed site. The no-argument loader
returned `mode=active`, `owner_approved=true`, revision
`active-16357c62-e559a8aa-v1`, active artifact SHA
`3412bdb20f928de226e159344cac04ec52587da4134d6c079e9fc53a6aa75d9d`,
and dormant source commit
`d171cd887f615158a196dbeef8fa93830818ea64`. This does not claim that the
no-dependencies installation environment alone contains runtime dependencies.

## Pull request and checks

Draft PR [#114](https://github.com/Doctacon/buoy/pull/114) opened from
`work/activate-bounded-prototype-routing` into `develop` with exact initial
head `e85b62ed8e27565e1ca371e113ffba77ffb3dd3c` and exact base
`94b06ac58c86e96ddd012aae0a4a019dcc548cef`. The base remained unchanged from
the dormant implementation boundary, and GitHub reported the PR mergeable.

Fresh CI run
[`31925850905`](https://github.com/Doctacon/buoy/actions/runs/31925850905)
passed all jobs on exact active commit `e85b62e`:

- [Python 3.11](https://github.com/Doctacon/buoy/actions/runs/31925850905/job/95113175186);
- [Python 3.13](https://github.com/Doctacon/buoy/actions/runs/31925850905/job/95113175179);
  and
- [Build distributions](https://github.com/Doctacon/buoy/actions/runs/31925850905/job/95113362180).

This records the behavior-bearing active commit and its exact fresh checks.
The ticket-status and handoff-evidence update that contains this receipt is
records-only; the final remote PR-head checks for that records-only closure are
reported externally because a commit cannot contain its own future identity
or check-run IDs.

## Compatibility risks

Automatic retrieval without explicit namespaces intentionally changes route
selection and may choose fewer or different corpora than the legacy selector;
explicit-namespace behavior and the maximum three-corpus fanout remain
unchanged. A missing, malformed, unapproved, byte-drifted, or catalog-drifted
active authority now fails closed before content access instead of silently
falling back to legacy routing. Any integration conflict that changes a bound
module, the authority artifact, a packaged canary, or another certified
receipt invalidates this evidence and requires renewed certification and
review rather than conflict-only repair.

## Effects and remaining authority

The post-commit package checks and installed-loader smoke made no provider or
model call. Across implementation and certification there was no provider
write, delete, schema/card/content mutation, content query, content-resource
acquisition, package publication, tag, GitHub Release, registry change, or
deployment.

This task branch is ready for integration review. PR #114 remains draft and
unmerged. Merging into `develop`, promoting to `main`, publishing, deploying,
or changing any provider state remains outside this task and requires the
normal separately explicit authority.
