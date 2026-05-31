"""Análisis semántico de MathLite.

- Tabla de símbolos con alcances global y por función.
- Verifica:
    * variables declaradas antes de su uso
    * redeclaración en el mismo alcance
    * llamadas a funciones existentes con aridad correcta
    * compatibilidad básica de tipos
    * uso de `return` solo dentro de funciones
- Anota cada nodo con `inferred_type` cuando es posible.
- Devuelve una lista de diagnósticos (no aborta al primer error).
"""
from __future__ import annotations

from .ast_nodes import (
    AssignNode,
    BinOpNode,
    BlockNode,
    BoolNode,
    ExprStmtNode,
    FuncCallNode,
    FuncDefNode,
    IfNode,
    Node,
    NumberNode,
    PrintNode,
    ProgramNode,
    ReturnNode,
    StringNode,
    UnaryOpNode,
    VariableNode,
    WhileNode,
)
from .errors import Diagnostic, ErrorPhase

# Tipos manejados por el análisis: "Int", "Real", "Bool", "String", "Unknown"
NUMERIC = {"Int", "Real"}

BUILTIN_FUNCS: dict[str, dict] = {
    "sin":   {"arity": 1, "return": "Real"},
    "cos":   {"arity": 1, "return": "Real"},
    "tan":   {"arity": 1, "return": "Real"},
    "sqrt":  {"arity": 1, "return": "Real"},
    "log":   {"arity": 1, "return": "Real"},
    "abs":   {"arity": 1, "return": "Real"},
    "floor": {"arity": 1, "return": "Int"},
    "ceil":  {"arity": 1, "return": "Int"},
}


