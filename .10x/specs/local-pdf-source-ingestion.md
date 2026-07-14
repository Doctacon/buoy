Status: active
Created: 2026-07-08
Updated: 2026-07-08

# Local PDF Source Ingestion

## Purpose and scope

`buoy` MUST support a single local PDF filepath as a first-class source for the existing local-only `crawl`/`plan` workflow and the existing explicit `apply` workflow.

This specification governs local PDF acquisition and artifact identity. Existing website and GitHub repository behavior remain in scope only insofar as they must not regress.

## Behavior

### Source detection and identity

- A path ending in `.pdf` or `.PDF` that points to an existing regular local file MUST be detected as `source_kind: pdf`.
- Relative and absolute PDF paths MAY be accepted for reading, but generated artifacts, rows, and summaries MUST NOT store the absolute local path.
- The source ID MUST be deterministic from the PDF filename and SHA-256 hash of the file bytes:
  - `source_id`: `pdf-<safe-filename-slug>-<sha16>`
  - `namespace_candidate`: `pdf-<safe-filename-slug>-<sha16>-v1`
- The source/base identity used in plan/apply state MUST be a synthetic, non-path source URI such as `pdf://<source_id>`.
- Generated chunk/page citation URLs MUST identify the document, not the local filesystem path, e.g. `pdf://<source_id>/<filename>`.

### CLI contract

- `buoy plan <path-to-file.pdf>` MUST create a local plan for the PDF.
- `buoy crawl --base-url <path-to-file.pdf>` MAY continue to work through the existing crawl source argument for compatibility, but CLI help SHOULD describe the argument as a source URL/path rather than only a base URL.
- `--namespace` MUST still override the deterministic PDF namespace candidate.
- Existing website URL and GitHub repository URL usage MUST remain backward-compatible.

### Extraction

- PDF extraction MUST use Microsoft MarkItDown via its local conversion path, as decided in `.10x/decisions/local-pdf-ingestion-uses-markitdown.md`.
- The built-in/local MarkItDown PDF conversion path MUST be used without OCR plugins, cloud APIs, LLM vision, or page-splitting wrappers.
- A PDF source MUST produce one generated Markdown page for the whole document.
- If MarkItDown extracts no non-whitespace Markdown, the command MUST fail clearly with an error explaining that no text was extracted and OCR/scanned PDFs are out of v1 scope.

### Artifacts and metadata

Generated Markdown frontmatter for a PDF MUST include at least:

- `url`: synthetic document URL;
- `title`: original PDF filename;
- `status`: `200`;
- `content_type`: `application/pdf`;
- `source_kind`: `pdf`;
- `pdf_filename`: original filename only;
- `pdf_sha256`: full SHA-256 hash of the file bytes;
- `fetcher` or converter marker identifying MarkItDown;
- `crawl_timestamp` for local generation bookkeeping.

Plan, manifest, chunks JSONL, and summary output MUST preserve PDF source metadata without storing absolute paths.

### Local-only and live-write guardrails

- `crawl` and `plan` for PDFs MUST remain local-only with respect to turbopuffer: no credentials, embeddings, namespace creation, row writes, stale deletion, or live turbopuffer calls.
- `apply` and `apply --approve` MUST behave exactly like existing source plans: preflight by default, live embedding/upsert only with explicit `--approve`, and stale deletion only with existing explicit deletion guardrails.

## Explicit exclusions

- Page-number citations or page-preserving chunks.
- OCR/scanned-image PDF support.
- Directory ingestion or multi-PDF batch ingestion.
- Password-protected/encrypted PDF handling beyond clear failure.
- Remote PDF URLs as a special source type.
- MarkItDown plugin enablement, Azure services, LLM image captioning, or cloud document extraction.

## Acceptance criteria

- `buoy plan ./example.pdf --json` succeeds for a text PDF and reports `source_kind: pdf`, one generated Markdown page, generated chunks, `namespace_candidate` matching `pdf-<filename-slug>-<sha16>-v1`, and no turbopuffer API calls.
- PDF plan artifacts contain the filename and hash but not the absolute local filepath.
- `buoy crawl --base-url ./example.pdf --json` produces the same local PDF corpus shape without live calls.
- Empty/scanned PDF extraction fails clearly without writing a misleading successful plan.
- Existing website/GitHub URL detection, namespace defaults, and tests continue to pass.
