from __future__ import annotations

import ast
from unittest.mock import patch
import unittest

from buoy_search.indexing.repo_syntax_chunking import (
    RepoSyntaxChunkingError,
    chunk_source,
    lf_physical_lines,
    source_payload,
)


class RepoSyntaxChunkingTests(unittest.TestCase):
    def test_lf_coordinates_preserve_blank_and_form_feed_without_terminal_line(self) -> None:
        source = "first\n\n\fform-feed\nlast"
        self.assertEqual(lf_physical_lines(source), ("first", "", "\fform-feed", "last"))
        self.assertEqual(lf_physical_lines(source + "\n"), ("first", "", "\fform-feed", "last"))
        with self.assertRaisesRegex(RepoSyntaxChunkingError, "carriage return"):
            lf_physical_lines("first\rlast")

    def test_fixed_arm_emits_all_intersecting_name_only_ancestor_chains(self) -> None:
        source = "\n".join(
            [
                "class Client:",
                "    def request(self):",
                "        def decode():",
                "            return 1",
                "        return decode()",
            ]
            + ["        value = 1"] * 76
        )

        result = chunk_source(source, "client.py", "python", "fixed-80-python-breadcrumbs")

        self.assertEqual([(item.start, item.end) for item in result.ranges], [(1, 80), (81, 81)])
        self.assertEqual(
            result.ranges[0].breadcrumbs,
            ("Client", "Client > request", "Client > request > decode"),
        )
        self.assertEqual(result.ranges[1].breadcrumbs, ("Client", "Client > request"))
        self.assertEqual(
            tuple(
                line
                for item in result.ranges
                for line in source_payload(result, item).split("\n")
            ),
            result.lines,
        )

    def test_ast_arm_uses_tokenizer_owned_multiline_decorators_and_nested_ownership(self) -> None:
        source = "\n".join(
            [
                "class Client:",
                "    @first",
                "    # between decorators",
                "    @(",
                "        left",
                "        @ right",
                "    )  # final decorator row",
                "    # between decorator and definition",
                "    async def request(self):",
                "        before = 1",
                "        @inner(",
                "            option=True,",
                "        )",
                "        def decode():",
                "            return 1",
                "        return decode()",
            ]
        )

        result = chunk_source(source, "client.py", "python", "python-ast")

        self.assertEqual(
            [(item.start, item.end, item.breadcrumbs) for item in result.ranges],
            [
                (1, 1, ("Client",)),
                (2, 10, ("Client > request",)),
                (11, 15, ("Client > request > decode",)),
                (16, 16, ("Client > request",)),
            ],
        )
        reconstructed = [
            line
            for item in result.ranges
            for line in result.lines[item.start - 1 : item.end]
        ]
        self.assertEqual(tuple(reconstructed), result.lines)

    def test_ast_arm_assigns_outside_symbol_trivia_forward_except_at_eof(self) -> None:
        source = "\n".join(
            [
                "# module header",
                "module_value = 1",
                "# attached forward",
                "",
                "def first():",
                "    return 1",
                "# attached to next",
                "",
                "def second():",
                "    return 2",
                "# attached backward at EOF",
                "",
            ]
        )

        result = chunk_source(source, "owners.py", "python", "python-ast")

        self.assertEqual(
            [(item.start, item.end, item.breadcrumbs) for item in result.ranges],
            [
                (1, 2, ()),
                (3, 6, ("first",)),
                (7, 11, ("second",)),
            ],
        )

    def test_ast_arm_keeps_all_trivia_file_as_one_module_region(self) -> None:
        result = chunk_source("# comment\n\n\f# second", "trivia.py", "python", "python-ast")
        self.assertEqual([(item.start, item.end, item.breadcrumbs) for item in result.ranges], [(1, 3, ())])

    def test_long_ownership_region_subdivides_80_80_1_without_overlap(self) -> None:
        source = "\n".join(["def long_function():"] + ["    value = 1"] * 160)

        result = chunk_source(source, "long.py", "python", "python-ast")

        self.assertEqual([(item.start, item.end) for item in result.ranges], [(1, 80), (81, 160), (161, 161)])
        self.assertTrue(all(item.breadcrumbs == ("long_function",) for item in result.ranges))

    def test_parse_and_non_python_fallbacks_are_whole_file_fixed_without_breadcrumbs(self) -> None:
        malformed = chunk_source("def broken(:\n    pass\n", "broken.py", "python", "python-ast")
        javascript = chunk_source("\n".join(["const value = 1;"] * 81), "app.js", "javascript", "fixed-80-python-breadcrumbs")

        self.assertEqual(malformed.fallback, "python-parse")
        self.assertEqual([(item.start, item.end, item.breadcrumbs) for item in malformed.ranges], [(1, 2, ())])
        self.assertEqual(javascript.fallback, "non-python")
        self.assertEqual([(item.start, item.end, item.breadcrumbs) for item in javascript.ranges], [(1, 80, ()), (81, 81, ())])

    def test_unexpected_tokenizer_failure_is_not_downgraded(self) -> None:
        with patch(
            "buoy_search.indexing.repo_syntax_chunking.tokenize.generate_tokens",
            side_effect=RuntimeError("unexpected tokenizer failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "unexpected tokenizer failure"):
                chunk_source("def valid():\n    pass\n", "valid.py", "python", "python-ast")

    def test_missing_required_ast_position_fails_closed(self) -> None:
        tree = ast.Module(body=[ast.FunctionDef(name="broken", args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]), body=[ast.Pass()], decorator_list=[])], type_ignores=[])
        with patch("buoy_search.indexing.repo_syntax_chunking.ast.parse", return_value=tree):
            with self.assertRaisesRegex(RepoSyntaxChunkingError, "invalid lineno"):
                chunk_source("def valid():\n    pass\n", "valid.py", "python", "python-ast")


if __name__ == "__main__":
    unittest.main()
