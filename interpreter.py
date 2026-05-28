from __future__ import annotations
from dataclasses import dataclass
from ifp_ast import TBinOp, TBool, TIf, TInt, TLam, TString, TUnOp, TVar, Term
from printer import encode_string, to_base94

MAX_STEPS = 10_000_000

class InterpreterError(Exception):
    pass
class BetaReductionLimit(InterpreterError):
    pass
class ScopeError(InterpreterError):
    pass
class TypeError_(InterpreterError):
    pass
class ArithmeticError_(InterpreterError):
    pass
class UnknownUnOp(InterpreterError):
    def __init__(self, op: str):
        super().__init__(f"Unknown unary operator: {op}")
        self.op = op
class UnknownBinOp(InterpreterError):
    def __init__(self, op: str):
        super().__init__(f"Unknown binary operator: {op}")
        self.op = op
@dataclass
class VInt:
    value: int
@dataclass
class VBool:
    value: bool
@dataclass
class VString:
    value: str
@dataclass
class VClosure:
    var: int
    body: Term
    env: dict[int, "Thunk"]

Value = VInt | VBool | VString | VClosure
@dataclass
class Thunk:
    kind: str
    value: Value | None = None
    steps: int = 0
    term: Term | None = None
    env: dict[int, "Thunk"] | None = None
def _to_term(v: Value) -> Term:
    if isinstance(v, VInt):
        return TInt(v.value)
    if isinstance(v, VBool):
        return TBool(v.value)
    if isinstance(v, VString):
        return TString(v.value)
    if isinstance(v, VClosure):
        return TLam(v.var, v.body)
    raise TypeError(f"Unknown value type: {type(v).__name__}")

from ifp_ast import CHARS_DECODED as _ALPHA

_ALPHA_INDEX: dict[str, int] = {ch: i for i, ch in enumerate(_ALPHA)}

def _string_to_int(s: str) -> int:
    v = 0
    for ch in s:
        v = v * 94 + _ALPHA_INDEX[ch]
    return v
def _int_to_string(v: int) -> str:
    if v == 0:
        return _ALPHA[0]
    digits: list[str] = []
    while v > 0:
        v, r = divmod(v, 94)
        digits.append(_ALPHA[r])
    return "".join(reversed(digits))
