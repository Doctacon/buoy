"""Markdown ingestion, chunking, embedding, and turbopuffer writer helpers.

Parsing and chunking are local-only and do not load embedding models, read
credentials, or contact external APIs. Live writes are performed by the explicit
plan/apply path, which injects credentials at the call site.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re
from typing import Iterable, Iterator, Sequence, TypeVar
from urllib.parse import urlparse

from turbo_search.config import RuntimeConfig

VECTOR_DIMENSIONS = 384
DEFAULT_TARGET_TOKENS = 300
DEFAULT_OVERLAP_SENTENCES = 2

T = TypeVar("T")

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*|[^\s]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\[])")
FRONTMATTER_BOUNDARY_RE = re.compile(r"^---\s*$")

OBVIOUS_CHROME_EXACT = {
    "in this article",
    "skip to content",
    "table of contents",
}
OBVIOUS_CHROME_PATTERNS = [
    re.compile(r"^\[Skip to content\]\([^)]*\)\s*$", re.IGNORECASE),
    re.compile(r"^New episode: .*utm_content=topbar_cta", re.IGNORECASE),
]
KNOWN_DOC_KINDS = {
    "blog",
    "library",
    "integrations",
    "integration",
    "platform",
    "solutions",
    "solution",
    "resources",
    "events-and-webinars",
    "newsroom",
    "customers",
    "customer",
    "thank-you",
}
DOC_KIND_ALIASES = {
    "integration": "integrations",
    "solution": "solutions",
    "customer": "customers",
}

TURBOPUFFER_SCHEMA = {
    "vector": {"type": f"[{VECTOR_DIMENSIONS}]f16", "ann": True},
    "content": {"type": "string", "full_text_search": True, "filterable": False},
    "title": {"type": "string", "full_text_search": True},
    "url": {"type": "string"},
    "path": {"type": "string"},
    "section_path": {"type": "string", "full_text_search": True},
    "chunk_index": {"type": "uint"},
    "doc_kind": {"type": "string"},
    "tags": {"type": "[]string"},
    "source_hash": {"type": "string"},
}


@dataclass(frozen=True)
class MarkdownDocument:
    """Parsed Markdown source page."""

    path: Path
    relative_path: str
    title: str
    url: str
    metadata: dict[str, str]
    body: str
    normalized_body: str
    source_hash: str


@dataclass(frozen=True)
class MarkdownChunk:
    """One retrieval/indexing unit derived from a Markdown page."""

    id: str
    content: str
    title: str
    url: str
    path: str
    section_path: str
    chunk_index: int
    doc_kind: str
    tags: list[str]
    source_hash: str

    @property
    def embedding_text(self) -> str:
        """Text sent to the embedding model, with citation context included."""

        context: list[str] = []
        if self.title:
            context.append(f"Title: {self.title}")
        if self.section_path:
            context.append(f"Section: {self.section_path}")
        context.append(self.content)
        return "\n\n".join(part for part in context if part.strip())


@dataclass
class FileError:
    path: str
    message: str


@dataclass
class IndexingStats:
    files_seen: int = 0
    files_skipped_empty: int = 0
    files_error: int = 0
    chunks_generated: int = 0
    rows_written: int = 0
    errors: list[FileError] = field(default_factory=list)


@dataclass
class IndexingPlan:
    corpus_dir: Path
    files_discovered: int
    chunks: list[MarkdownChunk]
    stats: IndexingStats
    limit_reached: bool = False


def discover_markdown_files(corpus_dir: Path) -> list[Path]:
    """Return all Markdown files under ``corpus_dir`` in deterministic order."""

    return sorted(path for path in corpus_dir.rglob("*.md") if path.is_file())


def parse_markdown_file(path: Path, corpus_dir: Path) -> MarkdownDocument:
    """Parse frontmatter and normalize a Markdown file."""

    raw = path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(raw)
    normalized_body = normalize_markdown_body(body)
    source_hash = sha256_text(normalized_body)
    relative_path = str(path.relative_to(corpus_dir))
    title = metadata.get("title") or title_from_path(path)
    url = metadata.get("url", "")
    return MarkdownDocument(
        path=path,
        relative_path=relative_path,
        title=title,
        url=url,
        metadata=metadata,
        body=body,
        normalized_body=normalized_body,
        source_hash=source_hash,
    )


def split_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """Split simple YAML frontmatter from a Markdown document.

    The Jellyfish exports use scalar ``url`` and ``title`` fields. This parser is
    intentionally small and dependency-free for dry-run validation; unknown or
    nested frontmatter lines are ignored rather than treated as fatal.
    """

    lines = raw.splitlines()
    if not lines or not FRONTMATTER_BOUNDARY_RE.match(lines[0]):
        return {}, raw

    end_index: int | None = None
    for index in range(1, len(lines)):
        if FRONTMATTER_BOUNDARY_RE.match(lines[index]):
            end_index = index
            break
    if end_index is None:
        return {}, raw

    metadata = parse_scalar_frontmatter(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    if raw.endswith("\n"):
        body += "\n"
    return metadata, body


def parse_scalar_frontmatter(lines: Sequence[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_-]*$", key):
            continue
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        metadata[key] = value
    return metadata


def normalize_markdown_body(body: str) -> str:
    """Remove obvious repeated site chrome while preserving page content."""

    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    filtered: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        lowered = stripped.lower()
        if not stripped:
            filtered.append("")
            index += 1
            continue
        if lowered in OBVIOUS_CHROME_EXACT or any(pattern.match(stripped) for pattern in OBVIOUS_CHROME_PATTERNS):
            index += 1
            continue
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        next_heading = HEADING_RE.match(next_line)
        if next_heading and normalize_for_comparison(stripped) == normalize_for_comparison(
            clean_markdown_inline(next_heading.group(2))
        ):
            index += 1
            continue
        filtered.append(line)
        index += 1

    collapsed: list[str] = []
    blank_count = 0
    for line in filtered:
        if line.strip():
            collapsed.append(line.rstrip())
            blank_count = 0
        else:
            blank_count += 1
            if blank_count <= 2:
                collapsed.append("")
    return "\n".join(collapsed).strip()


def chunk_document(
    document: MarkdownDocument,
    *,
    target_tokens: int = DEFAULT_TARGET_TOKENS,
    overlap_sentences: int = DEFAULT_OVERLAP_SENTENCES,
) -> list[MarkdownChunk]:
    """Split a parsed document into heading-aware chunks."""

    if not document.normalized_body.strip():
        return []

    chunks: list[MarkdownChunk] = []
    doc_kind, tags = derive_doc_kind_and_tags(document.url, document.relative_path)
    source_sections = iter_sections(document.normalized_body)
    for section_path, section_text in source_sections:
        for content in split_section_into_chunks(
            section_text,
            target_tokens=target_tokens,
            overlap_sentences=overlap_sentences,
        ):
            chunk_index = len(chunks)
            chunk_id = deterministic_chunk_id(
                document.relative_path,
                chunk_index,
                document.source_hash,
                content,
            )
            chunks.append(
                MarkdownChunk(
                    id=chunk_id,
                    content=content,
                    title=document.title,
                    url=document.url,
                    path=document.relative_path,
                    section_path=section_path,
                    chunk_index=chunk_index,
                    doc_kind=doc_kind,
                    tags=tags,
                    source_hash=document.source_hash,
                )
            )
    return chunks


def iter_sections(markdown: str) -> Iterator[tuple[str, str]]:
    """Yield ``(section_path, section_text)`` pairs from Markdown headings."""

    heading_stack: list[tuple[int, str]] = []
    current_lines: list[str] = []
    current_path = ""
    in_code_fence = False

    def flush() -> Iterator[tuple[str, str]]:
        text = "\n".join(current_lines).strip()
        if text:
            yield current_path, text

    for line in markdown.splitlines():
        if line.strip().startswith("```") or line.strip().startswith("~~~"):
            in_code_fence = not in_code_fence
            current_lines.append(line)
            continue
        heading_match = HEADING_RE.match(line) if not in_code_fence else None
        if heading_match:
            yield from flush()
            current_lines = []
            level = len(heading_match.group(1))
            heading = clean_markdown_inline(heading_match.group(2))
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, heading))
            current_path = " > ".join(item[1] for item in heading_stack)
            continue
        current_lines.append(line)
    yield from flush()


def split_section_into_chunks(
    section_text: str,
    *,
    target_tokens: int,
    overlap_sentences: int,
) -> list[str]:
    units = split_markdown_units(section_text)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    overlap_prefix = ""

    for unit in units:
        pieces = split_oversized_unit(unit, target_tokens)
        for piece in pieces:
            piece_tokens = approximate_token_count(piece)
            if current and current_tokens + piece_tokens > target_tokens:
                emitted = "\n\n".join(current).strip()
                if emitted:
                    chunks.append(emitted)
                overlap_prefix = sentence_overlap(emitted, overlap_sentences)
                current = [overlap_prefix] if overlap_prefix else []
                current_tokens = approximate_token_count(overlap_prefix) if overlap_prefix else 0
            current.append(piece)
            current_tokens += piece_tokens

    emitted = "\n\n".join(current).strip()
    if emitted:
        chunks.append(emitted)
    return chunks


def split_markdown_units(section_text: str) -> list[str]:
    """Split section text into paragraphs/lists/code blocks without headings."""

    units: list[str] = []
    current: list[str] = []
    in_code_fence = False

    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            current.append(line)
            in_code_fence = not in_code_fence
            if not in_code_fence:
                units.append("\n".join(current).strip())
                current = []
            continue
        if in_code_fence:
            current.append(line)
            continue
        if stripped:
            current.append(line)
        elif current:
            units.append("\n".join(current).strip())
            current = []
    if current:
        units.append("\n".join(current).strip())
    return [unit for unit in units if unit]


def split_oversized_unit(unit: str, target_tokens: int) -> list[str]:
    if approximate_token_count(unit) <= target_tokens:
        return [unit]
    sentences = split_sentences(unit)
    pieces: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for sentence in sentences:
        sentence_tokens = approximate_token_count(sentence)
        if current and current_tokens + sentence_tokens > target_tokens:
            pieces.append(" ".join(current).strip())
            current = []
            current_tokens = 0
        if sentence_tokens > target_tokens:
            pieces.extend(split_by_words(sentence, target_tokens))
        else:
            current.append(sentence)
            current_tokens += sentence_tokens
    if current:
        pieces.append(" ".join(current).strip())
    return [piece for piece in pieces if piece]


def split_sentences(text: str) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    return [part.strip() for part in SENTENCE_RE.split(normalized) if part.strip()]


def split_by_words(text: str, target_tokens: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) == 1 and approximate_token_count(text) > target_tokens:
        return split_by_token_spans(text, target_tokens)
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if approximate_token_count(" ".join(current)) >= target_tokens:
            chunks.append(" ".join(current).strip())
            current = []
    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def split_by_token_spans(text: str, target_tokens: int) -> list[str]:
    matches = list(TOKEN_RE.finditer(text))
    chunks: list[str] = []
    for start in range(0, len(matches), target_tokens):
        group = matches[start : start + target_tokens]
        if not group:
            continue
        chunks.append(text[group[0].start() : group[-1].end()].strip())
    return [chunk for chunk in chunks if chunk]


def sentence_overlap(text: str, sentence_count: int, max_tokens: int = 80) -> str:
    if sentence_count <= 0:
        return ""
    sentences = split_sentences(text)
    overlap = " ".join(sentences[-sentence_count:]).strip()
    if approximate_token_count(overlap) <= max_tokens:
        return overlap
    words = overlap.split()
    if len(words) <= 1:
        spans = split_by_token_spans(overlap, max_tokens)
        return spans[-1] if spans else ""
    tail: list[str] = []
    for word in reversed(words):
        candidate = " ".join(reversed([word, *tail]))
        if tail and approximate_token_count(candidate) > max_tokens:
            break
        tail.insert(0, word)
    return " ".join(tail).strip()


def process_corpus(
    corpus_dir: Path,
    *,
    max_files: int | None = None,
    limit_chunks: int | None = None,
    target_tokens: int = DEFAULT_TARGET_TOKENS,
    overlap_sentences: int = DEFAULT_OVERLAP_SENTENCES,
) -> IndexingPlan:
    """Parse and chunk a corpus without embedding or API calls."""

    corpus_dir = corpus_dir.resolve()
    if not corpus_dir.exists():
        raise FileNotFoundError(corpus_dir)
    if not corpus_dir.is_dir():
        raise NotADirectoryError(corpus_dir)
    files = discover_markdown_files(corpus_dir)
    selected_files = files[:max_files] if max_files is not None else files
    stats = IndexingStats()
    chunks: list[MarkdownChunk] = []
    limit_reached = False

    for path in selected_files:
        stats.files_seen += 1
        try:
            document = parse_markdown_file(path, corpus_dir)
            document_chunks = chunk_document(
                document,
                target_tokens=target_tokens,
                overlap_sentences=overlap_sentences,
            )
            if not document_chunks:
                stats.files_skipped_empty += 1
                continue
            for chunk in document_chunks:
                if limit_chunks is not None and len(chunks) >= limit_chunks:
                    limit_reached = True
                    break
                chunks.append(chunk)
            if limit_reached:
                break
        except Exception as exc:  # pragma: no cover - exercised by integration failures.
            stats.files_error += 1
            stats.errors.append(FileError(path=str(path), message=str(exc)))
    stats.chunks_generated = len(chunks)
    return IndexingPlan(
        corpus_dir=corpus_dir,
        files_discovered=len(files),
        chunks=chunks,
        stats=stats,
        limit_reached=limit_reached,
    )


def build_row(chunk: MarkdownChunk, vector: Sequence[float]) -> dict[str, object]:
    """Build the turbopuffer row for one embedded chunk."""

    return {
        "id": chunk.id,
        "vector": list(vector),
        "content": chunk.content,
        "title": chunk.title,
        "url": chunk.url,
        "path": chunk.path,
        "section_path": chunk.section_path,
        "chunk_index": chunk.chunk_index,
        "doc_kind": chunk.doc_kind,
        "tags": chunk.tags,
        "source_hash": chunk.source_hash,
    }


class SentenceTransformerEmbedder:
    """Lazy local BGE embedder used only for approved live apply/retrieval paths."""

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on optional install.
            raise RuntimeError(
                "sentence-transformers is required for approved live embedding. Run `uv sync` first."
            ) from exc
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        embeddings = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [embedding.tolist() if hasattr(embedding, "tolist") else list(embedding) for embedding in embeddings]


class TurbopufferWriter:
    """Small wrapper around the turbopuffer SDK write path."""

    def __init__(self, *, config: RuntimeConfig, api_key: str, schema: dict[str, object] | None = None) -> None:
        try:
            import turbopuffer as tpuf
        except ImportError as exc:  # pragma: no cover - depends on optional install.
            raise RuntimeError("turbopuffer is required for approved apply. Run `uv sync` first.") from exc

        self._tpuf = tpuf
        self._schema = schema or TURBOPUFFER_SCHEMA
        self._namespace = self._build_namespace(tpuf, config, api_key)

    @staticmethod
    def _build_namespace(tpuf: object, config: RuntimeConfig, api_key: str) -> object:
        if hasattr(tpuf, "api_key"):
            setattr(tpuf, "api_key", api_key)
        if hasattr(tpuf, "api_base_url"):
            setattr(tpuf, "api_base_url", f"https://{config.region}.turbopuffer.com")
        if hasattr(tpuf, "Turbopuffer"):
            try:
                client = tpuf.Turbopuffer(api_key=api_key, region=config.region)  # type: ignore[attr-defined]
            except TypeError:
                client = tpuf.Turbopuffer(api_key=api_key)  # type: ignore[attr-defined]
            if hasattr(client, "namespace"):
                return client.namespace(config.namespace)
            if hasattr(client, "Namespace"):
                return client.Namespace(config.namespace)
        if hasattr(tpuf, "Namespace"):
            return tpuf.Namespace(config.namespace)  # type: ignore[attr-defined]
        raise RuntimeError("Unsupported turbopuffer SDK: no Namespace constructor found.")

    def upsert_rows(self, rows: Sequence[dict[str, object]]) -> None:
        try:
            self._namespace.write(
                upsert_rows=list(rows),
                schema=self._schema,
                distance_metric="cosine_distance",
            )
        except TypeError:
            # Some SDK versions use ``rows`` for upserts. Keep the fallback local
            # to approved apply so dry-runs never depend on SDK shape.
            self._namespace.write(
                rows=list(rows),
                schema=self._schema,
                distance_metric="cosine_distance",
            )

    def delete_rows(self, row_ids: Sequence[str]) -> None:
        """Delete whole documents by row ID."""

        if not row_ids:
            return
        self._namespace.write(deletes=list(row_ids), distance_metric="cosine_distance")


def batched(items: Sequence[T], batch_size: int) -> Iterator[list[T]]:
    for start in range(0, len(items), batch_size):
        yield list(items[start : start + batch_size])


def deterministic_chunk_id(
    relative_path: str,
    chunk_index: int,
    source_hash: str,
    content: str,
) -> str:
    digest = hashlib.sha256(
        f"{relative_path}\n{chunk_index}\n{source_hash}\n{sha256_text(content)}".encode("utf-8")
    ).hexdigest()[:32]
    return f"jf_{digest}"


def derive_doc_kind_and_tags(url: str, relative_path: str) -> tuple[str, list[str]]:
    path = urlparse(url).path if url else ""
    segments = [slugify(segment) for segment in path.split("/") if slugify(segment)]
    if not segments:
        stem = Path(relative_path).stem
        segments = [slugify(part) for part in re.split(r"[_/]+", stem) if slugify(part)]
    doc_kind = "page"
    for segment in segments:
        candidate = DOC_KIND_ALIASES.get(segment, segment)
        if candidate in KNOWN_DOC_KINDS:
            doc_kind = candidate
            break
    tags = unique_preserving_order([doc_kind, *segments[:4]])
    return doc_kind, tags


def clean_markdown_inline(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`~]", "", text)
    return " ".join(text.split()).strip()


def normalize_for_comparison(text: str) -> str:
    cleaned = clean_markdown_inline(text).lower()
    return re.sub(r"[^a-z0-9]+", " ", cleaned).strip()


def approximate_token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def title_from_path(path: Path) -> str:
    stem = path.stem.replace("jellyfish.co_", "")
    words = [part for part in re.split(r"[_-]+", stem) if part]
    return " ".join(word.capitalize() for word in words) or path.stem


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\.md$", "", value)
    value = re.sub(r"[^a-z0-9-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


def unique_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result
