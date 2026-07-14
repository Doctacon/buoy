Status: active
Created: 2026-07-13
Updated: 2026-07-13

# Documentation: Details on Demand

## Policy

Project documentation uses progressive disclosure. `README.md` is the shortest complete path from discovery to first successful index and retrieval; it is not the reference manual.

## README responsibilities

The README should let a new user quickly answer:

1. What does Buoy do?
2. Why is its plan/apply workflow safe?
3. How do I install it?
4. How do I index one source and search it?
5. Where do I go for the next level of detail?

Keep the heart visible: source → local plan → local preflight → approved apply → retrieval. Show websites, public GitHub repositories, and local documents as source choices without enumerating every source-specific constraint.

Aim for roughly 100 lines or fewer. Prefer one representative command over exhaustive option lists. Use direct language, short sections, and descriptive links.

## Details that belong elsewhere

Move material out of the README when it requires exhaustive defaults, extension lists, state migrations, lock mechanics, artifact retention rules, crawl/version/language policy matrices, ranking heuristics, metric formulas, eval dataset schemas, autoresearch internals, or operational edge cases.

Each detailed topic should have one canonical, clearly named Markdown home under `docs/`. README links should describe the user question answered, not merely repeat a filename.

## Duplication rule

Do not copy full explanations between README and reference docs. README may summarize a contract in one sentence and link to its canonical detail. CLI `--help` remains canonical for exhaustive flags and defaults.

## Showcase standard

- First runnable workflow appears near the top.
- Safe versus live commands are visually obvious.
- Examples are copyable and current.
- Internal implementation history is excluded from the user landing page.
- Links resolve, commands parse, and moved details remain discoverable.