def interpret(check_max: bool, term: Term) -> tuple[Term, int]:
    steps = 0
    def make_thunk(t: Term, env: dict[int, Thunk]) -> Thunk:
        return Thunk(kind="lazy", term=t, env=env)
    def force(thunk: Thunk) -> Value:
        if thunk.kind == "value":
            return thunk.value
        return eval_term(thunk.term, thunk.env)
    def eval_term(t: Term, env: dict[int, Thunk]) -> Value:
        nonlocal steps
        current_term = t
        current_env  = env
        while True:
            t   = current_term
            env = current_env

            if isinstance(t, TInt):
                return VInt(t.value)
            if isinstance(t, TBool):
                return VBool(t.value)
            if isinstance(t, TString):
                return VString(t.value)
            if isinstance(t, TLam):
                return VClosure(t.var, t.body, dict(env))
            if isinstance(t, TVar):
                if t.value not in env:
                    raise ScopeError(f"Unbound variable: v{t.value}")
                return force(env[t.value])
            if isinstance(t, TUnOp):
                val = eval_term(t.term, env)
                op  = t.op
                if op == "-":
                    if not isinstance(val, VInt):
                        raise TypeError_(f"U- expects integer, got {type(val).__name__}")
                    return VInt(-val.value)
                if op == "!":
                    if not isinstance(val, VBool):
                        raise TypeError_(f"U! expects bool, got {type(val).__name__}")
                    return VBool(not val.value)
                if op == "#":
                    if not isinstance(val, VString):
                        raise TypeError_(f"U# expects string, got {type(val).__name__}")
                    return VInt(_string_to_int(val.value))
                if op == "$":
                    if not isinstance(val, VInt):
                        raise TypeError_(f"U$ expects integer, got {type(val).__name__}")
                    return VString(_int_to_string(val.value))
                raise UnknownUnOp(op)
            if isinstance(t, TBinOp):
                op = t.op
                if op == "$":
                    nonlocal_steps_ref = steps
                    if check_max and steps >= MAX_STEPS:
                        raise BetaReductionLimit(
                            f"Beta reduction limit of {MAX_STEPS} exceeded"
                        )
                    steps += 1
                    fn = eval_term(t.left, env)
                    if not isinstance(fn, VClosure):
                        raise TypeError_(
                            f"B$ left-hand side must be a lambda, got {type(fn).__name__}"
                        )
                    arg_thunk = make_thunk(t.right, env)
                    new_env = dict(fn.env)
                    new_env[fn.var] = arg_thunk
                    current_term = fn.body
                    current_env  = new_env
                    continue

                left  = eval_term(t.left,  env)
                right = eval_term(t.right, env)
                if op == "+":
                    _expect_int(left, right, "B+")
                    return VInt(left.value + right.value)
                if op == "-":
                    _expect_int(left, right, "B-")
                    return VInt(left.value - right.value)
                if op == "*":
                    _expect_int(left, right, "B*")
                    return VInt(left.value * right.value)
                if op == "/":
                    _expect_int(left, right, "B/")
                    a, b = left.value, right.value
                    if b == 0:
                        raise ArithmeticError_("Division by zero")
                    result = int(a / b)
                    return VInt(result)
                if op == "%":
                    _expect_int(left, right, "B%")
                    a, b = left.value, right.value 
                    if b == 0:
                        raise ArithmeticError_("Modulo by zero")
                    result = int(a / b)
                    return VInt(a - result * b)
                if op == "<":
                    _expect_int(left, right, "B<")
                    return VBool(left.value < right.value)
                if op == ">":
                    _expect_int(left, right, "B>")
                    return VBool(left.value > right.value)
                if op == "=":
                    if type(left) is not type(right):
                        raise TypeError_("B= applied to different types")
                    if isinstance(left, VInt):
                        return VBool(left.value == right.value)
                    if isinstance(left, VBool):
                        return VBool(left.value == right.value)
                    if isinstance(left, VString):
                        return VBool(left.value == right.value)
                    raise TypeError_(f"B= unsupported type {type(left).__name__}")
                if op == "|":
                    _expect_bool(left, right, "B|")
                    return VBool(left.value or right.value)
                if op == "&":
                    _expect_bool(left, right, "B&")
                    return VBool(left.value and right.value)
                if op == ".":
                    _expect_str(left, right, "B.")
                    return VString(left.value + right.value)
                if op == "T":
                    if not isinstance(left, VInt):
                        raise TypeError_(f"BT left must be int, got {type(left).__name__}")
                    if not isinstance(right, VString):
                        raise TypeError_(f"BT right must be string, got {type(right).__name__}")
                    return VString(right.value[:left.value])
                if op == "D":
                    if not isinstance(left, VInt):
                        raise TypeError_(f"BD left must be int, got {type(left).__name__}")
                    if not isinstance(right, VString):
                        raise TypeError_(f"BD right must be string, got {type(right).__name__}")
                    return VString(right.value[left.value:])
                raise UnknownBinOp(op)
            if isinstance(t, TIf):
                cond = eval_term(t.cond, env)
                if not isinstance(cond, VBool):
                    raise TypeError_(f"? condition must be bool, got {type(cond).__name__}")
                current_term = t.true_branch if cond.value else t.false_branch
                current_env  = env
                continue
            raise TypeError_(f"Unknown term type: {type(t).__name__}")
    
    def _expect_int(l: Value, r: Value, ctx: str) -> None:
        if not isinstance(l, VInt) or not isinstance(r, VInt):
            raise TypeError_(
                f"{ctx} expects two integers, got {type(l).__name__} and {type(r).__name__}"
            )
    def _expect_bool(l: Value, r: Value, ctx: str) -> None:
        if not isinstance(l, VBool) or not isinstance(r, VBool):
            raise TypeError_(
                f"{ctx} expects two booleans, got {type(l).__name__} and {type(r).__name__}"
            )
    def _expect_str(l: Value, r: Value, ctx: str) -> None:
        if not isinstance(l, VString) or not isinstance(r, VString):
            raise TypeError_(
                f"{ctx} expects two strings, got {type(l).__name__} and {type(r).__name__}"
            )
    result = eval_term(term, {})
    return _to_term(result), steps
