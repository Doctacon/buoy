from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from buoy_search.chunker import (
    approximate_token_count,
    chunk_document,
    derive_doc_kind_and_tags,
    parse_markdown_file,
    process_corpus,
)


class MarkdownChunkerTests(unittest.TestCase):
    def test_frontmatter_normalization_and_doc_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            page = corpus / "page.md"
            page.write_text(
                "---\n"
                "url: \"https://example.com/blog/example-post/\"\n"
                "title: \"Example Post\"\n"
                "---\n\n"
                "[Skip to content](https://example.com/blog/example-post/#content)\n\n"
                "In this article\n\n"
                "Overview\n"
                "## Overview\n"
                "Actual body text about engineering metrics.\n",
                encoding="utf-8",
            )

            document = parse_markdown_file(page, corpus)
            doc_kind, tags = derive_doc_kind_and_tags(document.url, document.relative_path)

            self.assertEqual(document.url, "https://example.com/blog/example-post/")
            self.assertEqual(document.title, "Example Post")
            self.assertNotIn("Skip to content", document.normalized_body)
            self.assertNotIn("In this article", document.normalized_body)
            self.assertNotIn("Overview\n## Overview", document.normalized_body)
            self.assertEqual(doc_kind, "blog")
            self.assertIn("example-post", tags)

    def test_chunking_is_heading_aware_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            page = corpus / "library.md"
            page.write_text(
                "---\nurl: https://example.com/docs/fetchers/\ntitle: Fetchers\n---\n\n"
                "Intro sentence for the page. Another intro sentence.\n\n"
                "## Static Fetching\n"
                + " ".join(f"Fetcher sentence {idx}." for idx in range(80))
                + "\n\n## Browser Fetching\nDynamic pages may need browser rendering.\n",
                encoding="utf-8",
            )

            document = parse_markdown_file(page, corpus)
            chunks_a = chunk_document(document, target_tokens=40, overlap_sentences=2)
            chunks_b = chunk_document(document, target_tokens=40, overlap_sentences=2)

            self.assertGreater(len(chunks_a), 2)
            self.assertEqual([chunk.id for chunk in chunks_a], [chunk.id for chunk in chunks_b])
            self.assertTrue(all(len(chunk.id) <= 64 for chunk in chunks_a))
            self.assertIn("Static Fetching", {chunk.section_path for chunk in chunks_a})
            self.assertIn("Title: Fetchers", chunks_a[0].embedding_text)
            self.assertTrue(all(approximate_token_count(chunk.content) <= 60 for chunk in chunks_a))

    def test_process_corpus_handles_empty_files_and_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            (corpus / "empty.md").write_text("---\ntitle: Empty\n---\n\n", encoding="utf-8")
            (corpus / "full.md").write_text(
                "---\nurl: https://example.com/docs/test/\ntitle: Full\n---\n\n"
                "## Section\nUseful text. More useful text.\n",
                encoding="utf-8",
            )

            plan = process_corpus(corpus, limit_chunks=1)

            self.assertEqual(plan.files_discovered, 2)
            self.assertEqual(plan.stats.files_seen, 2)
            self.assertEqual(plan.stats.files_skipped_empty, 1)
            self.assertEqual(plan.stats.files_error, 0)
            self.assertEqual(plan.stats.chunks_generated, 1)
            self.assertTrue(plan.limit_reached or plan.stats.chunks_generated == 1)


if __name__ == "__main__":
    unittest.main()
