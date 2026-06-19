"""Expression AST and NumPy evaluation for grid_program / field_program."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np

from .array_manager import PixilArray


class TokKind(Enum):
    NUM = auto()
    IDENT = auto()
    OP = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    EOF = auto()


@dataclass
class Token:
    kind: TokKind
    value: str = ""


@dataclass
class ExprNode:
    kind: str
    value: Any = None
    children: Optional[List["ExprNode"]] = None

    def __post_init__(self) -> None:
        if self.children is None:
            self.children = []


_IDENT_RE = re.compile(r"^[a-zA-Z_]\w*$")
_SCALAR_FUNCS = frozenset({"clamp", "where", "min", "max", "abs", "floor"})
_FIELD_FUNCS = frozenset({"lap", "at", "neighbors", "neighbors4"})
_FIELD_FUNCS = frozenset({"lap", "at", "neighbors", "neighbors4", "sum_sites"})
_SITE_VARS = frozenset({"dx", "dy", "dist2", "weight"})


def tokenize(expr: str) -> List[Token]:
    text = expr.strip()
    tokens: List[Token] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "()":
            tokens.append(Token(TokKind.LPAREN if ch == "(" else TokKind.RPAREN, ch))
            i += 1
            continue
        if ch == ",":
            tokens.append(Token(TokKind.COMMA, ch))
            i += 1
            continue
        two = text[i : i + 2]
        if two in ("==", "!=", "<=", ">="):
            tokens.append(Token(TokKind.OP, two))
            i += 2
            continue
        if ch in "+-*/<>=!":
            tokens.append(Token(TokKind.OP, ch))
            i += 1
            continue
        if ch.isdigit() or (ch == "." and i + 1 < len(text) and text[i + 1].isdigit()):
            j = i
            while j < len(text) and (text[j].isdigit() or text[j] == "."):
                j += 1
            tokens.append(Token(TokKind.NUM, text[i:j]))
            i = j
            continue
        j = i
        while j < len(text) and (text[j].isalnum() or text[j] == "_"):
            j += 1
        ident = text[i:j]
        if ident in ("and", "or", "not"):
            tokens.append(Token(TokKind.OP, ident))
        else:
            tokens.append(Token(TokKind.IDENT, ident))
        i = j
    tokens.append(Token(TokKind.EOF, ""))
    return tokens


class _Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, kind: TokKind, value: Optional[str] = None) -> Token:
        tok = self._advance()
        if tok.kind != kind or (value is not None and tok.value != value):
            raise ValueError(f"Unexpected token {tok.value!r}")
        return tok

    def parse(self) -> ExprNode:
        node = self._parse_or()
        if self._peek().kind != TokKind.EOF:
            raise ValueError(f"Unexpected trailing token {self._peek().value!r}")
        return node

    def _parse_or(self) -> ExprNode:
        left = self._parse_and()
        while self._peek().kind == TokKind.OP and self._peek().value == "or":
            self._advance()
            right = self._parse_and()
            left = ExprNode("or", children=[left, right])
        return left

    def _parse_and(self) -> ExprNode:
        left = self._parse_not()
        while self._peek().kind == TokKind.OP and self._peek().value == "and":
            self._advance()
            right = self._parse_not()
            left = ExprNode("and", children=[left, right])
        return left

    def _parse_not(self) -> ExprNode:
        if self._peek().kind == TokKind.OP and self._peek().value == "not":
            self._advance()
            return ExprNode("not", children=[self._parse_not()])
        return self._parse_compare()

    def _parse_compare(self) -> ExprNode:
        left = self._parse_add()
        while self._peek().kind == TokKind.OP and self._peek().value in (
            "==", "!=", "<", ">", "<=", ">="
        ):
            op = self._advance().value
            right = self._parse_add()
            left = ExprNode("cmp", value=op, children=[left, right])
        return left

    def _parse_add(self) -> ExprNode:
        left = self._parse_mul()
        while self._peek().kind == TokKind.OP and self._peek().value in ("+", "-"):
            op = self._advance().value
            right = self._parse_mul()
            left = ExprNode("binop", value=op, children=[left, right])
        return left

    def _parse_mul(self) -> ExprNode:
        left = self._parse_unary()
        while self._peek().kind == TokKind.OP and self._peek().value in ("*", "/"):
            op = self._advance().value
            right = self._parse_unary()
            left = ExprNode("binop", value=op, children=[left, right])
        return left

    def _parse_unary(self) -> ExprNode:
        if self._peek().kind == TokKind.OP and self._peek().value == "-":
            self._advance()
            return ExprNode("neg", children=[self._parse_unary()])
        return self._parse_primary()

    def _parse_primary(self) -> ExprNode:
        tok = self._peek()
        if tok.kind == TokKind.NUM:
            self._advance()
            return ExprNode("num", value=float(tok.value))
        if tok.kind == TokKind.IDENT:
            name = self._advance().value
            if self._peek().kind == TokKind.LPAREN:
                self._advance()
                args: List[ExprNode] = []
                if self._peek().kind != TokKind.RPAREN:
                    args.append(self._parse_or())
                    while self._peek().kind == TokKind.COMMA:
                        self._advance()
                        args.append(self._parse_or())
                self._expect(TokKind.RPAREN, ")")
                return ExprNode("call", value=name, children=args)
            return ExprNode("ident", value=name)
        if tok.kind == TokKind.LPAREN:
            self._advance()
            node = self._parse_or()
            self._expect(TokKind.RPAREN, ")")
            return node
        raise ValueError(f"Unexpected token {tok.value!r}")


def parse_expr(expr: str) -> ExprNode:
    return _Parser(tokenize(expr)).parse()


def _to_array(value: Any) -> np.ndarray:
    if isinstance(value, np.ndarray):
        return value
    return np.asarray(value, dtype=np.float64)


def _broadcast(a: Any, b: Any) -> tuple[np.ndarray, np.ndarray]:
    aa = _to_array(a)
    bb = _to_array(b)
    if aa.shape == () and bb.ndim > 0:
        aa = np.full_like(bb, float(aa), dtype=np.float64)
    elif bb.shape == () and aa.ndim > 0:
        bb = np.full_like(aa, float(bb), dtype=np.float64)
    return aa, bb


@dataclass
class GridEvalContext:
    scalars: Dict[str, float]
    fields: Dict[str, np.ndarray]
    temps: Dict[str, np.ndarray]
    grid_vars: Dict[str, np.ndarray]
    size: int
    boundary: str
    laplacian_fn: Callable[[str], np.ndarray]
    neighbors_fn: Callable[[str, bool], np.ndarray]
    below_avg_fn: Callable[[str], np.ndarray]
    random_field_fn: Callable[[float, float], np.ndarray]


@dataclass
class FieldEvalContext:
    scalars: Dict[str, float]
    temps: Dict[str, np.ndarray]
    site_vars: Dict[str, np.ndarray]
    grid_vars: Dict[str, np.ndarray]
    sum_sites_fn: Callable[[ExprNode], np.ndarray]


def _resolve_ident(name: str, ctx: Union[GridEvalContext, FieldEvalContext]) -> Any:
    if name in ctx.temps:
        return ctx.temps[name]
    if name in ctx.scalars:
        return ctx.scalars[name]
    if isinstance(ctx, FieldEvalContext) and name in ctx.grid_vars:
        return ctx.grid_vars[name]
    if isinstance(ctx, FieldEvalContext) and name in ctx.site_vars:
        return ctx.site_vars[name]
    if isinstance(ctx, GridEvalContext) and name in ctx.grid_vars:
        return ctx.grid_vars[name]
    if isinstance(ctx, GridEvalContext) and name in ctx.fields:
        return ctx.fields[name]
    raise KeyError(f"Unknown identifier in expression: {name}")


def eval_expr(node: ExprNode, ctx: Union[GridEvalContext, FieldEvalContext]) -> Any:
    kind = node.kind
    if kind == "num":
        return float(node.value)
    if kind == "ident":
        return _resolve_ident(str(node.value), ctx)
    if kind == "neg":
        val = eval_expr(node.children[0], ctx)
        if isinstance(val, np.ndarray):
            return -val
        return -float(val)
    if kind == "not":
        val = eval_expr(node.children[0], ctx)
        if isinstance(val, np.ndarray):
            return np.logical_not(val)
        return not bool(val)
    if kind == "and":
        left = eval_expr(node.children[0], ctx)
        right = eval_expr(node.children[1], ctx)
        if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
            la, rb = _broadcast(left, right)
            return np.logical_and(la != 0, rb != 0)
        return bool(left) and bool(right)
    if kind == "or":
        left = eval_expr(node.children[0], ctx)
        right = eval_expr(node.children[1], ctx)
        if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
            la, rb = _broadcast(left, right)
            return np.logical_or(la != 0, rb != 0)
        return bool(left) or bool(right)
    if kind == "cmp":
        left = eval_expr(node.children[0], ctx)
        right = eval_expr(node.children[1], ctx)
        la, rb = _broadcast(left, right)
        op = node.value
        if op == "==":
            return la == rb
        if op == "!=":
            return la != rb
        if op == "<":
            return la < rb
        if op == ">":
            return la > rb
        if op == "<=":
            return la <= rb
        if op == ">=":
            return la >= rb
        raise ValueError(f"Unknown cmp op {op}")
    if kind == "binop":
        left = eval_expr(node.children[0], ctx)
        right = eval_expr(node.children[1], ctx)
        la, rb = _broadcast(left, right)
        op = node.value
        if op == "+":
            return la + rb
        if op == "-":
            return la - rb
        if op == "*":
            return la * rb
        if op == "/":
            return np.divide(la, rb, out=np.zeros_like(la, dtype=np.float64), where=rb != 0)
        raise ValueError(f"Unknown binop {op}")
    if kind == "call":
        name = str(node.value)
        if isinstance(ctx, FieldEvalContext) and name == "sum_sites" and len(node.children) == 1:
            return ctx.sum_sites_fn(node.children[0])
        if isinstance(ctx, GridEvalContext):
            if name == "lap" and len(node.children) == 1:
                field_node = node.children[0]
                if field_node.kind != "ident":
                    raise ValueError("lap() expects a field name")
                return ctx.laplacian_fn(str(field_node.value))
            if name == "at" and len(node.children) == 1:
                field_node = node.children[0]
                if field_node.kind != "ident":
                    raise ValueError("at() expects a field name")
                field = str(field_node.value)
                if field not in ctx.fields:
                    raise KeyError(f"Unknown field {field}")
                return ctx.fields[field]
            if name in ("neighbors", "neighbors4") and len(node.children) == 1:
                field_node = node.children[0]
                if field_node.kind != "ident":
                    raise ValueError(f"{name}() expects a field name")
                orth = name == "neighbors4"
                return ctx.neighbors_fn(str(field_node.value), orth)
            if name == "below_avg" and len(node.children) == 1:
                field_node = node.children[0]
                if field_node.kind != "ident":
                    raise ValueError("below_avg() expects a field name")
                return ctx.below_avg_fn(str(field_node.value))
            if name == "random_field" and len(node.children) == 2:
                lo = float(eval_expr(node.children[0], ctx))
                hi = float(eval_expr(node.children[1], ctx))
                return ctx.random_field_fn(lo, hi)
        args = [eval_expr(child, ctx) for child in node.children]
        if name == "clamp" and len(args) == 3:
            val, lo, hi = args
            return np.clip(_to_array(val), float(lo), float(hi))
        if name == "where" and len(args) == 3:
            cond, a, b = args
            ca, aa = _broadcast(cond, a)
            _, bb = _broadcast(cond, b)
            return np.where(ca != 0, aa, bb)
        if name == "min":
            if len(args) == 2:
                a, b = _broadcast(args[0], args[1])
                return np.minimum(a, b)
        if name == "max":
            if len(args) == 2:
                a, b = _broadcast(args[0], args[1])
                return np.maximum(a, b)
        if name == "abs" and len(args) == 1:
            val = args[0]
            if isinstance(val, np.ndarray):
                return np.abs(val)
            return abs(float(val))
        if name == "floor" and len(args) == 1:
            val = args[0]
            if isinstance(val, np.ndarray):
                return np.floor(val)
            return float(np.floor(float(val)))
        if name == "sin" and len(args) == 1:
            val = _to_array(args[0])
            return np.sin(val)
        if name == "cos" and len(args) == 1:
            val = _to_array(args[0])
            return np.cos(val)
        if name == "sqrt" and len(args) == 1:
            val = _to_array(args[0])
            return np.sqrt(np.maximum(val, 0.0))
        if name == "pow" and len(args) == 2:
            a, b = _broadcast(args[0], args[1])
            return np.power(a, b)
        raise ValueError(f"Unknown or invalid call: {name}")
    raise ValueError(f"Unknown node kind {kind}")


def resolve_scalar(value: str, variables: Any) -> float:
    text = value.strip()
    if re.match(r"^-?\d*\.?\d+$", text):
        return float(text)
    if text.startswith("v_"):
        val = variables.get(text) if hasattr(variables, "get") else variables[text]
        if isinstance(val, PixilArray):
            raise ValueError(f"Expected scalar, got array {text}")
        return float(val)
    raise ValueError(f"Cannot resolve scalar {text!r}")


def resolve_size(value: str, variables: Any) -> int:
    return int(resolve_scalar(value, variables))
