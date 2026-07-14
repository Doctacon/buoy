Status: active
Created: 2026-07-14
Updated: 2026-07-14

# Buoy Rebrand Release Validation

## Purpose and scope

Define completion evidence for the code-level Buoy 0.2 rebrand before external repository or registry mutation.

## Required validation

- Build wheel and source distribution from a clean temporary output directory and inspect package contents and metadata.
- Install the built artifact into an isolated temporary environment and verify `buoy`, the deprecated `turbo-search` alias, `python -m buoy_search`, and bundled data loading.
- Run CLI parser/help/version checks with stdout/stderr assertions for alias deprecation and JSON cleanliness.
- In temporary directories, verify new `.buoy` defaults; legacy `.turbo-search` fallback; dual-root refusal; explicit-root override; existing DuckDB ledger loading; and old schema-supported plan preflight.
- Prove no compatibility validation copies, moves, deletes, re-embeds, or remotely mutates existing rows/namespaces.
- Run fixture autoresearch and repository-search eval validation after module/path dataset changes.
- Run the complete test suite, diff hygiene, local-link checks, and independent review.
- Confirm no active source, tests, user docs, skills, package metadata, or open records incorrectly present `turbo-search` as the primary identity. Historical records and explicit migration compatibility references are allowed.

## Release boundary

Passing this specification authorizes the code-level 0.2 artifact only. It does not rename GitHub, publish to PyPI, delete old packages, change remote Turbopuffer namespaces, or perform live retrieval/apply/evals. Those are separate external actions.
