Status: active
Created: 2026-07-23
Updated: 2026-07-23

# Command Center Operator Interface

## Purpose and scope

Provide a React + TypeScript + Vite read-only operator console over the local Buoy API. Node is build/development-only; production uses packaged static assets from Python.

## Product model

The UI MUST explain: sources originate knowledge; plans are reviewed snapshots and proposed changes; namespaces are searchable applied snapshots; catalog cards describe and route to namespaces; future graphs are evidence-backed semantic models derived from namespaces.

## Routes and behavior

- `/`: local counts, recent plans, attention items, artifact errors, and remote `Not checked` state with an explicit refresh button.
- `/namespaces`: filterable inventory table by namespace, source kind, and local/remote/catalog statuses; no actions that mutate.
- `/namespaces/:namespace`: overview, safe source provenance, retrieval settings, plans/diffs, search entry point, and graph placeholder.
- `/plans`: deterministic plan history with artifact/source/diff/count metadata.
- `/plans/:planId`: identity, provenance, source activity, embedding contract, diff, page/Markdown preview, bounded paginated chunks, warnings/errors, and explicit Phase 1 read-only notices. Remote-source plans MUST state they can be reviewed without reconnecting to the source warehouse.
- `/search`: explicit or automatic routing controls, bounded ranking inputs, execution-impact notice, and escaped citation-rich results.
- `/graphs`: labeled future flow from namespace selection through evidence-backed graph snapshot and taxonomy/ontology exploration, with no generated graph data.

## UX and security

Use the existing Buoy identity, persistent navigation, semantic controls/tables, keyboard access, contrast, loading/empty/error states, responsive CSS, and accurate status badges. Content and Markdown MUST be rendered as escaped text; `dangerouslySetInnerHTML` MUST NOT be used. Remote refresh MUST never be automatic. No secrets or credentials may be stored in the browser.

## Acceptance criteria

Vitest and React Testing Library cover dashboard states, namespace filtering/detail, plan detail and escaped Markdown, search validation/results/missing credentials, explicit remote refresh, graph placeholder, and absence of mutation controls.

## Exclusions

No component framework, Redux, Tailwind unless already present, Electron, hosted deployment, WebSockets, workers, source/apply/delete/catalog controls, graph extraction/storage/editing, Cytoscape, or fake graph data.
