#!/usr/bin/env python

import sys
from dataclasses import replace
from enum import IntEnum
from parser.parser.exceptions import (
    MissingNonTerminalTypes,
    MissingRootNonTerminalType,
    ParseError,
    UnexpectedNonTerminalTypes,
)
from parser.parser.models import (
    ConcatenationExpression,
    ConjunctionExpression,
    Expression,
    NonTerminalExpression,
    OptionalExpression,
    RepeatExpression,
    TerminalExpression,
    Tree,
)
from parser.tokenizer.tokenizer import Token
from typing import Dict, List, Optional, Set


class Parser:
    def __init__(
        self,
        *,
        filename: str,
        code: str,
        tokens: List[Token],
        non_terminal_rules: Dict[IntEnum, Expression],
        pruned_non_terminals: Set[IntEnum],
        root_token: str = "ROOT",
        verbose: bool = False,
    ) -> None:
        self.filename = filename
        self.code = code
        self.tokens = tokens
        self.non_terminal_rules = non_terminal_rules
        self.pruned_non_terminals = pruned_non_terminals
        self.root_token = root_token
        self.verbose = verbose

    def parse(self) -> Tree:
        self._check_non_terminal_rules()

        non_terminal_enum_type = type(next(iter(self.non_terminal_rules.keys())))
        root_non_terminal = non_terminal_enum_type[self.root_token]
        root_expr = self.non_terminal_rules[root_non_terminal]

        tree = self._parse(root_expr, 0)
        tree.token_type = root_non_terminal

        if tree.token_count != len(self.tokens):
            assert tree.token_count < len(self.tokens)
            first_unexpected_token = self.tokens[tree.token_count]
            raise ParseError(self.filename, self.code, first_unexpected_token.offset)

        empty_tree = Tree(0, 0, root_non_terminal, [])

        pruned_tree = _prune_no_token_type(tree) or empty_tree

        pruned_tree = (
            _prune_by_token_types(pruned_tree, self.pruned_non_terminals) or empty_tree
        )

        return pruned_tree

    def _print_parse_debug_info(self, expr: Expression, offset: int) -> None:
        if not self.verbose:
            return

        expr_token_type = "<None>"
        if isinstance(expr, (TerminalExpression, NonTerminalExpression)):
            expr_token_type = expr.token_type.name

        if offset >= len(self.tokens):
            token_type = "<EOF>"
        else:
            token_type = self.tokens[offset].type.name

        print(
            f"DEBUG | Parser"
            + f" | offset={offset:>5}"
            + f" | token_type={token_type:>30}"
            + f" | try to match with {expr_token_type:>30}",
            file=sys.stderr,
        )

    def _parse(self, expr: Expression, offset: int) -> Tree:
        self._print_parse_debug_info(expr, offset)

        if offset >= len(self.tokens):

            if isinstance(expr, (RepeatExpression, OptionalExpression)):
                # No more tokens available, but we don't need any
                return Tree(offset, 0, None, [])

            raise ParseError(self.filename, self.code, offset)

        parse_funcs = {
            ConcatenationExpression: self._parse_concatenation,
            ConjunctionExpression: self._parse_conjunction,
            NonTerminalExpression: self._parse_non_terminal,
            OptionalExpression: self._parse_optional,
            RepeatExpression: self._parse_repeat,
            TerminalExpression: self._parse_terminal,
        }

        # Should not fail, so if this raises a KeyError, we want the parser to crash.
        parse_func = parse_funcs[type(expr)]

        return parse_func(expr, offset)

    def _parse_conjunction(self, expr: Expression, offset: int) -> Tree:
        assert isinstance(expr, ConjunctionExpression)

        parsed: Optional[Tree] = None

        for child in expr.children:
            try:
                parsed = self._parse(child, offset)
                break
            except ParseError:
                continue

        if not parsed:
            raise ParseError(self.filename, self.code, offset)

        return Tree(
            parsed.token_offset,
            parsed.token_count,
            None,
            [parsed],
        )

    def _parse_repeat(self, expr: Expression, offset: int) -> Tree:
        assert isinstance(expr, RepeatExpression)

        children: List[Tree] = []
        child_offset = offset

        while True:
            try:
                parsed = self._parse(expr.child, child_offset)
            except ParseError:
                break
            else:
                children.append(parsed)
                child_offset += parsed.token_count

        return Tree(
            offset,
            child_offset - offset,
            None,
            children,
        )

    def _parse_optional(self, expr: Expression, offset: int) -> Tree:
        assert isinstance(expr, OptionalExpression)

        children: List[Tree] = []
        length = 0

        try:
            parsed = self._parse(expr.child, offset)
            children = [parsed]
            length = parsed.token_count
        except ParseError:
            pass

        return Tree(
            offset,
            length,
            None,
            children,
        )

    def _parse_concatenation(self, expr: Expression, offset: int) -> Tree:
        assert isinstance(expr, ConcatenationExpression)

        sub_trees: List[Tree] = []

        child_offset = offset

        for child in expr.children:
            parsed = self._parse(child, child_offset)
            sub_trees.append(parsed)
            child_offset += parsed.token_count

        return Tree(
            offset,
            child_offset - offset,
            None,
            sub_trees,
        )

    def _parse_terminal(self, expr: Expression, offset: int) -> Tree:
        assert isinstance(expr, TerminalExpression)

        if self.tokens[offset].type != expr.token_type:
            raise ParseError(self.filename, self.code, offset)

        return Tree(offset, 1, expr.token_type, [])

    def _parse_non_terminal(self, expr: Expression, offset: int) -> Tree:
        assert isinstance(expr, NonTerminalExpression)

        non_terminal_expansion = self.non_terminal_rules[expr.token_type]
        child = self._parse(non_terminal_expansion, offset)
        return Tree(child.token_offset, child.token_count, expr.token_type, [child])

    def _check_non_terminal_rules(self) -> None:
        tokens_enum = type(list((self.non_terminal_rules.keys()))[0])

        unexpected_keys = self.non_terminal_rules.keys() - set(tokens_enum)
        missing_keys: Set[IntEnum] = set(tokens_enum) - self.non_terminal_rules.keys()

        if "ROOT" not in tokens_enum.__members__:
            raise MissingRootNonTerminalType

        if missing_keys:
            raise MissingNonTerminalTypes(missing_keys)

        if unexpected_keys:
            raise UnexpectedNonTerminalTypes(unexpected_keys)


