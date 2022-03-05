from enum import IntEnum, auto
from parser.parser import (
    ConcatenationParser,
    LiteralParser,
    OptionalParser,
    OrParser,
    Parser,
    RegexBasedParser,
    RepeatParser,
    SymbolParser,
)
from typing import Dict


class GrammarSymbolType(IntEnum):
    FILE = auto()
    LINE = auto()
    COMMENT_LINE = auto()
    WHITESPACE_LINE = auto()
    TOKEN_DEFINITION_LINE = auto()
    TOKEN_NAME = auto()
    TOKEN_COMPOUND_EXPRESSION = auto()
    TOKEN_EXPRESSION = auto()
    WHITESPACE = auto()
    LITERAL_EXPRESSION = auto()
    REGEX_EXPRESSION = auto()  # This name is far from great
    CONCATENATION_EXPRESSION = auto()
    BRACKET_EXPRESSION = auto()
    CONJUNCTION_EXPRESSION = auto()
    BRACKET_EXPRESSION_END = auto()
    INTEGER = auto()


REWRITE_RULES: Dict[IntEnum, Parser] = {
    GrammarSymbolType.FILE: RepeatParser(SymbolParser(GrammarSymbolType.LINE)),
    GrammarSymbolType.LINE: OrParser(
        SymbolParser(GrammarSymbolType.COMMENT_LINE),
        SymbolParser(GrammarSymbolType.WHITESPACE_LINE),
        SymbolParser(GrammarSymbolType.TOKEN_DEFINITION_LINE),
    ),
    GrammarSymbolType.COMMENT_LINE: RegexBasedParser("//[^\n]*\n"),
    GrammarSymbolType.WHITESPACE_LINE: RegexBasedParser(" *\n"),
    GrammarSymbolType.TOKEN_DEFINITION_LINE: ConcatenationParser(
        SymbolParser(GrammarSymbolType.TOKEN_NAME),
        SymbolParser(GrammarSymbolType.WHITESPACE),
        LiteralParser("="),
        SymbolParser(GrammarSymbolType.WHITESPACE),
        SymbolParser(GrammarSymbolType.TOKEN_COMPOUND_EXPRESSION),
        SymbolParser(GrammarSymbolType.WHITESPACE),
    ),
    GrammarSymbolType.TOKEN_NAME: RegexBasedParser("[A-Z_]+"),
    GrammarSymbolType.CONCATENATION_EXPRESSION: ConcatenationParser(
        SymbolParser(GrammarSymbolType.TOKEN_EXPRESSION),
        SymbolParser(GrammarSymbolType.WHITESPACE),
        SymbolParser(GrammarSymbolType.TOKEN_COMPOUND_EXPRESSION),
    ),
    GrammarSymbolType.BRACKET_EXPRESSION: ConcatenationParser(
        LiteralParser("("),
        SymbolParser(GrammarSymbolType.WHITESPACE),
        SymbolParser(GrammarSymbolType.TOKEN_COMPOUND_EXPRESSION),
        SymbolParser(GrammarSymbolType.WHITESPACE),
        SymbolParser(GrammarSymbolType.BRACKET_EXPRESSION_END),
    ),
    GrammarSymbolType.BRACKET_EXPRESSION_END: OrParser(
        LiteralParser(")"),
        LiteralParser(")+"),
        LiteralParser(")*"),
        LiteralParser(")?"),
        ConcatenationParser(
            LiteralParser("){"),
            SymbolParser(GrammarSymbolType.INTEGER),
            LiteralParser(",...}"),
        ),
    ),
    GrammarSymbolType.INTEGER: RegexBasedParser("[0-9]+"),
    GrammarSymbolType.TOKEN_COMPOUND_EXPRESSION: OrParser(
        SymbolParser(GrammarSymbolType.TOKEN_EXPRESSION),
        SymbolParser(GrammarSymbolType.CONCATENATION_EXPRESSION),
        SymbolParser(GrammarSymbolType.CONJUNCTION_EXPRESSION),
        ConcatenationParser(
            SymbolParser(GrammarSymbolType.BRACKET_EXPRESSION),
            OptionalParser(
                ConcatenationParser(
                    SymbolParser(GrammarSymbolType.WHITESPACE),
                    SymbolParser(GrammarSymbolType.TOKEN_COMPOUND_EXPRESSION),
                ),
            ),
        ),
    ),
    GrammarSymbolType.CONJUNCTION_EXPRESSION: ConcatenationParser(
        SymbolParser(GrammarSymbolType.TOKEN_EXPRESSION),
        SymbolParser(GrammarSymbolType.WHITESPACE),
        LiteralParser("|"),
        SymbolParser(GrammarSymbolType.WHITESPACE),
        SymbolParser(GrammarSymbolType.TOKEN_COMPOUND_EXPRESSION),
    ),
    GrammarSymbolType.TOKEN_EXPRESSION: OrParser(
        SymbolParser(GrammarSymbolType.LITERAL_EXPRESSION),
        SymbolParser(GrammarSymbolType.TOKEN_NAME),
        SymbolParser(GrammarSymbolType.REGEX_EXPRESSION),
    ),
    GrammarSymbolType.REGEX_EXPRESSION: ConcatenationParser(
        LiteralParser("regex("),
        SymbolParser(GrammarSymbolType.LITERAL_EXPRESSION),
        LiteralParser(")"),
    ),
    GrammarSymbolType.WHITESPACE: RegexBasedParser(" *"),
    GrammarSymbolType.LITERAL_EXPRESSION: RegexBasedParser(
        '"([^\\\\]|\\\\("|n|\\\\))*?"'
    ),
}

ROOT_SYMBOL = GrammarSymbolType.FILE