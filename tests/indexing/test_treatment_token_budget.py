from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from buoy_search.indexing.repo_syntax_chunking import SourceRange
from buoy_search.indexing.treatment_token_budget import (
    MAX_EMBEDDING_TOKENS,
    TOKENIZER_FILES_SHA256,
    TOKENIZER_IMPLEMENTATION,
    TreatmentTokenBudgetError,
    UnsplittableSourceLine,
    bundled_tokenizer_snapshot,
    exact_token_count,
    exhaustive_maximal_subdivision,
    load_pinned_tokenizer,
    tokenizer_files_identity,
)


class TreatmentTokenBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokenizer = load_pinned_tokenizer()

    def test_bundled_offline_tokenizer_has_exact_identity_class_lock_and_golden_counts(self) -> None:
        tokenizer = self.tokenizer
        self.assertEqual(tokenizer_files_identity(bundled_tokenizer_snapshot()), TOKENIZER_FILES_SHA256)
        self.assertEqual(
            f"{type(tokenizer).__module__}.{type(tokenizer).__name__}",
            TOKENIZER_IMPLEMENTATION,
        )
        self.assertEqual(tokenizer.model_max_length, MAX_EMBEDDING_TOKENS)
        golden_payloads = {
            "Title: src/app.py\n\nSection: src/app.py > Lines 1-1\n\n```python\nvalue = 1\n```": 35,
            "Title: src/app.py\n\nSection: src/app.py > Lines 9-10\n\nSymbol breadcrumbs: App > run\n\n```python\nvalue = 1\nvalue = 2\n```": 47,
            "Title: a`b.py\n\nSection: a`b.py > Lines 1-1\n\n````python\nx = \"```\"\n````": 39,
        }
        self.assertEqual(
            {payload: exact_token_count(tokenizer, payload) for payload in golden_payloads},
            golden_payloads,
        )

    def test_added_tokens_file_cannot_preserve_identity_load_or_change_counts(self) -> None:
        payload = "wholeword"
        committed_count = exact_token_count(self.tokenizer, payload)
        self.assertEqual(committed_count, 4)
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / bundled_tokenizer_snapshot().name
            shutil.copytree(bundled_tokenizer_snapshot(), mutated)
            (mutated / "added_tokens.json").write_text(
                '{"wholeword": 30522}\n', encoding="utf-8"
            )

            from transformers import BertTokenizer

            unguarded = BertTokenizer.from_pretrained(mutated, local_files_only=True)
            self.assertEqual(exact_token_count(unguarded, payload), 3)
            with self.assertRaisesRegex(TreatmentTokenBudgetError, "file-set identity mismatch"):
                tokenizer_files_identity(mutated)
            with patch("transformers.BertTokenizer.from_pretrained") as from_pretrained:
                with self.assertRaisesRegex(
                    TreatmentTokenBudgetError, "file-set identity mismatch"
                ):
                    load_pinned_tokenizer(mutated)
                from_pretrained.assert_not_called()

        self.assertEqual(exact_token_count(self.tokenizer, payload), committed_count)
        self.assertEqual(
            tokenizer_files_identity(bundled_tokenizer_snapshot()), TOKENIZER_FILES_SHA256
        )

    def test_snapshot_rejects_extra_files_subdirectories_and_symlink_entries(self) -> None:
        for mutation in ("extra-file", "subdirectory", "expected-symlink"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                mutated = Path(tmp) / bundled_tokenizer_snapshot().name
                shutil.copytree(bundled_tokenizer_snapshot(), mutated)
                if mutation == "extra-file":
                    (mutated / "unexpected.txt").write_text("extra\n", encoding="utf-8")
                elif mutation == "subdirectory":
                    (mutated / "nested").mkdir()
                else:
                    (mutated / "vocab.txt").unlink()
                    (mutated / "vocab.txt").symlink_to(
                        bundled_tokenizer_snapshot() / "vocab.txt"
                    )

                with self.assertRaisesRegex(
                    TreatmentTokenBudgetError, "file-set identity mismatch"
                ):
                    tokenizer_files_identity(mutated)
                with patch("transformers.BertTokenizer.from_pretrained") as from_pretrained:
                    with self.assertRaisesRegex(
                        TreatmentTokenBudgetError, "file-set identity mismatch"
                    ):
                        load_pinned_tokenizer(mutated)
                    from_pretrained.assert_not_called()

    def test_exact_count_forces_special_tokens_and_disables_truncation_and_padding(self) -> None:
        class RecordingTokenizer:
            model_max_length = 512

            def __call__(self, text: str, **kwargs: object) -> dict[str, object]:
                self.text = text
                self.kwargs = kwargs
                return {"length": [513]}

        tokenizer = RecordingTokenizer()
        self.assertEqual(exact_token_count(tokenizer, "complete payload"), 513)
        self.assertEqual(tokenizer.text, "complete payload")
        self.assertEqual(
            tokenizer.kwargs,
            {
                "add_special_tokens": True,
                "truncation": False,
                "padding": False,
                "return_length": True,
            },
        )

    def test_loader_rejects_package_revision_file_and_maximum_mutations(self) -> None:
        with patch("buoy_search.indexing.treatment_token_budget.version", return_value="5.12.0"):
            with self.assertRaisesRegex(TreatmentTokenBudgetError, "package mismatch"):
                load_pinned_tokenizer()

        with tempfile.TemporaryDirectory() as tmp:
            wrong_revision = Path(tmp) / "wrong-revision"
            shutil.copytree(bundled_tokenizer_snapshot(), wrong_revision)
            with self.assertRaisesRegex(TreatmentTokenBudgetError, "revision mismatch"):
                load_pinned_tokenizer(wrong_revision)

            mutated = Path(tmp) / bundled_tokenizer_snapshot().name
            shutil.copytree(bundled_tokenizer_snapshot(), mutated)
            with (mutated / "vocab.txt").open("a", encoding="utf-8") as handle:
                handle.write("mutation\n")
            with self.assertRaisesRegex(TreatmentTokenBudgetError, "file-set identity mismatch"):
                load_pinned_tokenizer(mutated)

        wrong_implementation = type("WrongTokenizer", (), {"model_max_length": 512})()
        with patch("transformers.BertTokenizer.from_pretrained", return_value=wrong_implementation):
            with self.assertRaisesRegex(TreatmentTokenBudgetError, "implementation mismatch"):
                load_pinned_tokenizer()

        wrong_maximum_type = type(
            "BertTokenizer",
            (),
            {"__module__": "transformers.models.bert.tokenization_bert", "model_max_length": 511},
        )
        with patch("transformers.BertTokenizer.from_pretrained", return_value=wrong_maximum_type()):
            with self.assertRaisesRegex(TreatmentTokenBudgetError, "model maximum mismatch"):
                load_pinned_tokenizer()

    def test_exhaustive_selection_crosses_non_monotone_failure_and_chooses_farthest_fit(self) -> None:
        visited: list[tuple[int, int]] = []
        counts = {(1, 1): 100, (1, 2): 600, (1, 3): 500, (1, 4): 700, (4, 4): 100}

        def render(candidate: SourceRange) -> str:
            visited.append((candidate.start, candidate.end))
            return f"{candidate.start}-{candidate.end}"

        children = exhaustive_maximal_subdivision(
            SourceRange(1, 4, ("owner",)),
            render,
            lambda value: counts[tuple(map(int, value.split("-")))],
        )

        self.assertEqual(children, (SourceRange(1, 3, ("owner",)), SourceRange(4, 4, ("owner",))))
        self.assertEqual(visited, [(1, 1), (1, 2), (1, 3), (1, 4), (4, 4)])

    def test_randomized_ranges_are_adjacent_reconstruct_parent_and_are_maximal(self) -> None:
        randomizer = random.Random(20260720)
        for _case in range(200):
            length = randomizer.randint(1, 80)
            counts = {
                (start, end): randomizer.randint(1, 700)
                for start in range(1, length + 1)
                for end in range(start, length + 1)
            }
            for line in range(1, length + 1):
                counts[(line, line)] = randomizer.randint(1, 512)
            children = exhaustive_maximal_subdivision(
                SourceRange(1, length, ("exact breadcrumb",)),
                lambda item: f"{item.start}:{item.end}",
                lambda value: counts[tuple(map(int, value.split(":")))],
            )
            cursor = 1
            for child in children:
                self.assertEqual(child.start, cursor)
                self.assertEqual(child.breadcrumbs, ("exact breadcrumb",))
                self.assertLessEqual(counts[(child.start, child.end)], 512)
                self.assertFalse(
                    any(
                        counts[(child.start, later)] <= 512
                        for later in range(child.end + 1, length + 1)
                    )
                )
                cursor = child.end + 1
            self.assertEqual(cursor, length + 1)

    def test_exact_513_token_complete_one_line_payload_is_unsplittable(self) -> None:
        payload = (
            "Title: huge.py\n\nSection: huge.py > Lines 1-1\n\n```python\n"
            + " ".join(["alpha"] * 487)
            + "\n```"
        )
        self.assertEqual(exact_token_count(self.tokenizer, payload), 513)
        with self.assertRaises(UnsplittableSourceLine) as raised:
            exhaustive_maximal_subdivision(
                SourceRange(1, 1, ()),
                lambda _candidate: payload,
                lambda text: exact_token_count(self.tokenizer, text),
            )
        self.assertEqual((raised.exception.line, raised.exception.token_count), (1, 513))


if __name__ == "__main__":
    unittest.main()
