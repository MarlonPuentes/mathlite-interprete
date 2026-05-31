"""Tests del intérprete (Fase 5)."""
from mathlite.pipeline import run_source


def out(src):
    r = run_source(src)
    return r.output, r.diagnostics


def test_run_area_example_from_pdf():
    src = """
let base = 5
let altura = 3.0
def area(b, h) { return (b * h) / 2 }
let resultado = area(base, altura)
print(resultado)
"""
    output, errs = out(src)
    assert errs == []
    assert output == ["7.5"]


def test_while_loop_squares():
    src = """
let i = 1
while i <= 5 {
  print(i * i)
  let i = i + 1
}
"""
    output, errs = out(src)
    assert errs == []
    assert output == ["1", "4", "9", "16", "25"]


def test_recursive_factorial():
    src = """
def fact(n) {
  if n <= 1 { return 1 }
  return n * fact(n - 1)
}
print(fact(6))
"""
    output, errs = out(src)
    assert errs == []
    assert output == ["720"]


def test_precedence_mixed():
    src = "print((3 + 4 * 2) / (1 - 5) ^ 2)"
    output, errs = out(src)
    assert errs == []
    assert output == ["0.6875"]


def test_trig_builtins_compose():
    src = "print(sin(0) + cos(0) + sqrt(16))"
    output, errs = out(src)
    assert errs == []
    assert output == ["5.0"]


def test_function_calls_function():
    src = """
def cuad(n) { return n * n }
def hipot(a, b) { return sqrt(cuad(a) + cuad(b)) }
print(hipot(3, 4))
"""
    output, errs = out(src)
    assert errs == []
    assert output == ["5.0"]


def test_sum_1_to_n_with_while():
    src = """
let n = 10
let s = 0
let i = 1
while i <= n {
  let s = s + i
  let i = i + 1
}
print(s)
"""
    output, errs = out(src)
    assert errs == []
    assert output == ["55"]


def test_runtime_division_by_zero():
    _, errs = out("let r = 10 / 0")
    assert any("división por cero" in e.message for e in errs)


def test_runtime_unknown_function_at_call_time():
    # función NO definida en el programa: el analizador semántico lo marca,
    # pero el intérprete también debe reportarlo si llegara a evaluarse.
    r = run_source("foo(1)", execute=True)
    assert any(d.phase.value in ("semantic", "runtime") for d in r.diagnostics)


def test_boolean_logic_short_circuit():
    src = """
let a = true
let b = false
if a or b { print("ok") }
if a and not b { print("yes") }
"""
    output, errs = out(src)
    assert errs == []
    assert output == ["ok", "yes"]


def test_modulo_and_negative_unary():
    src = """
print(10 % 3)
print(-(2 + 3))
"""
    output, errs = out(src)
    assert errs == []
    assert output == ["1", "-5"]


def test_string_concatenation():
    src = 'print("hola " + "mundo")'
    output, errs = out(src)
    assert errs == []
    assert output == ["hola mundo"]
