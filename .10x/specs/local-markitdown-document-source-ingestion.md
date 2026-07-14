Status: active
Created: 2026-07-08
Updated: 2026-07-08

# Local MarkItDown Document Source Ingestion

## Purpose and scope

`buoy` MUST support a single local document/data filepath from a fixed MarkItDown-backed allowlist as a first-class source for the existing local-only `crawl`/`plan` workflow and existing explicit `apply` workflow.

This specification extends `.10x/specs/local-pdf-source-ingestion.md`. Existing PDF behavior MUST remain backward-compatible.

## Supported v1 extensions

The v1 allowlist is:

- `.pdf`;
- `.docx`;
- `.pptx`;
- `.xlsx`;
- `.xls`;
- `.csv`;
- `.html`, `.htm`;
- `.txt`, `.text`;
- `.md`, `.markdown`;
- `.json`, `.jsonl`;
- `.xml`;
- `.ipynb`;
- `.epub`.

## Behavior

### Source detection and identity

- A path ending in a supported extension that points to an existing regular local file MUST be detected as a local document source.
- Relative and absolute paths MAY be accepted for reading, but generated artifacts, rows, summaries, and applied state MUST NOT store the absolute local path.
- Existing `.pdf` source IDs and namespaces MUST remain:
  - `source_id`: `pdf-<filename-slug>-<sha16>`;
  - `namespace_candidate`: `pdf-<filename-slug>-<sha16>-v1`;
  - source/base identity: `pdf://<source_id>`.
- Non-PDF source IDs and namespaces MUST be deterministic from extension, filename, and SHA-256 hash of file bytes:
  - `source_id`: `file-<ext>-<filename-slug>-<sha16>`;
  - `namespace_candidate`: `file-<ext>-<filename-slug>-<sha16>-v1`;
  - source/base identity: `file://<source_id>`.
- Generated citation URLs MUST identify the document, not the local filesystem path:
  - PDF: `pdf://<source_id>/<url-encoded-filename>`;
  - non-PDF: `file://<source_id>/<url-encoded-filename>`.

### CLI contract

- `buoy plan <path-to-supported-file>` MUST create a local plan for the file.
- `buoy crawl --base-url <path-to-supported-file>` MAY continue to work through the existing source argument for compatibility.
- CLI help SHOULD describe the source argument as a URL/path, not only a base URL.
- `--namespace` MUST still override the deterministic namespace candidate.
- Existing website URL, GitHub repository URL, and local PDF behavior MUST remain backward-compatible.

### Extraction

- Extraction MUST use Microsoft MarkItDown via its normal local conversion path.
- Each local document source MUST produce one generated Markdown document for the whole file.
- If MarkItDown extracts no non-whitespace Markdown, the command MUST fail clearly with an error explaining that no text was extracted for the file and that OCR/image/audio/cloud extraction is outside v1 scope.
- Dependency errors MUST fail clearly and identify the MarkItDown extra or local conversion support that is missing where practical.

### Artifacts and metadata

Generated Markdown frontmatter for a local document MUST include at least:

- `url`: synthetic document URL;
- `title`: original filename;
- `status`: `200`;
- `content_type`: a best-effort MIME/content type;
- `source_kind`: `pdf` for PDFs and `local_file` for non-PDF files;
- `file_filename`: original filename only;
- `file_extension`: extension without dot;
- `file_sha256`: full SHA-256 hash of file bytes;
- `file_source_id`: deterministic source ID;
- `fetcher`: `markitdown`;
- `crawl_timestamp` for local generation bookkeeping.

PDF artifacts MAY also preserve existing `pdf_filename`, `pdf_sha256`, and `pdf_source_id` fields for backward compatibility.

Plan, manifest, chunks JSONL, summaries, rows, and applied state MUST preserve local-file metadata without storing absolute paths.

### Local-only and live-write guardrails

- `crawl` and `plan` for local documents MUST remain local-only with respect to turbopuffer: no credentials, embeddings, namespace creation, row writes, stale deletion, or live turbopuffer calls.
- `apply` and `apply --approve` MUST behave exactly like existing source plans: preflight by default, live embedding/upsert only with explicit `--approve`, and stale deletion only with existing explicit deletion guardrails.

## Explicit exclusions

- Directories and multi-file batches.
- Archive traversal, including `.zip`.
- Images and OCR/image captioning.
- Audio/video transcription.
- YouTube or remote URL ingestion as local document sources.
- Azure Document Intelligence, Azure Content Understanding, cloud APIs, MarkItDown plugins, or LLM vision/captioning.
- Page, slide, sheet, cell, line, or notebook-cell citations.
- Password-protected/encrypted file handling beyond clear failure.

## Acceptance criteria

- `buoy plan ./example.docx --json` succeeds for a supported text-bearing file and reports `source_kind: local_file`, one generated Markdown document, generated chunks, `namespace_candidate` matching `file-docx-<filename-slug>-<sha16>-v1`, and no turbopuffer API calls.
- `buoy crawl --base-url ./example.csv --json` produces the same local document corpus shape without live calls.
- Existing PDF plans still use `pdf-<filename-slug>-<sha16>-v1`, not `file-pdf-...`.
- Generated artifacts and rows contain filename, extension, hash, source ID, and source kind but not the absolute source filepath.
- Empty MarkItDown extraction fails clearly without writing a misleading successful plan.
- Unsupported local extensions fail clearly as unsupported sources.
- Existing website/GitHub/PDF source detection, namespace defaults, plan/apply, and tests continue to pass.
