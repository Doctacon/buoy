"""Standard-library Python source boundaries for local repository experiments."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import io
import token
import tokenize
from typing import Sequence

MAX_SOURCE_CHUNK_LINES = 80
PYTHON_SYNTAX_ARMS = (
    "fixed-80-python-breadcrumbs",
    "python-ast",
)
REPO_CHUNKING_ARMS = ("current-default", *PYTHON_SYNTAX_ARMS)


class RepoSyntaxChunkingError(RuntimeError):
    """Raised when exact syntax coordinates or coverage cannot be guaranteed."""


@dataclass(frozen=True)
class SourceRange:
    """One exact inclusive LF-coordinate source range."""

    start: int
    end: int
    breadcrumbs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceChunking:
    """Exact source ranges and sanitized fallback classification for one file."""

    lines: tuple[str, ...]
    ranges: tuple[SourceRange, ...]
    fallback: str | None = None


@dataclass(frozen=True)
class _DecoratorStatement:
    start: int
    end: int
    column: int


@dataclass(frozen=True)
class _Symbol:
    name: str
    chain: tuple[str, ...]
    start: int
    end: int
    lexical_order: int


_SYMBOL_TYPES = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def lf_physical_lines(source: str) -> tuple[str, ...]:
    """Return physical lines using only LF as a coordinate boundary."""

    if "\r" in source:
        raise RepoSyntaxChunkingError(
            "repository source contains a bare carriage return after universal-newline acquisition"
        )
    if not source:
        return ()
    lines = source.split("\n")
    if source.endswith("\n"):
        lines.pop()
    return tuple(lines)


def fixed_ranges(line_count: int) -> tuple[SourceRange, ...]:
    return tuple(
        SourceRange(start=start, end=min(start + MAX_SOURCE_CHUNK_LINES - 1, line_count))
        for start in range(1, line_count + 1, MAX_SOURCE_CHUNK_LINES)
    )


def chunk_source(source: str, repo_path: str, language: str, arm: str) -> SourceChunking:
    """Build exact treatment ranges for one repository code file."""

    if arm not in PYTHON_SYNTAX_ARMS:
        raise ValueError(f"unsupported Python syntax chunking arm: {arm}")
    lines = lf_physical_lines(source)
    if not lines:
        return SourceChunking(lines=lines, ranges=())
    if language != "python":
        return SourceChunking(lines=lines, ranges=fixed_ranges(len(lines)), fallback="non-python")

    try:
        tree = ast.parse(
            source,
            filename=repo_path,
            mode="exec",
            type_comments=True,
            feature_version=(3, 11),
        )
    except (SyntaxError, ValueError):
        return SourceChunking(lines=lines, ranges=fixed_ranges(len(lines)), fallback="python-parse")

    symbols = _symbols_with_effective_spans(source, tree, len(lines))
    if arm == "fixed-80-python-breadcrumbs":
        ranges = []
        for source_range in fixed_ranges(len(lines)):
            ordered = sorted(
                (
                    symbol
                    for symbol in symbols
                    if symbol.start <= source_range.end and symbol.end >= source_range.start
                ),
                key=lambda symbol: (symbol.start, symbol.end, symbol.lexical_order),
            )
            breadcrumbs: list[str] = []
            seen: set[str] = set()
            for symbol in ordered:
                breadcrumb = " > ".join(symbol.chain)
                if breadcrumb not in seen:
                    seen.add(breadcrumb)
                    breadcrumbs.append(breadcrumb)
            ranges.append(
                SourceRange(
                    start=source_range.start,
                    end=source_range.end,
                    breadcrumbs=tuple(breadcrumbs),
                )
            )
        result = SourceChunking(lines=lines, ranges=tuple(ranges))
    else:
        result = SourceChunking(lines=lines, ranges=_ownership_ranges(lines, symbols))
    validate_source_chunking(result)
    return result


def validate_source_chunking(chunking: SourceChunking) -> None:
    """Fail unless ranges cover the LF vector exactly once in source order."""

    if not chunking.lines:
        if chunking.ranges:
            raise RepoSyntaxChunkingError("empty source unexpectedly produced source ranges")
        return
    expected_start = 1
    reconstructed: list[str] = []
    for source_range in chunking.ranges:
        if source_range.start != expected_start:
            raise RepoSyntaxChunkingError("source ranges are not adjacent in LF-coordinate order")
        if source_range.end < source_range.start:
            raise RepoSyntaxChunkingError("source range is empty")
        if source_range.end - source_range.start + 1 > MAX_SOURCE_CHUNK_LINES:
            raise RepoSyntaxChunkingError("source range exceeds the 80-line treatment maximum")
        reconstructed.extend(chunking.lines[source_range.start - 1 : source_range.end])
        expected_start = source_range.end + 1
    if expected_start != len(chunking.lines) + 1 or tuple(reconstructed) != chunking.lines:
        raise RepoSyntaxChunkingError("source ranges do not reconstruct the LF physical-line vector exactly")


def source_payload(chunking: SourceChunking, source_range: SourceRange) -> str:
    """Return an unchanged payload for an exact source range."""

    return "\n".join(chunking.lines[source_range.start - 1 : source_range.end])


def _symbols_with_effective_spans(source: str, tree: ast.AST, line_count: int) -> tuple[_Symbol, ...]:
    tokens = tuple(tokenize.generate_tokens(io.StringIO(source).readline))
    decorators = _decorator_statements(tokens)
    symbols: list[_Symbol] = []

    def visit(node: ast.AST, ancestors: tuple[str, ...]) -> None:
        if isinstance(node, _SYMBOL_TYPES):
            name = _required_name(node)
            lineno = _required_position(node, "lineno", line_count)
            end_lineno = _required_position(node, "end_lineno", line_count)
            if end_lineno < lineno:
                raise RepoSyntaxChunkingError("Python symbol end precedes its definition")
            column = _definition_column(tokens, node, lineno)
            decorator_nodes = tuple(node.decorator_list)
            matched = _matching_decorators(
                decorators,
                lines=lf_physical_lines(source),
                definition_line=lineno,
                definition_column=column,
                expected_count=len(decorator_nodes),
            )
            for decorator_node, statement in zip(decorator_nodes, matched):
                decorator_line = _required_position(decorator_node, "lineno", line_count)
                decorator_end = _required_position(decorator_node, "end_lineno", line_count)
                if not (statement.start <= decorator_line <= decorator_end <= statement.end):
                    raise RepoSyntaxChunkingError("AST decorator coordinates disagree with tokenizer-owned span")
            start = matched[0].start if matched else lineno
            chain = (*ancestors, name)
            symbols.append(
                _Symbol(
                    name=name,
                    chain=chain,
                    start=start,
                    end=end_lineno,
                    lexical_order=len(symbols),
                )
            )
            ancestors = chain
        for child in ast.iter_child_nodes(node):
            visit(child, ancestors)

    visit(tree, ())
    _validate_symbol_nesting(symbols)
    return tuple(symbols)


def _required_name(node: ast.AST) -> str:
    name = getattr(node, "name", None)
    if not isinstance(name, str) or not name:
        raise RepoSyntaxChunkingError("Python symbol has no valid name")
    return name


def _required_position(node: ast.AST, attribute: str, line_count: int) -> int:
    value = getattr(node, attribute, None)
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= line_count:
        raise RepoSyntaxChunkingError(f"Python AST node has invalid {attribute}")
    return value


def _definition_column(tokens: Sequence[tokenize.TokenInfo], node: ast.AST, lineno: int) -> int:
    expected = (
        "class"
        if isinstance(node, ast.ClassDef)
        else "async"
        if isinstance(node, ast.AsyncFunctionDef)
        else "def"
    )
    candidates = [
        item
        for item in tokens
        if item.type == token.NAME and item.string == expected and item.start[0] == lineno
    ]
    if not candidates:
        raise RepoSyntaxChunkingError("could not locate Python definition keyword token")
    ast_column = getattr(node, "col_offset", None)
    if not isinstance(ast_column, int) or isinstance(ast_column, bool) or ast_column < 0:
        raise RepoSyntaxChunkingError("Python symbol has invalid col_offset")
    candidate = next((item for item in candidates if item.start[1] == ast_column), None)
    if candidate is None:
        raise RepoSyntaxChunkingError("AST definition column disagrees with tokenizer coordinates")
    return candidate.start[1]


def _decorator_statements(tokens: Sequence[tokenize.TokenInfo]) -> tuple[_DecoratorStatement, ...]:
    statements: list[_DecoratorStatement] = []
    first_non_trivia = True
    active: tokenize.TokenInfo | None = None
    for item in tokens:
        if item.type in {tokenize.ENCODING, tokenize.INDENT, tokenize.DEDENT}:
            continue
        if item.type == tokenize.NEWLINE:
            if active is not None:
                statements.append(
                    _DecoratorStatement(start=active.start[0], end=item.end[0], column=active.start[1])
                )
                active = None
            first_non_trivia = True
            continue
        if item.type in {tokenize.NL, tokenize.COMMENT}:
            continue
        if first_non_trivia and item.type == token.OP and item.string == "@":
            active = item
        first_non_trivia = False
    if active is not None:
        raise RepoSyntaxChunkingError("decorator logical statement has no terminating NEWLINE token")
    return tuple(statements)


def _matching_decorators(
    decorators: Sequence[_DecoratorStatement],
    *,
    lines: Sequence[str],
    definition_line: int,
    definition_column: int,
    expected_count: int,
) -> tuple[_DecoratorStatement, ...]:
    matched: list[_DecoratorStatement] = []
    cursor = definition_line
    for statement in reversed(decorators):
        if statement.end >= cursor or statement.column != definition_column:
            continue
        if not _only_blank_or_comment(lines[statement.end : cursor - 1]):
            continue
        matched.append(statement)
        cursor = statement.start
    matched.reverse()
    if len(matched) != expected_count:
        raise RepoSyntaxChunkingError("tokenizer decorator introducer count disagrees with Python AST")
    return tuple(matched)


def _only_blank_or_comment(lines: Sequence[str]) -> bool:
    return all(not line.strip() or line.lstrip().startswith("#") for line in lines)


def _validate_symbol_nesting(symbols: Sequence[_Symbol]) -> None:
    for index, left in enumerate(symbols):
        for right in symbols[index + 1 :]:
            if left.end < right.start or right.end < left.start:
                continue
            left_contains = left.start <= right.start and left.end >= right.end
            right_contains = right.start <= left.start and right.end >= left.end
            if not left_contains and not right_contains:
                raise RepoSyntaxChunkingError("Python symbol spans overlap without lexical containment")


def _ownership_ranges(lines: Sequence[str], symbols: Sequence[_Symbol]) -> tuple[SourceRange, ...]:
    owners: list[_Symbol | None] = []
    for line_number in range(1, len(lines) + 1):
        containing = [symbol for symbol in symbols if symbol.start <= line_number <= symbol.end]
        if containing:
            containing.sort(key=lambda symbol: (len(symbol.chain), symbol.lexical_order))
            owners.append(containing[-1])
        else:
            owners.append(None)

    index = 0
    while index < len(lines):
        if owners[index] is not None or not _is_trivia(lines[index]):
            index += 1
            continue
        end = index + 1
        while end < len(lines) and owners[end] is None and _is_trivia(lines[end]):
            end += 1
        replacement: _Symbol | None
        if end < len(lines):
            replacement = owners[end]
        else:
            replacement = next(
                (
                    owners[prior]
                    for prior in range(index - 1, -1, -1)
                    if not _is_trivia(lines[prior])
                ),
                None,
            )
        for trivia_index in range(index, end):
            owners[trivia_index] = replacement
        index = end

    regions: list[SourceRange] = []
    start = 1
    owner = owners[0]
    for line_number in range(2, len(lines) + 2):
        next_owner = owners[line_number - 1] if line_number <= len(lines) else object()
        if next_owner is owner:
            continue
        breadcrumbs = (" > ".join(owner.chain),) if owner is not None else ()
        region_end = line_number - 1
        for chunk_start in range(start, region_end + 1, MAX_SOURCE_CHUNK_LINES):
            regions.append(
                SourceRange(
                    start=chunk_start,
                    end=min(chunk_start + MAX_SOURCE_CHUNK_LINES - 1, region_end),
                    breadcrumbs=breadcrumbs,
                )
            )
        start = line_number
        owner = next_owner if line_number <= len(lines) else None
    return tuple(regions)


def _is_trivia(line: str) -> bool:
    return not line.strip() or line.lstrip().startswith("#")
