from __future__ import annotations
from dataclasses import dataclass
from ifp_ast import (
    CHARS, CHARS_DECODED, TBinOp, TBool, TIf, TInt, TLam, TString, TUnOp, TVar, Term,
)

@dataclass(frozen=True)
class ParseError(Exception):
    kind: str
    index: int | None = None
    ch: str | None = None
    def __str__(self) -> str:
        if self.kind == "UnexpectedChar":
            return f"UnexpectedChar({self.ch!r}, {self.index})"
        if self.kind == "UnusedInput":
            return f"UnusedInput({self.index})"
        return "UnexpectedEOF"
def _decode_base94(body: str) -> int:
    """Decode a non-empty base-94 body into a non-negative integer.
    Each character contributes (ord(ch) - 33) as one base-94 digit."""
    v = 0
    for ch in body:
        v = v * 94 + (ord(ch) - 33)
    return v
def _decode_string(body: str) -> str:
    """Decode an IFP string token body into a Python string using CHARS_DECODED."""
    return "".join(CHARS_DECODED[ord(ch) - 33] for ch in body)
def _tokenise(inp: str) -> list[tuple[int, str]]:
    """Split *inp* on whitespace; return list of (source_index, token) pairs."""
    result: list[tuple[int, str]] = []
    i, n = 0, len(inp)
    while i < n:
        while i < n and inp[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        start = i
        while i < n and inp[i] not in " \t\r\n":
            i += 1
        result.append((start, inp[start:i]))
    return result

# ─── Recursive-descent parser ────────────────────────────────────────────────
class _Parser:
    def __init__(self, tokens: list[tuple[int, str]]) -> None:
        self._tokens = tokens
        self._pos    = 0
    def _next(self) -> tuple[int, str]:
        if self._pos >= len(self._tokens):
            raise ParseError("UnexpectedEOF")
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok
    def parse(self) -> Term:
        term = self._parse_term()
        if self._pos < len(self._tokens):
            idx, _ = self._tokens[self._pos]
            raise ParseError("UnusedInput", index=idx)
        return term
    def _parse_term(self) -> Term:
        idx, tok = self._next()

        indicator = tok[0]
        body      = tok[1:]
        # ── Boolean ──────────────────────────────────────────────────────────
        if indicator == "T":
            return TBool(True)
        if indicator == "F":
            return TBool(False)
        # ── Integer ───────────────────────────────────────────────────────────
        if indicator == "I":
            if not body:
                raise ParseError("UnexpectedChar", index=idx, ch=indicator)
            return TInt(_decode_base94(body))
        # ── String ────────────────────────────────────────────────────────────
        if indicator == "S":
            # body can be empty (empty string is valid)
            return TString(_decode_string(body))
        # ── Unary operator ────────────────────────────────────────────────────
        if indicator == "U":
            if len(body) != 1:
                raise ParseError("UnexpectedChar", index=idx, ch=indicator)
            op      = body
            operand = self._parse_term()
            return TUnOp(op, operand)
        # ── Binary operator / function application ────────────────────────────
        if indicator == "B":
            if len(body) != 1:
                raise ParseError("UnexpectedChar", index=idx, ch=indicator)
            op = body
            # B$ is function application: left=func, right=arg
            left  = self._parse_term()
            right = self._parse_term()
            return TBinOp(left, op, right)
        # ── Conditional ───────────────────────────────────────────────────────
        if indicator == "?":
            cond         = self._parse_term()
            true_branch  = self._parse_term()
            false_branch = self._parse_term()
            return TIf(cond, true_branch, false_branch)
        # ── Lambda abstraction ────────────────────────────────────────────────
        if indicator == "L":
            if not body:
                raise ParseError("UnexpectedChar", index=idx, ch=indicator)
            var_id    = _decode_base94(body)
            body_term = self._parse_term()
            return TLam(var_id, body_term)
        # ── Variable ──────────────────────────────────────────────────────────
        if indicator == "v":
            if not body:
                raise ParseError("UnexpectedChar", index=idx, ch=indicator)
            var_id = _decode_base94(body)
            return TVar(var_id)
        raise ParseError("UnexpectedChar", index=idx, ch=indicator)
def p_term(inp: str) -> Term:
    tokens = _tokenise(inp)
    if not tokens:
        raise ParseError("UnexpectedEOF")
    return _Parser(tokens).parse()
