Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commit `792d6509ad7e08c14e90fbffd1ea2ef098e3a08d`
Verdict: pass

# Data Vault Analogy Scope Correction Review

## Target

Independent semantic review of commit `792d650` against the user-confirmed contract that Data Vault was only an analogy and Buoy must not build Data Vault.

## Findings

### Pass — the active decision captures the corrected contract

The new active decision states that Buoy **MUST NOT** build or require Data Vault 2.0 for this workstream, limits hub/link/satellite language to comparative analogy, and explicitly excludes Data Vault schemas, business-key governance, loading semantics, warehouse authority, and technology dependencies (`.10x/decisions/data-vault-is-analogy-not-architecture.md:17-35`). It preserves useful identity, relationship, provenance, history, ACL, correction, and deletion findings without selecting a taxonomy, ontology, graph schema, storage engine, extraction method, ACL policy, or threshold (`.10x/decisions/data-vault-is-analogy-not-architecture.md:33-35`). Its consequences require a new user-ratified decision before any future Data Vault component can enter scope (`.10x/decisions/data-vault-is-analogy-not-architecture.md:51-57`). This accurately captures analogy-only authority without inventing implementation semantics.

### Pass — the active parent plan no longer authorizes Data Vault or implementation

The renamed parent remains explicitly research-only and says it does not authorize product implementation, live Turbopuffer operations, or an architecture decision (`.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md:9-18`). Its ratified context identifies Data Vault as analogy rather than architecture, its shared invariants forbid warehouse requirements, and its acceptance/blocker language prevents implementation until findings are reconciled, the user ratifies an architecture, focused specifications exist, and executable tickets are opened (`.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md:20-26`, `:37-49`, `:51-60`, `:70-72`). The earlier formal-Data-Vault progress entry at line 77 is append-only history and is expressly corrected by line 81; it does not function as current authorization.

### Pass — all five research records have prominent, non-contradictory corrections

Each affected research record places its correction immediately after the title and before the historical question or findings:

- preliminary research: `.10x/research/2026-07-15-metadata-tagging-graphs-and-data-vault.md:7-20`;
- concept graph: `.10x/research/2026-07-15-data-vault-concept-graph.md:7-17`;
- governed tagging/filtering: `.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:7-17`;
- multi-hop/global retrieval: `.10x/research/2026-07-15-data-vault-multi-hop-global-retrieval.md:7-17`;
- namespace catalog/routing: `.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:7-17`.

The corrections consistently defer to the active decision, withdraw recommendations that require actual Data Vault machinery, and identify which non-Data-Vault findings remain useful. The historical questions and investigation bodies remain intact as provenance rather than being silently rewritten into post-hoc findings. The preliminary record additionally corrects its former interpretation and unresolved direction where those passages could otherwise appear current (`.10x/research/2026-07-15-metadata-tagging-graphs-and-data-vault.md:17-20`, `:235-251`).

### Pass — rename and history repairs are bounded

Repository-wide exact searches found no remaining occurrence of either the predecessor parent path or its basename. The live parent, all five research references, all affected review references, and all four completed child `Parent:` headers point to `.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md` (for examples, `.10x/research/2026-07-15-data-vault-concept-graph.md:25-29` and `.10x/tickets/done/2026-07-15-research-data-vault-concept-graph.md:1-5`). Diff inspection confirms that completed tickets changed only their `Parent:` path and completed reviews changed only the cited parent path; their historical semantics, findings, and verdicts were not rewritten.

### Pass — no product, specification, or implementation behavior was introduced

The commit changes only `.10x/decisions`, `.10x/research`, `.10x/reviews`, and `.10x/tickets`. It changes no specification, source, test, dependency, migration, generated artifact, or product documentation. The decision explicitly declines to select behavior, and the parent explicitly retains the research/ratification/specification/executable-ticket gates. No test run was necessary for this record-only semantic correction.

### Pass — no active contradictory authority remains

A status-aware scan found Data Vault references in only three live records: the new active decision, the open renamed parent plan, and the active preliminary research. The decision and parent prohibit Data Vault architecture; the preliminary research prominently defers to that decision and withdraws actual-Data-Vault recommendations. Remaining Data Vault language in done research/tickets and recorded reviews is historical comparison or preserved investigation provenance, not active contradictory authority.

## Verdict

**Pass.** Commit `792d650` is a coherent, bounded semantic record correction. No required repair was found.

## Residual risk

The intentionally preserved historical research and completed-ticket bodies still contain formal Data Vault terminology. A reader who skips the prominent scope corrections and active decision could quote those passages out of context. This is accepted preservation risk rather than a repair request: the correction placement, explicit withdrawal language, and active parent/decision authority are sufficient, while broader rewriting would damage historical provenance.
