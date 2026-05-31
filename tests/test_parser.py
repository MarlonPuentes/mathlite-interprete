"""Tests del parser y construcción del AST (Fase 3)."""
from mathlite.ast_nodes import (
    AssignNode, BinOpNode, FuncCallNode, FuncDefNode, IfNode, NumberNode,
    PrintNode, ProgramNode, WhileNode, pretty,
)
from mathlite.lexer import tokenize
from mathlite.parser import parse


def build(src):
    toks, lex_errs = tokenize(src)
    assert lex_errs == []
    ast, errs = parse(toks)
    return ast, errs


def test_parse_let():
    ast, errs = build("let x = 5")
    assert errs == []
    assert isinstance(ast.statements[0], AssignNode)
    assert ast.statements[0].name == "x"


def test_parse_arithmetic_precedence():
    ast, _ = build("let r = 3 + 4 * 2")
    # r = 3 + (4*2)  → AssignNode → BinOp(+, 3, BinOp(*, 4, 2))
    expr = ast.statements[0].expr
    assert isinstance(expr, BinOpNode) and expr.op == "+"
    assert isinstance(expr.right, BinOpNode) and expr.right.op == "*"


def test_parse_power_right_associative():
    ast, _ = build("let r = 2 ^ 3 ^ 2")
    expr = ast.statements[0].expr
    assert isinstance(expr, BinOpNode) and expr.op == "^"
    # right child es a su vez ^
    assert isinstance(expr.right, BinOpNode) and expr.right.op == "^"


def test_parse_function_definition_and_call():
    ast, errs = build("def f(a, b) { return a + b }\nprint(f(1,2))")
    assert errs == []
    assert isinstance(ast.statements[0], FuncDefNode)
    assert ast.statements[0].params == ["a", "b"]
    assert isinstance(ast.statements[1], PrintNode)
    assert isinstance(ast.statements[1].expr, FuncCallNode)


def test_parse_if_else_and_while():
    src = """
let i = 0
if i < 1 { print(1) } else { print(2) }
while i < 1 { let i = i + 1 }
"""
    ast, errs = build(src)
    assert errs == []
    assert any(isinstance(s, IfNode) for s in ast.statements)
    assert any(isinstance(s, WhileNode) for s in ast.statements)


def test_parse_unclosed_paren_reports_error():
    toks, _ = tokenize("print((3 + 4 * 2)")
    _ast, errs = parse(toks)
    assert any(d.phase.value == "syntax" for d in errs)


def test_parse_if_without_condition():
    toks, _ = tokenize("if { print(1) }")
    _ast, errs = parse(toks)
    assert any("requiere condición" in d.message for d in errs)


def test_parse_def_without_brace():
    toks, _ = tokenize("def f() return 1")
    _ast, errs = parse(toks)
    assert any(d.phase.value == "syntax" for d in errs)


def test_pretty_printer_works():
    ast, _ = build("print(1 + 2)")
    s = pretty(ast)
    assert "Program" in s and "Print" in s and "BinOp(+)" in s
