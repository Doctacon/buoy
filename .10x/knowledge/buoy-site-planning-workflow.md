Status: active
Created: 2026-07-02
Updated: 2026-07-18

# Buoy Site Planning Workflow

For a new credential-free HTTP(S) website, the shortest Turbopuffer-local planning command is:

```bash
uv run buoy plan "https://example.com/"
```

From 2026-07-02 onward, interactive text-mode `plan` and `crawl` runs show a default one-line progress indicator on stderr. It updates in place with crawl/plan phases so long crawls do not feel stalled and do not spam terminal output. The renderer truncates messages to terminal width so long URLs do not soft-wrap into apparent new lines. Progress labels use `cap=` for crawl limits; sitemap crawl labels add a sitemap-derived URL estimate when available instead of treating the cap as the known total.

Default website planning caps are `3000` pages and `120000` chunks. Use lower caps for smoke tests or when you only need a subset.

Default website crawl strategy is `--crawl-strategy sitemap`: use robots/sitemap discovery and fall back to link crawling only when sitemap discovery yields no pages. Use `--crawl-strategy link` to force link-only crawling, or `--crawl-strategy hybrid` to explicitly crawl sitemap pages and then same-site links before merging both results.

Default website docs-version behavior is `--docs-version-policy warn`: detect repeated sitemap families such as `/docs/1.10.2/**`, `/docs/latest/**`, and `/docs/nightly/**`, then stop before page crawling so the user chooses intentionally. For duplicated version docs, prefer `--docs-version-policy latest` for moving current docs, `stable-latest` for the highest semantic version, `latest-nightly` for current plus preview docs, or `all` to keep every version.

Default website language behavior is `--language-policy english`: when sitemap analysis detects a multilingual locale-prefix family, keep unprefixed and `/en/**` pages while adding effective excludes for detected non-English locale prefixes such as `/de/**`, `/fr/**`, `/pt-br/**`, or `/zh-cn/**`. Use `--language-policy all` when the intended index includes every language.

Progress behavior:

- enabled by default only for interactive terminals;
- suppressed automatically for `--json`;
- suppressed automatically when stderr is not a TTY, such as redirected logs or CI;
- disabled explicitly with `--no-progress`.

Useful bounded planning variants:

```bash
uv run buoy plan "https://example.com/" --max-pages 10 --max-chunks 200
uv run buoy plan "https://example.com/" --include-path "/docs/**" --max-pages 100
uv run buoy plan "https://example.com/" --crawl-strategy hybrid
```

After inspecting the plan, run explicit local-only preflight with:

```bash
uv run buoy apply --dry-run
```

For normal interactive execution, plain `uv run buoy apply` performs that preflight, displays it, and prompts `Apply this plan? [y/N]`; only exact `y`/`yes` proceeds. Use `--approve` only for separately authorized non-interactive execution.

Before preflight, inspect `first_apply`, `state_first_apply`, the local state path, prior apply provenance, upsert counts, and stale-row counts. A request to create a new namespace is not authority to refresh an existing deterministic namespace. If the reviewed plan reports prior applied state, pause before any preflight or live write and ask the user to choose among:

- use the existing namespace without writes;
- refresh the existing namespace under explicitly renewed write authority, with stale-row handling stated separately;
- create a genuinely new versioned namespace from a new plan targeting that namespace.

Do not infer the choice from the absence of an active ticket or record: local applied state can reveal prior work that project records do not index. Only confirm interactive plain apply with `y`/`yes`, or use `uv run buoy apply --approve` non-interactively, after the selected namespace and exact live-write action are explicit and the plan for that target has been reviewed. Enter/no/EOF cancels without writes; plain non-interactive apply is rejected.
