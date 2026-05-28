"""
test_ifp.py  –  Test cases for the IFP interpreter

Run with:
    python3 test_ifp.py

All test inputs are valid IFP programs NOT taken from the assignment PDF.
Expected outputs are verified against the completed interpreter.
"""

from ifp_ast import TInt, TBool, TString, TLam
from printer import to_base94, encode_string
from parser import p_term
from interpreter import interpret


# ─── Helpers ─────────────────────────────────────────────────────────────────

def enc(n: int) -> str:
    """Encode a non-negative integer as an IFP integer token."""
    return "I" + to_base94(n)


def enc_s(s: str) -> str:
    """Encode a Python string as an IFP string token."""
    return "S" + encode_string(s)


def run(src: str):
    """Parse and evaluate an IFP source string; return (value, steps)."""
    result, steps = interpret(True, p_term(src))
    if isinstance(result, TInt):    return result.value, steps
    if isinstance(result, TBool):   return result.value, steps
    if isinstance(result, TString): return result.value, steps
    if isinstance(result, TLam):    return "<lambda>", steps
    raise RuntimeError(f"Unknown result type: {type(result)}")


def rec(fn_body: str) -> str:
    """Wrap a two-argument lambda in the standard Y-combinator scaffold.

    The scaffold exposes:
        v"  – the recursive self-reference (call v" to recurse)
        v#  – the current argument

    fn_body must be a string of the form  'L" L# <body>'
    """
    return (
        'B$ B$ L" B$ L# B$ v" B$ v# v# '
        'L# B$ v" B$ v# v# '
        + fn_body
    )


# ─── Test registry ────────────────────────────────────────────────────────────

_tests: list[tuple[str, str, object]] = []   # (description, src, expected)


def register(desc: str, src: str, expected: object) -> None:
    _tests.append((desc, src, expected))


# ════════════════════════════════════════════════════════════════════════════
# 1. INTEGER LITERALS & ARITHMETIC
# ════════════════════════════════════════════════════════════════════════════

register("Integer: zero",                   "I!",                                    0)
register("Integer: 93 (max 1-digit)",       "I~",                                   93)
register("Integer: 94 (first 2-digit)",     'I"!',                                  94)
register("Integer: large value 1000",       enc(1000),                           1000)

register("Add: 100 + 200 = 300",            f"B+ {enc(100)} {enc(200)}",           300)
register("Sub: 0 - 1 = -1",                 'B- I! I"',                             -1)
register("Sub: 50 - 30 = 20",               f"B- {enc(50)} {enc(30)}",              20)
register("Mul: 6 * 7 = 42",                 f"B* {enc(6)} {enc(7)}",               42)
register("Mul: anything * 0 = 0",           f"B* {enc(999)} I!",                    0)
register("Div: 7 / 2 = 3 (trunc toward 0)",f"B/ {enc(7)} {enc(2)}",                3)
register("Div: -7 / 2 = -3 (trunc toward 0)",f"B/ U- {enc(7)} {enc(2)}",          -3)
register("Mod: 10 % 3 = 1",                 f"B% {enc(10)} {enc(3)}",               1)
register("Mod: -10 % 3 = -1",              f"B% U- {enc(10)} {enc(3)}",            -1)
register("Neg: U- 0 = 0",                   "U- I!",                                0)
register("Neg: double negation --5 = 5",    f"U- U- {enc(5)}",                      5)
register("Nested: (3*4) + (10-2) = 20",
         f"B+ B* {enc(3)} {enc(4)} B- {enc(10)} {enc(2)}",                         20)
register("Nested: (100/7)*7 ≠ 100 (trunc)",
         f"B= B* B/ {enc(100)} {enc(7)} {enc(7)} {enc(100)}",                   False)

# ════════════════════════════════════════════════════════════════════════════
# 2. BOOLEAN LITERALS & LOGIC
# ════════════════════════════════════════════════════════════════════════════

register("Bool: literal true",              "T",                                  True)
register("Bool: literal false",             "F",                                 False)
register("Unary: U! T = false",             "U! T",                              False)
register("Unary: U! F = true",              "U! F",                               True)
register("Unary: U! U! T = true",           "U! U! T",                            True)
register("AND: T & T = true",               "B& T T",                             True)
register("AND: T & F = false",              "B& T F",                            False)
register("AND: F & F = false",              "B& F F",                            False)
register("OR:  F | F = false",              "B| F F",                            False)
register("OR:  F | T = true",               "B| F T",                             True)
register("OR:  T | T = true",               "B| T T",                             True)
register("De Morgan: !(T&F) = !T|!F",
         "B= U! B& T F B| U! T U! F",                                            True)

