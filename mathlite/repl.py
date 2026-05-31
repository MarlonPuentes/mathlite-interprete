"""REPL interactivo de MathLite.

Permite ingresar línea a línea (o bloques con `:multi`) y muestra resultados,
errores y diagnósticos al instante. Mantiene el estado entre líneas.
"""
from __future__ import annotations

import sys

from .ast_nodes import ExprStmtNode, ProgramNode
from .interpreter import Interpreter
from .lexer import tokenize
from .parser import parse
from .semantic import analyze


BANNER = (
    "MathLite REPL — Ctrl+D o ':quit' para salir.\n"
    "Comandos: :multi (modo varias líneas hasta línea vacía), :ast <expr>, :tokens <code>\n"
)


def _exec_source(source: str, interp: Interpreter) -> None:
    toks, lex_errs = tokenize(source)
    for e in lex_errs:
        print(e)
    ast, syn_errs = parse(toks)
    for e in syn_errs:
        print(e)
    if syn_errs:
        return
    sem_errs = analyze(ast)
    for e in sem_errs:
        print(e)
    if sem_errs:
        return
    # Si la única sentencia es una expresión simple, imprimir su valor.
    if (
        isinstance(ast, ProgramNode)
        and len(ast.statements) == 1
        and isinstance(ast.statements[0], ExprStmtNode)
    ):
        try:
            value = interp.eval_expression(ast.statements[0].expr)
            if value is not None:
                print(Interpreter._format(value))
        except Exception as e:
            print(f"[runtime] {e}")
        return
    try:
        out, rt_errs = interp.run(ast)
        for line in out:
            print(line)
        for e in rt_errs:
            print(e)
    except Exception as e:
        print(f"[runtime] {e}")


def main() -> None:
    interp = Interpreter()
    print(BANNER)
    while True:
        try:
            line = input(">>> ")
        except EOFError:
            print()
            return
        if line.strip() in (":quit", ":q"):
            return
        if line.strip() == ":multi":
            buf = []
            print("(modo multi-línea — termina con línea vacía)")
            while True:
                try:
                    sub = input("... ")
                except EOFError:
                    break
                if sub == "":
                    break
                buf.append(sub)
            _exec_source("\n".join(buf), interp)
            continue
        if line.startswith(":tokens "):
            from .lexer import dump_tokens
            print(dump_tokens(line[len(":tokens "):]))
            continue
        if line.startswith(":ast "):
            from .ast_nodes import pretty
            toks, _ = tokenize(line[len(":ast "):])
            ast, _ = parse(toks)
            print(pretty(ast))
            continue
        if line.strip() == "":
            continue
        _exec_source(line, interp)


if __name__ == "__main__":
    main()
