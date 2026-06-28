Status: done
Created: 2026-06-25
Updated: 2026-06-25
Depends-On: .loom/specs/github-repo-url-ingestion.md, .loom/research/2026-06-25-github-repo-url-ingestion-research.md, .loom/knowledge/github-repo-ingestion-vocabulary.md

# GitHub Repository URL Ingestion Plan

## Scope

Implement automatic GitHub repository URL handling for the existing `turbo-search` plan/apply workflow.

A user should be able to run:

```bash
uv run turbo-search plan https://github.com/Doctacon/open-streaming-lab
```

and receive a local-only, reviewable plan over repository contents, with repo-specific namespace/state/output defaults and the same apply/preflight/approved-apply path used by ordinary websites.

## Non-scope

- Do not implement private repository authentication in this plan.
- Do not crawl rendered GitHub HTML as the repository source.
- Do not ingest GitHub issues, PRs, releases, discussions, or wikis.
- Do not run live turbopuffer writes or live retrieval as part of implementation validation unless explicitly approved in the current conversation.
- Do not delete namespaces or stale rows except through the existing explicit `apply --approve --delete-stale` path.

## Child tickets and sequencing

Execute child tickets in this order. Independent test/doc updates can be parallelized only after the source and artifact contracts are stable.

1. `.loom/tickets/2026-06-25-github-repo-url-parser-and-source-routing.md`
   - Add source detection, GitHub URL parsing, canonical repo identity, and repo-specific namespace/out-dir/state defaults.
   - Must land before acquisition/corpus work so later code has stable typed inputs.

2. `.loom/tickets/2026-06-25-github-repo-local-acquisition.md`
   - Add local-only public repo metadata/default-branch resolution and shallow clone/fallback acquisition.
   - Depends on parser/source-routing ticket.

3. `.loom/tickets/2026-06-25-github-repo-file-selection-and-corpus.md`
   - Enumerate tracked files, apply default/user filters, write generated Markdown corpus with GitHub metadata.
   - Depends on acquisition ticket.

4. `.loom/tickets/2026-06-25-github-repo-aware-chunking-and-artifacts.md`
   - Ensure repository corpus/chunks feed existing plan artifacts safely, with code-aware fallback chunking or an explicit safe Markdown wrapper strategy.
   - Depends on corpus ticket.

5. `.loom/tickets/2026-06-25-github-repo-cli-docs-validation.md`
   - Wire CLI summaries/help/docs, validate end-to-end dry-run behavior with mocks/local fixtures, and ensure ordinary website behavior remains compatible.
   - Depends on the implementation tickets above.

## Acceptance criteria

The parent plan is complete when all child tickets are done and the following end-to-end behavior is true:

- `turbo-search plan https://github.com/Doctacon/open-streaming-lab --json` classifies the input as `github_repo`.
- The command produces repo-specific defaults:
  - namespace candidate: `github-doctacon-open-streaming-lab-v1`
  - site ID: `github-doctacon-open-streaming-lab`
  - default output dir: repo-specific, not `github-com`.
- Plan generation is local-only with respect to turbopuffer: no credentials, embeddings, or turbopuffer API calls.
- Repository content comes from git acquisition, not Scrapling crawling of GitHub UI.
- Artifacts include `plan.json`, `summary.json`, `manifest.json`, `chunks.jsonl`, and generated `pages/*.md`.
- Apply preflight can verify the generated plan without GitHub/turbopuffer credentials.
- Existing website crawl/plan/apply tests continue to pass.
- Documentation shows the one-command GitHub repo example and filter examples.

## Progress and notes

- 2026-06-25: Researched GitHub repository ingestion practices, GitHub metadata/default-branch handling, git clone options, file filtering, and code-aware chunking. Captured research in `.loom/research/2026-06-25-github-repo-url-ingestion-research.md`.
- 2026-06-25: Drafted behavior contract in `.loom/specs/github-repo-url-ingestion.md` and vocabulary in `.loom/knowledge/github-repo-ingestion-vocabulary.md`.

## Current State

Done. All child tickets are closed. Public GitHub repository URLs are now automatically detected, acquired through local git, filtered into a generated Markdown corpus, planned through the existing artifact/diff/apply-preflight workflow, and documented.

## Journal

- 2026-06-25: Began execution under `/loom-driver`; set parent plan active and started the first child ticket.
- 2026-06-25: Completed parser/source-routing ticket; evidence: `.loom/evidence/2026-06-25-github-repo-url-parser-routing-validation.md`.
- 2026-06-25: Completed local acquisition ticket; evidence: `.loom/evidence/2026-06-25-github-repo-local-acquisition-validation.md`.
- 2026-06-25: Completed file selection/corpus ticket; evidence: `.loom/evidence/2026-06-25-github-repo-file-selection-corpus-validation.md`.
- 2026-06-25: Completed repo-aware chunking/artifacts ticket; evidence: `.loom/evidence/2026-06-25-github-repo-aware-chunking-artifacts-validation.md`.
- 2026-06-25: Completed CLI/docs validation ticket; evidence: `.loom/evidence/2026-06-25-github-repo-cli-docs-validation.md`.
- 2026-06-25: Final validation ran `uv run python -m unittest discover tests`: 103 tests passed.

## Blockers

- None for public repository MVP.
- Product decision still needed before private repository support, Tree-sitter semantic chunking, or issue/PR/wiki ingestion.
