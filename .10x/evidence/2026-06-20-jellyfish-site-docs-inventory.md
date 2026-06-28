Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-turbopuffer-jellyfish-rag-plan.md, .loom/research/2026-06-20-turbopuffer-markdown-rag-research.md

# Jellyfish site docs corpus inventory

## What was observed

The repository currently contains a single corpus directory, `jellyfish-site-docs/`, with Markdown exports of Jellyfish site pages.

Observed facts:

- Markdown file count: `1124`
- Directory size: `12M`
- Example files include blog, library, integration, platform, solution, event/webinar, newsroom, and thank-you pages.
- Sample file `jellyfish-site-docs/jellyfish.co_blog_how-to-measure-developer-productivity_.md` starts with YAML frontmatter:
  - `url: "https://jellyfish.co/blog/how-to-measure-developer-productivity/"`
  - `title: "How To Measure Developer Productivity (+Key Metrics)"`
- After frontmatter, the body includes scraped site chrome/boilerplate such as topbar CTAs, skip links, and "In this article" text before article content.

## Procedure

Commands/inspection performed from `<repo-root>`:

```bash
find jellyfish-site-docs -type f -name '*.md' | wc -l
# 1124

du -sh jellyfish-site-docs
# 12M jellyfish-site-docs

find jellyfish-site-docs -maxdepth 2 -type f | head -50
# showed representative .md files across URL-derived filenames
```

Read a sample Markdown file with the `read` tool:

```text
---
url: "https://jellyfish.co/blog/how-to-measure-developer-productivity/"
title: "How To Measure Developer Productivity (+Key Metrics)"
---

New episode: Building Safe, Useful AI for 500M+ Users, with Flo Health's Director of Engineering. [Watch now](...)

[Skip to content](...)

In this article
...
```

## What this supports or challenges

Supports the plan to build a local Markdown RAG ingestion pipeline that:

- Reads YAML frontmatter for `url` and `title` citation metadata.
- Normalizes/removes repeated site boilerplate before chunking where safe.
- Chunks by Markdown structure rather than treating each file as one document.
- Stores one turbopuffer row per chunk, not one row per page.

## Limits

This inventory does not prove all 1124 files have valid frontmatter or useful body content. It inspected one representative file and filesystem-level counts only. Full corpus validation belongs in the indexing ticket.