def _get_descendants_without_token_types(
    tree: Tree, token_types: Set[IntEnum]
) -> List[Tree]:
    with_token_type: List[Tree] = []

    for child in tree.children:
        if child.token_type in token_types:
            with_token_type += _get_descendants_without_token_types(child, token_types)
        else:
            with_token_type.append(
                replace(
                    child,
                    children=_get_descendants_without_token_types(child, token_types),
                )
            )

    return with_token_type


def _prune_by_token_types(tree: Tree, token_types: Set[IntEnum]) -> Optional[Tree]:
    descendants_with_token_type = _get_descendants_without_token_types(
        tree, token_types
    )

    children = [
        Tree(
            child.token_offset,
            child.token_count,
            child.token_type,
            _get_descendants_without_token_types(child, token_types),
        )
        for child in descendants_with_token_type
    ]

    return Tree(tree.token_offset, tree.token_count, tree.token_type, children)


def _get_descendants_with_token_type(tree: Tree) -> List[Tree]:
    with_token_type: List[Tree] = []

    for child in tree.children:
        if child.token_type is None:
            with_token_type += _get_descendants_with_token_type(child)
        else:
            with_token_type.append(
                replace(child, children=_get_descendants_with_token_type(child))
            )

    return with_token_type


def _prune_no_token_type(tree: Tree) -> Optional[Tree]:
    assert tree.token_type is not None

    return Tree(
        tree.token_offset,
        tree.token_count,
        tree.token_type,
        _get_descendants_with_token_type(tree),
    )