# ════════════════════════════════════════════════════════════════════════════
# 3. COMPARISONS
# ════════════════════════════════════════════════════════════════════════════

register("Eq: 42 = 42 → true",             f"B= {enc(42)} {enc(42)}",             True)
register("Eq: 1 = 2 → false",              f"B= {enc(1)} {enc(2)}",              False)
register("Eq: T = T → true",               "B= T T",                              True)
register("Eq: T = F → false",              "B= T F",                             False)
register("Eq: string abc = abc → true",    f"B= {enc_s('abc')} {enc_s('abc')}",   True)
register("Eq: string abc = xyz → false",   f"B= {enc_s('abc')} {enc_s('xyz')}",  False)
register("Lt: 3 < 10 → true",             f"B< {enc(3)} {enc(10)}",              True)
register("Lt: 10 < 3 → false",            f"B< {enc(10)} {enc(3)}",             False)
register("Lt: 5 < 5 → false",             f"B< {enc(5)} {enc(5)}",              False)
register("Gt: 10 > 3 → true",             f"B> {enc(10)} {enc(3)}",              True)
register("Gt: 5 > 5 → false",             f"B> {enc(5)} {enc(5)}",             False)

# ════════════════════════════════════════════════════════════════════════════
# 4. STRING OPERATIONS
# ════════════════════════════════════════════════════════════════════════════

register("String: empty",                   "S",                                    "")
register("String: hello",                   enc_s("hello"),                    "hello")
register("Concat: foo + bar = foobar",      f"B. {enc_s('foo')} {enc_s('bar')}","foobar")
register("Concat: with space",
         f"B. {enc_s('hello')} {enc_s(' world')}",                        "hello world")
register("Take: 0 chars → empty",           f"BT I! {enc_s('hello')}",             "")
register("Take: 3 of 5 → hel",             f"BT {enc(3)} {enc_s('hello')}",     "hel")
register("Take: all 5 → hello",            f"BT {enc(5)} {enc_s('hello')}",   "hello")
register("Drop: 0 chars → hello",          f"BD I! {enc_s('hello')}",         "hello")
register("Drop: 3 of 5 → lo",             f"BD {enc(3)} {enc_s('hello')}",      "lo")
register("Drop: all → empty",             f"BD {enc(5)} {enc_s('hello')}",        "")
register("Take then Drop: middle 2 chars of hello = ll",
         f"BD {enc(2)} BT {enc(4)} {enc_s('hello')}",                           "ll")

# ════════════════════════════════════════════════════════════════════════════
# 5. U# / U$ CONVERSIONS
# ════════════════════════════════════════════════════════════════════════════

register("U$: 0 → 'a'",                    "U$ I!",                               "a")
register("U$: 1 → 'b'",                    'U$ I"',                               "b")
register("U#: 'a' → 0",                    f"U# {enc_s('a')}",                     0)
register("U#: 'b' → 1",                    f"U# {enc_s('b')}",                     1)
register("Roundtrip: U$ U# 'hello'",       f"U$ U# {enc_s('hello')}",         "hello")
register("Roundtrip: U# U$ 42",            f"U# U$ {enc(42)}",                    42)

# ════════════════════════════════════════════════════════════════════════════
# 6. CONDITIONAL
# ════════════════════════════════════════════════════════════════════════════

register("If: T picks first branch",        f"? T {enc(1)} {enc(2)}",               1)
register("If: F picks second branch",       f"? F {enc(1)} {enc(2)}",               2)
register("If: computed cond 5=5 → yes",
         f"? B= {enc(5)} {enc(5)} {enc_s('yes')} {enc_s('no')}",              "yes")
register("If: computed cond 5≠6 → no",
         f"? B= {enc(5)} {enc(6)} {enc_s('yes')} {enc_s('no')}",               "no")
register("If: only selected branch is evaluated (true side)",
         f"? T {enc_s('ok')} {enc_s('never')}",                               "ok")
