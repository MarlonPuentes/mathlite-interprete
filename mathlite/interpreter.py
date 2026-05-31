"""Intérprete tree-walking de MathLite.

Recorre el AST con un patrón Visitor implícito (despacho por isinstance).
Mantiene un `Environment` por llamada de función (paso por valor).
"""
from __future__ import annotations

import math
from typing import Any, Callable

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
from .errors import Diagnostic, ErrorPhase, ReturnSignal, RuntimeError_


class Environment:
    def __init__(self, parent: "Environment | None" = None) -> None:
        self.parent = parent
        self.vars: dict[str, Any] = {}

    def get(self, name: str) -> Any:
        if name in self.vars:
            return self.vars[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise KeyError(name)

    def set(self, name: str, value: Any) -> None:
        # Si existe en cadena, actualizar ahí; si no, crear en el scope actual.
        env: Environment | None = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = value
                return
            env = env.parent
        self.vars[name] = value

    def declare(self, name: str, value: Any) -> None:
        self.vars[name] = value


BUILTINS: dict[str, Callable[..., Any]] = {
    "sin":   math.sin,
    "cos":   math.cos,
    "tan":   math.tan,
    "sqrt":  math.sqrt,
    "log":   math.log,
    "abs":   abs,
    "floor": math.floor,
    "ceil":  math.ceil,
}


class Interpreter:
    def __init__(self) -> None:
        self.global_env = Environment()
        self.functions: dict[str, FuncDefNode] = {}
        self.output: list[str] = []

    # ---------- API pública ----------
    def run(self, program: ProgramNode) -> tuple[list[str], list[Diagnostic]]:
        # Registrar funciones primero (permite recursión + uso antes de def).
        for st in program.statements:
            if isinstance(st, FuncDefNode):
                self.functions[st.name] = st

        errors: list[Diagnostic] = []
        try:
            for st in program.statements:
                if isinstance(st, FuncDefNode):
                    continue  # ya registrada
                self._exec(st, self.global_env)
        except RuntimeError_ as e:
            errors.append(e.diagnostic)
        return self.output, errors

    def eval_expression(self, expr: Node) -> Any:
        return self._eval(expr, self.global_env)

    # ---------- ejecución de sentencias ----------
    def _exec(self, node: Node, env: Environment) -> None:
        if isinstance(node, AssignNode):
            value = self._eval(node.expr, env)
            env.set(node.name, value)
            return
        if isinstance(node, IfNode):
            cond = self._eval(node.condition, env)
            if self._truthy(cond):
                self._exec_block(node.then_block, env)
            elif node.else_block is not None:
                self._exec_block(node.else_block, env)
            return
        if isinstance(node, WhileNode):
            # Guarda para evitar bucles infinitos accidentales en demo (configurable).
            max_iter = 1_000_000
            i = 0
            while self._truthy(self._eval(node.condition, env)):
                self._exec_block(node.body, env)
                i += 1
                if i > max_iter:
                    raise RuntimeError_(Diagnostic(
                        ErrorPhase.RUNTIME,
                        f"while excedió {max_iter} iteraciones (posible bucle infinito)",
                        node.line, node.col,
                    ))
            return
        if isinstance(node, ReturnNode):
            value = self._eval(node.expr, env) if node.expr is not None else None
            raise ReturnSignal(value)
        if isinstance(node, PrintNode):
            value = self._eval(node.expr, env)
            self.output.append(self._format(value))
            return
        if isinstance(node, ExprStmtNode):
            self._eval(node.expr, env)
            return
        if isinstance(node, BlockNode):
            self._exec_block(node, env)
            return
        if isinstance(node, FuncDefNode):
            self.functions[node.name] = node
            return

    def _exec_block(self, block: BlockNode, env: Environment) -> None:
        for st in block.statements:
            self._exec(st, env)

    # ---------- evaluación de expresiones ----------
    def _eval(self, node: Node, env: Environment) -> Any:
        if isinstance(node, NumberNode):
            return node.value
        if isinstance(node, StringNode):
            return node.value
        if isinstance(node, BoolNode):
            return node.value
        if isinstance(node, VariableNode):
            try:
                return env.get(node.name)
            except KeyError:
                raise RuntimeError_(Diagnostic(
                    ErrorPhase.RUNTIME, f"variable '{node.name}' no definida",
                    node.line, node.col,
                ))
        if isinstance(node, UnaryOpNode):
            v = self._eval(node.operand, env)
            if node.op == "-":
                return -v
            if node.op == "not":
                return not self._truthy(v)
        if isinstance(node, BinOpNode):
            return self._eval_binop(node, env)
        if isinstance(node, FuncCallNode):
            return self._eval_call(node, env)
        raise RuntimeError_(Diagnostic(
            ErrorPhase.RUNTIME, f"nodo no soportado: {type(node).__name__}",
            node.line, node.col,
        ))

    def _eval_binop(self, node: BinOpNode, env: Environment) -> Any:
        op = node.op
        # Short-circuit para and/or
        if op == "and":
            l = self._eval(node.left, env)
            if not self._truthy(l):
                return False
            return self._truthy(self._eval(node.right, env))
        if op == "or":
            l = self._eval(node.left, env)
            if self._truthy(l):
                return True
            return self._truthy(self._eval(node.right, env))

        l = self._eval(node.left, env)
        r = self._eval(node.right, env)
        try:
            if op == "+":
                if isinstance(l, str) and isinstance(r, str):
                    return l + r
                return l + r
            if op == "-": return l - r
            if op == "*": return l * r
            if op == "/":
                if r == 0:
                    raise RuntimeError_(Diagnostic(
                        ErrorPhase.RUNTIME, "división por cero", node.line, node.col,
                    ))
                # Si ambos enteros y división exacta, mantener int (estilo PDF: 7.5 sale de real)
                if isinstance(l, int) and isinstance(r, int) and l % r == 0:
                    return l // r
                return l / r
            if op == "%":
                if r == 0:
                    raise RuntimeError_(Diagnostic(
                        ErrorPhase.RUNTIME, "módulo por cero", node.line, node.col,
                    ))
                return l % r
            if op == "^": return l ** r
            if op == "==": return l == r
            if op == "!=": return l != r
            if op == "<":  return l < r
            if op == ">":  return l > r
            if op == "<=": return l <= r
            if op == ">=": return l >= r
        except RuntimeError_:
            raise
        except TypeError as e:
            raise RuntimeError_(Diagnostic(
                ErrorPhase.RUNTIME, f"operación '{op}' inválida: {e}",
                node.line, node.col,
            ))
        raise RuntimeError_(Diagnostic(
            ErrorPhase.RUNTIME, f"operador desconocido '{op}'", node.line, node.col,
        ))

    def _eval_call(self, node: FuncCallNode, env: Environment) -> Any:
        args = [self._eval(a, env) for a in node.args]
        if node.name in BUILTINS:
            try:
                return BUILTINS[node.name](*args)
            except (ValueError, ZeroDivisionError, TypeError) as e:
                raise RuntimeError_(Diagnostic(
                    ErrorPhase.RUNTIME,
                    f"error en '{node.name}': {e}", node.line, node.col,
                ))
        if node.name not in self.functions:
            raise RuntimeError_(Diagnostic(
                ErrorPhase.RUNTIME, f"función '{node.name}' no definida",
                node.line, node.col,
            ))
        func = self.functions[node.name]
        if len(args) != len(func.params):
            raise RuntimeError_(Diagnostic(
                ErrorPhase.RUNTIME,
                f"función '{node.name}' espera {len(func.params)} argumentos, recibió {len(args)}",
                node.line, node.col,
            ))
        call_env = Environment(parent=self.global_env)
        for p, v in zip(func.params, args):
            call_env.declare(p, v)
        try:
            self._exec_block(func.body, call_env)
        except ReturnSignal as r:
            return r.value
        return None

    # ---------- utilidades ----------
    @staticmethod
    def _truthy(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        return value is not None

    @staticmethod
    def _format(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return "nil"
        return str(value)


def run(program: ProgramNode) -> tuple[list[str], list[Diagnostic]]:
    return Interpreter().run(program)
