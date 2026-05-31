"""Pipeline completo: source → tokens → AST → semántico → interpreter.

Útil para la API web y los tests: ejecuta cada fase y devuelve un resultado
con tokens, AST en formato indentado, diagnósticos por fase y salida.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ast_nodes import ProgramNode, pretty, to_json
from .errors import Diagnostic
from .interpreter import Interpreter
from .lexer import tokenize
from .parser import parse
from .semantic import analyze
from .tokens import Token


@dataclass
class PipelineResult:
    tokens: list[Token] = field(default_factory=list)
    ast: ProgramNode | None = None
    ast_pretty: str = ""
    ast_json: dict | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    output: list[str] = field(default_factory=list)
    executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tokens": [t.to_dict() for t in self.tokens],
            "ast": self.ast_pretty,
            "ast_json": self.ast_json,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "output": self.output,
            "executed": self.executed,
        }


def run_source(source: str, *, execute: bool = True) -> PipelineResult:
    result = PipelineResult()

    tokens, lex_errs = tokenize(source)
    result.tokens = tokens
    result.diagnostics.extend(lex_errs)

    ast, syn_errs = parse(tokens)
    result.ast = ast
    result.ast_pretty = pretty(ast)
    result.ast_json = to_json(ast)
    result.diagnostics.extend(syn_errs)

    if syn_errs:
        return result  # no avanzar con AST malformado

    sem_errs = analyze(ast)
    result.diagnostics.extend(sem_errs)

    if not execute or sem_errs or lex_errs:
        return result

    interp = Interpreter()
    out, rt_errs = interp.run(ast)
    result.output = out
    result.diagnostics.extend(rt_errs)
    result.executed = not rt_errs
    return result
