"""Tests del análisis semántico (Fase 4)."""
from mathlite.lexer import tokenize
from mathlite.parser import parse
from mathlite.semantic import analyze


def diagnose(src):
    toks, _ = tokenize(src)
    ast, _ = parse(toks)
    return analyze(ast)


def test_undeclared_variable():
    errs = diagnose("print(x)")
    assert any("no declarada" in e.message for e in errs)


def test_type_mismatch_string_plus_int():
    errs = diagnose('let r = "hola" + 5')
    assert any("no admitida entre String y Int" in e.message for e in errs)


def test_function_arity_mismatch():
    errs = diagnose("def f(a) { return a }\nf(1, 2)")
    assert any("espera 1 argumentos" in e.message for e in errs)


def test_return_outside_function():
    errs = diagnose("return 5")
    assert any("fuera del cuerpo" in e.message for e in errs)


def test_if_condition_must_be_bool():
    errs = diagnose("if 5 { print(1) }")
    assert any("Bool" in e.message for e in errs)


def test_undefined_function_call():
    errs = diagnose("foo(1)")
    assert any("no está definida" in e.message for e in errs)


def test_no_error_for_valid_program():
    errs = diagnose("""
let x = 1
let y = 2.5
def add(a, b) { return a + b }
print(add(x, y))
""")
    assert errs == []
