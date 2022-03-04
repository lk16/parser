from enum import IntEnum
from parser.grammar_parser import REWRITE_RULES, ROOT_SYMBOL, GrammarSymbolType
from parser.parser import (
    ConcatenationParser,
    LiteralParser,
    OptionalParser,
    OrParser,
    Parser,
    RegexBasedParser,
    RepeatParser,
    SymbolParser,
    new_parse_generic,
)
from parser.tree import Tree, prune_by_symbol_types, prune_no_symbol, prune_zero_length
from pathlib import Path
from typing import Dict, Optional, Tuple

ESCAPE_SEQUENCES = [
    ("\\", "\\\\"),
    ("'", "\\'"),
    ('"', '\\"'),
    ("\a", "\\a"),
    ("\b", "\\b"),
    ("\f", "\\f"),
    ("\n", "\\n"),
    ("\r", "\\r"),
    ("\t", "\\t"),
    ("\v", "\\v"),
]


def escape_string(s: str) -> str:
    result = s
    for before, after in ESCAPE_SEQUENCES:
        result = result.replace(before, after)

    return '"' + result + '"'


def unescape_string(s: str) -> str:
    if len(s) < 2 or s[0] != '"' or s[-1] != '"':
        raise ValueError

    result = s[1:-1]
    for after, before in ESCAPE_SEQUENCES:
        result = result.replace(before, after)

    return result


def _grammar_expression(parser: Parser, depth: int = 0) -> str:
    """
    Generates a BNF-like expression from a parser.
    This expression shows what the parser accepts.
    """

    if parser.symbol_type is not None and depth != 0:
        return parser.symbol_type.name

    if isinstance(parser, SymbolParser):  # pragma: nocover
        raise NotImplementedError  # unreachable

    elif isinstance(parser, ConcatenationParser):
        return " ".join(
            _grammar_expression(child, depth + 1) for child in parser.children
        )

    elif isinstance(parser, OrParser):
        expr = " | ".join(
            _grammar_expression(child, depth + 1) for child in parser.children
        )

        if depth != 0:
            expr = f"({expr})"

        return expr

    elif isinstance(parser, OptionalParser):
        return "(" + _grammar_expression(parser.child, depth + 1) + ")?"

    elif isinstance(parser, RepeatParser):
        expr = "(" + _grammar_expression(parser.child, depth + 1) + ")"
        if parser.min_repeats == 0:
            return expr + "*"
        elif parser.min_repeats == 1:
            return expr + "+"
        else:
            return expr + "{" + str(parser.min_repeats) + ",...}"

    elif isinstance(parser, RegexBasedParser):
        return "regex(" + escape_string(parser.regex.pattern[1:]) + ")"

    elif isinstance(parser, LiteralParser):
        return escape_string(parser.literal)

    else:  # pragma: nocover
        raise NotImplementedError


def check_grammar_file_staleness(
    grammar_file: Path, rewrite_rules: Dict[IntEnum, Parser], root_symbol: IntEnum
) -> Tuple[bool, str]:  # pragma: nocover
    if grammar_file.exists():
        old_grammar = grammar_file.read_text()
    else:
        old_grammar = ""

    new_grammar = parsers_to_grammar(rewrite_rules, root_symbol)

    stale = old_grammar != new_grammar
    return stale, new_grammar


def parsers_to_grammar(
    rewrite_rules: Dict[IntEnum, Parser],
    root_symbol: IntEnum,
) -> str:  # pragma: nocover

    output = (
        "// Human readable grammar. Easier to understand than actual rewrite rules.\n"
        "// This file was generated using regenerate_bnf_like_grammar_file().\n"
        "// A unit test should make sure this file is up to date with its source.\n\n"
        f"// The root symbol is {root_symbol.name}.\n\n"
    )

    symbols = sorted(rewrite_rules.keys(), key=lambda x: x.name)

    for i, symbol in enumerate(symbols):
        parser = rewrite_rules[symbol]
        output += f"{symbol.name} = " + _grammar_expression(parser)

        if i == len(symbols) - 1:
            output += "\n"
        else:
            output += "\n\n"

    return output


def grammar_to_parsers(grammar_file: Path) -> str:
    """
    Reads the grammar file and generates a python parser file from it.
    """

    code = grammar_file.read_text()

    tree: Optional[Tree] = new_parse_generic(
        REWRITE_RULES, ROOT_SYMBOL, code, GrammarSymbolType
    )

    assert tree  # TODO

    tree = prune_no_symbol(tree)

    assert tree  # TODO

    tree = prune_zero_length(tree)

    assert tree  # TODO

    tree = prune_by_symbol_types(
        tree,
        {GrammarSymbolType.WHITESPACE_LINE, GrammarSymbolType.WHITESPACE},
        prune_subtree=True,
    )

    breakpoint()
    ...

    return ""
