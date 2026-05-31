"""Tests integradores: verifican que cada categoría de error
aterrice en el campo `diagnostics` del pipeline con la fase correcta."""
from mathlite.pipeline import run_source


def phases(src):
    return {d.phase.value for d in run_source(src).diagnostics}


def test_lexical_invalid_char_phase():
    assert "lexical" in phases("let x = @ + 1")


def test_lexical_unterminated_string_phase():
    assert "lexical" in phases('print("hola)')


def test_syntax_unclosed_paren_phase():
    assert "syntax" in phases("print((3 + 4 * 2)")


def test_syntax_if_without_condition_phase():
    assert "syntax" in phases("if { print(1) }")


def test_semantic_undeclared_phase():
    assert "semantic" in phases("print(x)")


def test_runtime_division_phase():
    assert "runtime" in phases("let r = 10 / 0")


def test_clean_program_has_no_diagnostics():
    r = run_source("print(1 + 2)")
    assert r.diagnostics == []
    assert r.executed
    assert r.output == ["3"]
