"""Definición de nodos del AST de MathLite.

Cada nodo guarda `line`/`col` para reporte de errores y un campo `inferred_type`
que el análisis semántico rellena.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Node:
    line: int = 0
    col: int = 0
    inferred_type: Optional[str] = field(default=None, init=False, repr=False)


# ---------- expresiones ----------
@dataclass
class NumberNode(Node):
    value: float | int = 0
    is_real: bool = False


@dataclass
class StringNode(Node):
    value: str = ""


@dataclass
class BoolNode(Node):
    value: bool = False


@dataclass
class VariableNode(Node):
    name: str = ""


@dataclass
class UnaryOpNode(Node):
    op: str = ""
    operand: Node = None  # type: ignore


@dataclass
class BinOpNode(Node):
    op: str = ""
    left: Node = None   # type: ignore
    right: Node = None  # type: ignore


@dataclass
class FuncCallNode(Node):
    name: str = ""
    args: list[Node] = field(default_factory=list)


# ---------- sentencias ----------
@dataclass
class AssignNode(Node):
    name: str = ""
    expr: Node = None  # type: ignore


@dataclass
class FuncDefNode(Node):
    name: str = ""
    params: list[str] = field(default_factory=list)
    body: "BlockNode" = None  # type: ignore


@dataclass
class IfNode(Node):
    condition: Node = None  # type: ignore
    then_block: "BlockNode" = None  # type: ignore
    else_block: Optional["BlockNode"] = None


@dataclass
class WhileNode(Node):
    condition: Node = None  # type: ignore
    body: "BlockNode" = None  # type: ignore


@dataclass
class ReturnNode(Node):
    expr: Optional[Node] = None


@dataclass
class PrintNode(Node):
    expr: Node = None  # type: ignore


@dataclass
class ExprStmtNode(Node):
    expr: Node = None  # type: ignore


@dataclass
class BlockNode(Node):
    statements: list[Node] = field(default_factory=list)


@dataclass
class ProgramNode(Node):
    statements: list[Node] = field(default_factory=list)


# ---------- pretty printer (formato árbol indentado) ----------
def pretty(node: Node, indent: int = 0) -> str:
    pad = "  " * indent
    if node is None:
        return f"{pad}<None>"

    if isinstance(node, ProgramNode):
        s = f"{pad}Program\n"
        for st in node.statements:
            s += pretty(st, indent + 1)
        return s
    if isinstance(node, BlockNode):
        s = f"{pad}Block\n"
        for st in node.statements:
            s += pretty(st, indent + 1)
        return s
    if isinstance(node, NumberNode):
        kind = "Real" if node.is_real else "Int"
        return f"{pad}{kind}({node.value})\n"
    if isinstance(node, StringNode):
        return f"{pad}String({node.value!r})\n"
    if isinstance(node, BoolNode):
        return f"{pad}Bool({node.value})\n"
    if isinstance(node, VariableNode):
        return f"{pad}Var({node.name})\n"
    if isinstance(node, UnaryOpNode):
        return f"{pad}Unary({node.op})\n" + pretty(node.operand, indent + 1)
    if isinstance(node, BinOpNode):
        return (
            f"{pad}BinOp({node.op})\n"
            + pretty(node.left, indent + 1)
            + pretty(node.right, indent + 1)
        )
    if isinstance(node, FuncCallNode):
        s = f"{pad}Call({node.name})\n"
        for a in node.args:
            s += pretty(a, indent + 1)
        return s
    if isinstance(node, AssignNode):
        return f"{pad}Assign({node.name})\n" + pretty(node.expr, indent + 1)
    if isinstance(node, FuncDefNode):
        s = f"{pad}FuncDef({node.name}, params={node.params})\n"
        s += pretty(node.body, indent + 1)
        return s
    if isinstance(node, IfNode):
        s = f"{pad}If\n"
        s += pretty(node.condition, indent + 1)
        s += f"{pad}  Then:\n" + pretty(node.then_block, indent + 2)
        if node.else_block is not None:
            s += f"{pad}  Else:\n" + pretty(node.else_block, indent + 2)
        return s
    if isinstance(node, WhileNode):
        return (
            f"{pad}While\n"
            + pretty(node.condition, indent + 1)
            + pretty(node.body, indent + 1)
        )
    if isinstance(node, ReturnNode):
        if node.expr is None:
            return f"{pad}Return\n"
        return f"{pad}Return\n" + pretty(node.expr, indent + 1)
    if isinstance(node, PrintNode):
        return f"{pad}Print\n" + pretty(node.expr, indent + 1)
    if isinstance(node, ExprStmtNode):
        return f"{pad}ExprStmt\n" + pretty(node.expr, indent + 1)
    return f"{pad}<unknown {type(node).__name__}>\n"


# ---------- JSON serializer (para render gráfico en el frontend) ----------
def to_json(node: Optional[Node]) -> dict:
    """Convierte el AST a un dict jerárquico {label, kind, children}.

    `kind` se usa en el frontend para colorear el nodo según su categoría.
    `label` es el texto corto que se muestra dentro del nodo.
    `children` es la lista de hijos (en orden) para el layout del árbol.
    """
    if node is None:
        return {"label": "∅", "kind": "none", "children": []}

    if isinstance(node, ProgramNode):
        return {
            "label": "Program",
            "kind": "program",
            "children": [to_json(s) for s in node.statements],
        }
    if isinstance(node, BlockNode):
        return {
            "label": "Block",
            "kind": "block",
            "children": [to_json(s) for s in node.statements],
        }
    if isinstance(node, NumberNode):
        kind_lbl = "Real" if node.is_real else "Int"
        return {
            "label": f"{kind_lbl}({node.value})",
            "kind": "literal",
            "children": [],
        }
    if isinstance(node, StringNode):
        return {
            "label": f"String({node.value!r})",
            "kind": "literal",
            "children": [],
        }
    if isinstance(node, BoolNode):
        return {
            "label": f"Bool({node.value})",
            "kind": "literal",
            "children": [],
        }
    if isinstance(node, VariableNode):
        return {
            "label": f"Var({node.name})",
            "kind": "variable",
            "children": [],
        }
    if isinstance(node, UnaryOpNode):
        return {
            "label": f"Unary({node.op})",
            "kind": "operator",
            "children": [to_json(node.operand)],
        }
    if isinstance(node, BinOpNode):
        return {
            "label": f"BinOp({node.op})",
            "kind": "operator",
            "children": [to_json(node.left), to_json(node.right)],
        }
    if isinstance(node, FuncCallNode):
        return {
            "label": f"Call({node.name})",
            "kind": "call",
            "children": [to_json(a) for a in node.args],
        }
    if isinstance(node, AssignNode):
        return {
            "label": f"Assign({node.name})",
            "kind": "assign",
            "children": [to_json(node.expr)],
        }
    if isinstance(node, FuncDefNode):
        params = ", ".join(node.params)
        return {
            "label": f"FuncDef({node.name}, [{params}])",
            "kind": "funcdef",
            "children": [to_json(node.body)],
        }
    if isinstance(node, IfNode):
        children = [
            {"label": "cond", "kind": "label", "children": [to_json(node.condition)]},
            {"label": "then", "kind": "label", "children": [to_json(node.then_block)]},
        ]
        if node.else_block is not None:
            children.append(
                {"label": "else", "kind": "label", "children": [to_json(node.else_block)]}
            )
        return {"label": "If", "kind": "control", "children": children}
    if isinstance(node, WhileNode):
        return {
            "label": "While",
            "kind": "control",
            "children": [
                {"label": "cond", "kind": "label", "children": [to_json(node.condition)]},
                {"label": "body", "kind": "label", "children": [to_json(node.body)]},
            ],
        }
    if isinstance(node, ReturnNode):
        return {
            "label": "Return",
            "kind": "control",
            "children": [to_json(node.expr)] if node.expr is not None else [],
        }
    if isinstance(node, PrintNode):
        return {
            "label": "Print",
            "kind": "io",
            "children": [to_json(node.expr)],
        }
    if isinstance(node, ExprStmtNode):
        return {
            "label": "ExprStmt",
            "kind": "stmt",
            "children": [to_json(node.expr)],
        }
    return {
        "label": f"<unknown {type(node).__name__}>",
        "kind": "unknown",
        "children": [],
    }
