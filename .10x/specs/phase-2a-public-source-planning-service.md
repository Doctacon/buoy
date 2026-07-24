Status: active
Created: 2026-07-23
Updated: 2026-07-24

# Phase 2A Shared Public-Source Planning Service

## Purpose and scope

Extract the existing CLI plan orchestration into a reusable Python application service used by both the CLI and command-center plan jobs. Phase 2A managed requests support only credential-free HTTP(S) websites and public GitHub repository-root URLs. Existing CLI support for local documents and DuckDB/BigQuery/Snowflake remains unchanged but is not exposed through managed jobs.

## Request contract

A managed request contains required `source_url` and optional `max_pages_or_files`, `max_chunks`, `namespace`, `include_paths`, and `exclude_paths`. Omitted limits use current source defaults. Namespace validation and target semantics MUST match the CLI. `source_url` MUST be at most 2048 characters, use only `http` or `https`, contain no URL userinfo, and current source detection MUST classify it as a credential-free HTTP(S) website or supported public GitHub repository root. GitHub `/tree/` and `/blob/` URLs MUST be rejected because arbitrary refs, subtrees, and blobs are outside managed scope. Existing source detection and canonicalization govern query and fragment handling; managed validation MUST NOT reject them categorically because website URLs may use them. Website validation is not a public-routability or SSRF firewall; the Command Center remains loopback-only under the local operator's control. No token, credential, local path, arbitrary Git ref, selector, custom chunking, or advanced source option is accepted.

## Service behavior

The service MUST own current source validation/detection, acquisition, Markdown materialization, indexing plan creation, artifact construction, local applied-state loading/diffing, catalog preview, artifact integrity verification, summary construction, and writing. It MUST call current domain functions and MUST NOT shell out to `buoy plan`.

The service accepts a progress callback and emits sanitized stage/message/count information. Each sanitized stage MUST be at most 64 characters and each sanitized message MUST be at most 500 characters. It MUST NOT read turbopuffer credentials, call turbopuffer, load an embedding model, update applied state, or mutate a routing catalog. It MUST lazily import database/local-document adapters only when existing CLI source modes require them; managed public-source planning imports none of those adapters.

CLI `_run_plan` MUST delegate to this service while preserving existing arguments, output, progress behavior, artifact schema, errors, and exit semantics.

## Artifacts

Managed jobs write ordinary artifacts into a unique directory under `<artifacts-root>/command-center/plans/<job-id>/`. The managed output directory MUST be absent before planning begins; the service MUST reject an existing file, directory, or symlink rather than reuse it. The job ID affects only storage/audit identity, never source, document, chunk, plan namespace, or row identity. Success requires complete, verified `plan.json`, `manifest.json`, `chunks.jsonl`, `summary.json`, and `pages/` artifacts using the unchanged `PLAN_SCHEMA_VERSION`. For a managed run, `summary.json` MUST include the validated originating plan-job ID as read-only audit metadata; that metadata MUST NOT affect plan, source, document, chunk, namespace, row, or schema identity. The plan remains discoverable by Phase 1 and applicable only through the existing explicit CLI.

## Acceptance criteria

Tests prove shared CLI/web service use; website and GitHub request construction; namespace override; progress callbacks; unique managed output; integrity before success; preserved CLI behavior; and absence of turbopuffer credentials/calls, model load, and source-database adapter imports.

## Exclusions

No managed local files, databases, credentials, private repositories, reusable source definitions, apply, catalog mutation, or namespace mutation.
