Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .pi/skills/turbopuffer-site-rag/SKILL.md, docs/agent-answering-workflow.md

# Private Credential Identifier Redaction

## What was observed

The user objected that private Proton Pass vault/item identifiers had been recorded in the newly created skill material. The skill references were updated to avoid storing private vault names, item titles, share IDs, or secret field values. Existing docs/Loom text was also scrubbed of the same exact private identifiers and replaced with generic placeholders.

A repository search for the exact private vault/item identifiers across the skill, docs, and Loom records returned no matches after redaction.

## Procedure

- Updated `.pi/skills/turbopuffer-site-rag/references/jellyfish-namespace.md` to use generic credential-retrieval placeholders only.
- Replaced the same private identifiers in `docs/` and `.loom/` records with generic placeholders.
- Searched the skill, docs, and Loom records for the exact private identifiers; no output was returned.

## What this supports

- The reusable skill no longer exposes the user's private Proton Pass vault name or item title.
- Durable project records no longer include those exact private identifiers.
- Future credential retrieval should ask the user or rely on the active session's private procedure rather than storing lookup identifiers in project files.

## Limits

- This evidence intentionally does not reproduce the private identifiers or literal search pattern.
- It does not inspect shell history, terminal scrollback, external chat summaries, or non-project storage outside the searched project records.