register("Nested if: 3>2 and 3>1 → big",
         f"? B> {enc(3)} {enc(2)} ? B> {enc(3)} {enc(1)} "
         f"{enc_s('big')} {enc_s('mid')} {enc_s('small')}",                  "big")
register("Nested if: 1<2 → less",
         f"? B< {enc(1)} {enc(2)} {enc_s('less')} {enc_s('more')}",         "less")

# ════════════════════════════════════════════════════════════════════════════
# 7. LAMBDA & FUNCTION APPLICATION
# ════════════════════════════════════════════════════════════════════════════

register("Lambda: identity on int 42",      f'B$ L" v" {enc(42)}',                42)
register("Lambda: identity on bool T",      f'B$ L" v" T',                       True)
register("Lambda: identity on string hi",   f'B$ L" v" {enc_s("hi")}',           "hi")
register("Lambda: constant fn ignores arg", f'B$ L" {enc(99)} {enc(0)}',          99)
register("Lambda: curried add 3+4=7",
         f'B$ B$ L" L# B+ v" v# {enc(3)} {enc(4)}',                              7)
register("Lambda: higher-order (*2) applied to 5 = 10",
         f'B$ B$ L" L# B$ v" v# L$ B* v$ {enc(2)} {enc(5)}',                    10)
register("Lambda: arg used twice → 5+5=10",
         f'B$ L" B+ v" v" {enc(5)}',                                             10)
register("Lambda: inner shadows outer (scoping)",
         f'B$ L" B$ L" v" {enc(7)} {enc(0)}',                                     7)
register("Lambda: swap args",
         f'B$ B$ L" L# B- v# v" {enc(10)} {enc(3)}',                            -7)

# ════════════════════════════════════════════════════════════════════════════
# 8. RECURSION (Y-combinator style)
# ════════════════════════════════════════════════════════════════════════════

# factorial: f(n) = if n=1 then 1 else n * f(n-1)
_fact = 'L" L# ? B= v# I" I" B* v# B$ v" B- v# I"'
register("Recursion: factorial 1 = 1",   rec(_fact) + ' I"',          1)
register("Recursion: factorial 3 = 6",   rec(_fact) + f' {enc(3)}',   6)
register("Recursion: factorial 4 = 24",  rec(_fact) + f' {enc(4)}',  24)
register("Recursion: factorial 5 = 120", rec(_fact) + f' {enc(5)}', 120)

# sum 1..n: f(n) = if n=1 then 1 else n + f(n-1)
_sum = 'L" L# ? B= v# I" I" B+ v# B$ v" B- v# I"'
register("Recursion: sum 1..1 = 1",    rec(_sum) + ' I"',            1)
register("Recursion: sum 1..5 = 15",   rec(_sum) + f' {enc(5)}',    15)
register("Recursion: sum 1..10 = 55",  rec(_sum) + f' {enc(10)}',   55)

# power: f(n) = 2^n  (f(n) = if n=0 then 1 else 2 * f(n-1))
_pow2 = 'L" L# ? B= v# I! I" B* I# B$ v" B- v# I"'
register("Recursion: 2^0 = 1",   rec(_pow2) + ' I!',         1)
register("Recursion: 2^4 = 16",  rec(_pow2) + f' {enc(4)}', 16)
register("Recursion: 2^8 = 256", rec(_pow2) + f' {enc(8)}', 256)


# ─── Runner ───────────────────────────────────────────────────────────────────

def main() -> None:
    passed = 0
    failed = 0

    print(f"\n{'='*72}")
    print(f" IFP Test Suite  –  {len(_tests)} test cases")
    print(f"{'='*72}\n")

    for desc, src, expected in _tests:
        try:
            got, steps = run(src)
            ok = (got == expected)
        except Exception as exc:
            got, steps, ok = f"ERROR: {exc}", 0, False

        mark = "✅" if ok else "❌"
        print(f"{mark}  {desc}")
        if not ok:
            print(f"     Input:    {src}")
            print(f"     Expected: {expected!r}")
            print(f"     Got:      {got!r}")
        else:
            print(f"     Input:    {src}")
            print(f"     Expected: {expected!r}   (steps: {steps})")
        print()

        if ok:
            passed += 1
        else:
            failed += 1

    print(f"{'='*72}")
    print(f" PASSED: {passed}/{len(_tests)}", end="")
    if failed:
        print(f"   FAILED: {failed}")
    else:
        print("  🎉 All tests passed!")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    main()