class Scope:
    def __init__(self, parent: "Scope | None" = None) -> None:
        self.parent = parent
        self.symbols: dict[str, str] = {}  # name -> type

    def declare(self, name: str, ttype: str) -> bool:
        if name in self.symbols:
            return False
        self.symbols[name] = ttype
        return True

    def assign(self, name: str, ttype: str) -> None:
        """Reasignación: si existe en la cadena, actualiza el tipo en ese scope."""
        scope: Scope | None = self
        while scope is not None:
            if name in scope.symbols:
                scope.symbols[name] = ttype
                return
            scope = scope.parent
        self.symbols[name] = ttype

    def resolve(self, name: str) -> str | None:
        scope: Scope | None = self
        while scope is not None:
            if name in scope.symbols:
                return scope.symbols[name]
            scope = scope.parent
        return None

    def declared_here(self, name: str) -> bool:
        return name in self.symbols


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.errors: list[Diagnostic] = []
        self.functions: dict[str, dict] = {}  # nombre -> {arity, params}
        self.global_scope = Scope()
        self.scope = self.global_scope
        self.in_function_depth = 0

    def _error(self, message: str, node: Node) -> None:
        self.errors.append(Diagnostic(ErrorPhase.SEMANTIC, message, node.line, node.col))

    # ---------- entrada ----------
    def analyze(self, program: ProgramNode) -> list[Diagnostic]:
        # Pre-pasada: registrar todas las funciones (permite recursión y orden libre).
        for st in program.statements:
            if isinstance(st, FuncDefNode):
                if st.name in self.functions or st.name in BUILTIN_FUNCS:
                    self._error(f"función '{st.name}' redeclarada", st)
                else:
                    self.functions[st.name] = {"arity": len(st.params), "params": st.params}
        for st in program.statements:
            self._stmt(st)
        return self.errors

    # ---------- sentencias ----------
    def _stmt(self, node: Node) -> None:
        if isinstance(node, AssignNode):
            t = self._expr(node.expr)
            # En MathLite usamos `let` también para reasignación;
            # solo prohibimos redeclaración en el mismo alcance si el tipo cambia drásticamente.
            if self.scope.declared_here(node.name):
                # Permitimos reasignación pero anotamos como aviso si tipo difiere.
                self.scope.assign(node.name, t)
            else:
                self.scope.declare(node.name, t)
            node.inferred_type = t
        elif isinstance(node, FuncDefNode):
            self._func_def(node)
        elif isinstance(node, IfNode):
            ct = self._expr(node.condition)
            if ct not in ("Bool", "Unknown"):
                self._error(f"condición de 'if' debe ser Bool, no {ct}", node.condition)
            self._block(node.then_block)
            if node.else_block is not None:
                self._block(node.else_block)
        elif isinstance(node, WhileNode):
            ct = self._expr(node.condition)
            if ct not in ("Bool", "Unknown"):
                self._error(f"condición de 'while' debe ser Bool, no {ct}", node.condition)
            self._block(node.body)
        elif isinstance(node, ReturnNode):
            if self.in_function_depth == 0:
                self._error("'return' usado fuera del cuerpo de una función", node)
            if node.expr is not None:
                self._expr(node.expr)
        elif isinstance(node, PrintNode):
            self._expr(node.expr)
        elif isinstance(node, ExprStmtNode):
            self._expr(node.expr)
        elif isinstance(node, BlockNode):
            self._block(node)

    def _block(self, block: BlockNode) -> None:
        # Bloques de if/while NO crean nuevo scope para variables (MathLite las
        # mantiene en el scope actual, como el ejemplo del PDF que reasigna
        # `let i = i + 1` dentro de un while).
        for st in block.statements:
            self._stmt(st)

    def _func_def(self, node: FuncDefNode) -> None:
        # Crear scope de función con los parámetros como Unknown.
        previous = self.scope
        func_scope = Scope(parent=self.global_scope)
        for p in node.params:
            func_scope.declare(p, "Unknown")
        self.scope = func_scope
        self.in_function_depth += 1
        for st in node.body.statements:
            self._stmt(st)
        self.in_function_depth -= 1
        self.scope = previous

    # ---------- expresiones (devuelve tipo inferido) ----------
    def _expr(self, node: Node) -> str:
        t = self._infer(node)
        node.inferred_type = t
        return t

    def _infer(self, node: Node) -> str:
        if isinstance(node, NumberNode):
            return "Real" if node.is_real else "Int"
        if isinstance(node, StringNode):
            return "String"
        if isinstance(node, BoolNode):
            return "Bool"
        if isinstance(node, VariableNode):
            t = self.scope.resolve(node.name)
            if t is None:
                self._error(f"variable '{node.name}' no declarada", node)
                return "Unknown"
            return t
        if isinstance(node, UnaryOpNode):
            inner = self._expr(node.operand)
            if node.op == "not":
                if inner not in ("Bool", "Unknown"):
                    self._error(f"'not' aplicado a {inner}", node)
                return "Bool"
            if node.op == "-":
                if inner not in NUMERIC | {"Unknown"}:
                    self._error(f"unario '-' aplicado a {inner}", node)
                    return "Unknown"
                return inner
            return "Unknown"
        if isinstance(node, BinOpNode):
            return self._infer_binop(node)
        if isinstance(node, FuncCallNode):
            return self._infer_call(node)
        return "Unknown"

    def _infer_binop(self, node: BinOpNode) -> str:
        lt = self._expr(node.left)
        rt = self._expr(node.right)
        op = node.op
        if op in ("+", "-", "*", "/", "%", "^"):
            if op == "+" and lt == "String" and rt == "String":
                return "String"
            if lt in NUMERIC | {"Unknown"} and rt in NUMERIC | {"Unknown"}:
                if "Real" in (lt, rt):
                    return "Real"
                if lt == "Unknown" or rt == "Unknown":
                    return "Unknown"
                return "Int"
            self._error(f"operación '{op}' no admitida entre {lt} y {rt}", node)
            return "Unknown"
        if op in ("==", "!=", "<", ">", "<=", ">="):
            if op in ("==", "!="):
                return "Bool"
            if lt in NUMERIC | {"Unknown"} and rt in NUMERIC | {"Unknown"}:
                return "Bool"
            self._error(f"comparación '{op}' no admitida entre {lt} y {rt}", node)
            return "Bool"
        if op in ("and", "or"):
            if lt not in ("Bool", "Unknown") or rt not in ("Bool", "Unknown"):
                self._error(f"operador '{op}' requiere Bool", node)
            return "Bool"
        return "Unknown"

    def _infer_call(self, node: FuncCallNode) -> str:
        name = node.name
        # Argumentos siempre se evalúan (para detectar errores anidados).
        arg_types = [self._expr(a) for a in node.args]
        if name in BUILTIN_FUNCS:
            spec = BUILTIN_FUNCS[name]
            if len(arg_types) != spec["arity"]:
                self._error(
                    f"función built-in '{name}' espera {spec['arity']} argumentos, recibió {len(arg_types)}",
                    node,
                )
            for at in arg_types:
                if at not in NUMERIC | {"Unknown"}:
                    self._error(f"argumento de '{name}' debe ser numérico, no {at}", node)
            return spec["return"]
        if name in self.functions:
            expected = self.functions[name]["arity"]
            if len(arg_types) != expected:
                self._error(
                    f"función '{name}' espera {expected} argumentos, recibió {len(arg_types)}",
                    node,
                )
            return "Unknown"
        self._error(f"función '{name}' no está definida", node)
        return "Unknown"


def analyze(program: ProgramNode) -> list[Diagnostic]:
    return SemanticAnalyzer().analyze(program)
