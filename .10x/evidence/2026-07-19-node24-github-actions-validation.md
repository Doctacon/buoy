Status: recorded
Created: 2026-07-19
Updated: 2026-07-20
Relates-To: .10x/tickets/done/2026-07-14-update-node24-github-actions.md

# Node.js 24 GitHub Actions Validation

## What was observed

- `actions/checkout` release `v5.0.1` resolves to commit `93cb6efe18208431cddfb8368fd83d5badbf9bfd`, and that commit's `action.yml` declares `runs.using: node24`.
- `astral-sh/setup-uv` release `v7.6.0` resolves to commit `37802adc94f370d6bfd71619e3f0bf239e1f3b78`, and that commit's `action.yml` declares `runs.using: "node24"`.
- The exact tag-to-SHA mappings agreed between the GitHub Git Data API and independent `git ls-remote` queries against the upstream repositories.
- Local Python 3.11 and 3.13 full test runs each passed all 422 tests.
- Local distribution build produced the expected wheel and source archive outside the repository.
- Pull-request CI run [`29713297074`](https://github.com/Doctacon/buoy-search/actions/runs/29713297074) completed successfully for implementation commit `14496acc3693744e8231d30b6e718c625e4bd421`: Python 3.11, Python 3.13, and Build distributions all passed.
- GitHub's check-run annotation API returned an empty annotation list for all three hosted jobs, confirming there were no Node.js 20 runtime deprecation annotations.
- The workflow diff changes only the `actions/checkout` and `astral-sh/setup-uv` full-SHA pins and their identifying major-version comments. The static workflow test's expected majors changed correspondingly.

The selected revisions are the latest patch releases in the minimum upstream major lines that natively use Node.js 24 (`checkout` v5 and `setup-uv` v7). This avoids unrelated later-major adoption while including patch fixes in those compatibility lines.

## Procedure

Upstream provenance and runtime were verified for each action with the equivalent of:

```bash
gh api repos/<owner>/<action>/releases/tags/<tag> --jq .tag_name
gh api repos/<owner>/<action>/git/ref/tags/<tag> --jq .object.sha
git ls-remote https://github.com/<owner>/<action>.git refs/tags/<tag>
gh api 'repos/<owner>/<action>/contents/action.yml?ref=<full-commit-sha>' --jq .content | base64 --decode
```

Observed results:

```text
repo=actions/checkout release=v5.0.1 api_sha=93cb6efe18208431cddfb8368fd83d5badbf9bfd remote_sha=93cb6efe18208431cddfb8368fd83d5badbf9bfd runtime=node24
repo=astral-sh/setup-uv release=v7.6.0 api_sha=37802adc94f370d6bfd71619e3f0bf239e1f3b78 remote_sha=37802adc94f370d6bfd71619e3f0bf239e1f3b78 runtime=node24
```

Authoritative release pages:

- https://github.com/actions/checkout/releases/tag/v5.0.1
- https://github.com/astral-sh/setup-uv/releases/tag/v7.6.0

Local validation:

```bash
uv sync --locked --python 3.11
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q
uv sync --locked --python 3.13
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q
uv build --out-dir /tmp/buoy-node24-actions-dist
git diff --check
```

Results:

```text
Python 3.11: Ran 422 tests in 23.751s — OK
Python 3.13: Ran 422 tests in 23.251s — OK
Build: buoy_search-0.4.0-py3-none-any.whl and buoy_search-0.4.0.tar.gz built successfully
git diff --check: passed
```

Hosted validation and annotation inspection:

```bash
gh pr checks 53 --repo Doctacon/buoy-search --watch --interval 10
gh api repos/Doctacon/buoy-search/actions/runs/29713297074
gh api repos/Doctacon/buoy-search/check-runs/<job-id>/annotations
```

```text
Run 29713297074: completed / success
Python 3.11: success
Python 3.13: success
Build distributions: success
Annotations for all three check runs: none
```

## What this supports or challenges

This supports that the replacement pins are released, immutable full commit SHAs with independently corroborated upstream provenance, that both action metadata files natively select Node.js 24, that the workflow/static-test changes retain local project validation, and that the updated actions execute successfully on GitHub-hosted runners without Node.js 20 deprecation annotations.

## Limits

The successful hosted run covers the pull-request CI workflow, not the tag-only release workflow; triggering release validation would violate this ticket's explicit no-tag/no-release boundary. Independent review subsequently passed in `.10x/reviews/2026-07-20-node24-github-actions-review.md`; the review did not merge the pull request.
