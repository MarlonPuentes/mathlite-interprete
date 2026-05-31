"""Parser recursivo descendente (LL(1)) de MathLite.

Construye un AST según la gramática EBNF documentada en `docs/spec.md`.
Recoge errores sintácticos en una lista; al encontrar un error intenta
sincronizar saltando hasta el inicio de la siguiente sentencia para no
abortar el análisis.
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
from .tokens import Token, TokenType


class _ParseError(Exception):
    """Excepción interna para sincronización; no escapa del parser."""


# Tokens que inician una sentencia (FIRST(statement)).
_STMT_FIRST = {
    TokenType.LET, TokenType.DEF, TokenType.IF, TokenType.WHILE,
    TokenType.RETURN, TokenType.PRINT, TokenType.IDENT, TokenType.INT,
    TokenType.REAL, TokenType.STRING, TokenType.TRUE, TokenType.FALSE,
    TokenType.LPAREN, TokenType.MINUS, TokenType.NOT,
}


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.errors: list[Diagnostic] = []

    # ---------- helpers ----------
    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]

    def _check(self, *types: TokenType) -> bool:
        return self._peek().type in types

    def _match(self, *types: TokenType) -> Token | None:
        if self._check(*types):
            tok = self._peek()
            self.pos += 1
            return tok
        return None

    def _consume(self, ttype: TokenType, message: str) -> Token:
        if self._check(ttype):
            tok = self._peek()
            self.pos += 1
            return tok
        cur = self._peek()
        self._error(message + f" (encontrado {cur.type.name} {cur.lexeme!r})", cur)
        raise _ParseError()

    def _error(self, message: str, tok: Token) -> None:
        self.errors.append(Diagnostic(ErrorPhase.SYNTAX, message, tok.line, tok.column))

    def _synchronize(self) -> None:
        """Avanza hasta el siguiente inicio de sentencia o '}' o EOF.

        Siempre consume al menos un token para evitar bucles infinitos cuando
        el error se reporta sobre el token actual (ej. '}' suelto al final).
        """
        if not self._check(TokenType.EOF):
            self.pos += 1
        while not self._check(TokenType.EOF):
            if self._peek().type in _STMT_FIRST or self._check(TokenType.RBRACE):
                return
            self.pos += 1

    # ---------- entrada principal ----------
    def parse(self) -> tuple[ProgramNode, list[Diagnostic]]:
        statements: list[Node] = []
        while not self._check(TokenType.EOF):
            try:
                statements.append(self._statement())
            except _ParseError:
                self._synchronize()
        return ProgramNode(statements=statements), self.errors

    # ---------- sentencias ----------
    def _statement(self) -> Node:
        tok = self._peek()
        if tok.type is TokenType.LET:
            return self._let_stmt()
        if tok.type is TokenType.DEF:
            return self._func_def()
        if tok.type is TokenType.IF:
            return self._if_stmt()
        if tok.type is TokenType.WHILE:
            return self._while_stmt()
        if tok.type is TokenType.RETURN:
            return self._return_stmt()
        if tok.type is TokenType.PRINT:
            return self._print_stmt()
        # expression statement
        expr = self._expression()
        return ExprStmtNode(expr=expr, line=expr.line, col=expr.col)

    def _let_stmt(self) -> AssignNode:
        tok = self._consume(TokenType.LET, "se esperaba 'let'")
        name_tok = self._consume(TokenType.IDENT, "se esperaba identificador después de 'let'")
        self._consume(TokenType.ASSIGN, "se esperaba '=' en declaración let")
        expr = self._expression()
        return AssignNode(name=name_tok.lexeme, expr=expr, line=tok.line, col=tok.column)

    def _func_def(self) -> FuncDefNode:
        tok = self._consume(TokenType.DEF, "se esperaba 'def'")
        name_tok = self._consume(TokenType.IDENT, "se esperaba nombre de función")
        self._consume(TokenType.LPAREN, "se esperaba '(' tras nombre de función")
        params: list[str] = []
        if not self._check(TokenType.RPAREN):
            params.append(self._consume(TokenType.IDENT, "se esperaba parámetro").lexeme)
            while self._match(TokenType.COMMA):
                params.append(self._consume(TokenType.IDENT, "se esperaba parámetro").lexeme)
        self._consume(TokenType.RPAREN, "se esperaba ')' al cerrar parámetros")
        body = self._block()
        return FuncDefNode(name=name_tok.lexeme, params=params, body=body,
                           line=tok.line, col=tok.column)

    def _if_stmt(self) -> IfNode:
        tok = self._consume(TokenType.IF, "se esperaba 'if'")
        if self._check(TokenType.LBRACE):
            self._error("'if' requiere condición antes del bloque", tok)
            raise _ParseError()
        cond = self._expression()
        then_block = self._block()
        else_block = None
        if self._match(TokenType.ELSE):
            else_block = self._block()
        return IfNode(condition=cond, then_block=then_block, else_block=else_block,
                      line=tok.line, col=tok.column)

    def _while_stmt(self) -> WhileNode:
        tok = self._consume(TokenType.WHILE, "se esperaba 'while'")
        if self._check(TokenType.LBRACE):
            self._error("'while' requiere condición antes del bloque", tok)
            raise _ParseError()
        cond = self._expression()
        body = self._block()
        return WhileNode(condition=cond, body=body, line=tok.line, col=tok.column)

    def _return_stmt(self) -> ReturnNode:
        tok = self._consume(TokenType.RETURN, "se esperaba 'return'")
        # ¿hay expresión a continuación?
        if self._peek().type in _STMT_FIRST and not self._check(TokenType.RBRACE):
            expr = self._expression()
            return ReturnNode(expr=expr, line=tok.line, col=tok.column)
        return ReturnNode(expr=None, line=tok.line, col=tok.column)

    def _print_stmt(self) -> PrintNode:
        tok = self._consume(TokenType.PRINT, "se esperaba 'print'")
        self._consume(TokenType.LPAREN, "se esperaba '(' tras 'print'")
        expr = self._expression()
        self._consume(TokenType.RPAREN, "se esperaba ')' al cerrar print")
        return PrintNode(expr=expr, line=tok.line, col=tok.column)

    def _block(self) -> BlockNode:
        tok = self._consume(TokenType.LBRACE, "se esperaba '{' para abrir el bloque")
        stmts: list[Node] = []
        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            try:
                stmts.append(self._statement())
            except _ParseError:
                self._synchronize()
        self._consume(TokenType.RBRACE, "se esperaba '}' al cerrar el bloque")
        return BlockNode(statements=stmts, line=tok.line, col=tok.column)

    # ---------- expresiones (precedencia ascendente) ----------
    def _expression(self) -> Node:
        return self._logic_or()

    def _logic_or(self) -> Node:
        left = self._logic_and()
        while self._check(TokenType.OR):
            op_tok = self._peek(); self.pos += 1
            right = self._logic_and()
            left = BinOpNode(op="or", left=left, right=right, line=op_tok.line, col=op_tok.column)
        return left

    def _logic_and(self) -> Node:
        left = self._logic_not()
        while self._check(TokenType.AND):
            op_tok = self._peek(); self.pos += 1
            right = self._logic_not()
            left = BinOpNode(op="and", left=left, right=right, line=op_tok.line, col=op_tok.column)
        return left

    def _logic_not(self) -> Node:
        if self._check(TokenType.NOT):
            tok = self._peek(); self.pos += 1
            operand = self._equality()
            return UnaryOpNode(op="not", operand=operand, line=tok.line, col=tok.column)
        return self._equality()

    def _equality(self) -> Node:
        left = self._comparison()
        while self._check(TokenType.EQ, TokenType.NEQ):
            op_tok = self._peek(); self.pos += 1
            right = self._comparison()
            left = BinOpNode(op=op_tok.lexeme, left=left, right=right,
                             line=op_tok.line, col=op_tok.column)
        return left

    def _comparison(self) -> Node:
        left = self._additive()
        while self._check(TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE):
            op_tok = self._peek(); self.pos += 1
            right = self._additive()
            left = BinOpNode(op=op_tok.lexeme, left=left, right=right,
                             line=op_tok.line, col=op_tok.column)
        return left

    def _additive(self) -> Node:
        left = self._multiplicative()
        while self._check(TokenType.PLUS, TokenType.MINUS):
            op_tok = self._peek(); self.pos += 1
            right = self._multiplicative()
            left = BinOpNode(op=op_tok.lexeme, left=left, right=right,
                             line=op_tok.line, col=op_tok.column)
        return left

    def _multiplicative(self) -> Node:
        left = self._unary()
        while self._check(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_tok = self._peek(); self.pos += 1
            right = self._unary()
            left = BinOpNode(op=op_tok.lexeme, left=left, right=right,
                             line=op_tok.line, col=op_tok.column)
        return left

    def _unary(self) -> Node:
        if self._check(TokenType.MINUS):
            tok = self._peek(); self.pos += 1
            operand = self._power()
            return UnaryOpNode(op="-", operand=operand, line=tok.line, col=tok.column)
        return self._power()

    def _power(self) -> Node:
        base = self._primary()
        if self._check(TokenType.CARET):
            tok = self._peek(); self.pos += 1
            exponent = self._unary()  # asociativa por derecha
            return BinOpNode(op="^", left=base, right=exponent,
                             line=tok.line, col=tok.column)
        return base

    def _primary(self) -> Node:
        tok = self._peek()
        if tok.type is TokenType.INT:
            self.pos += 1
            return NumberNode(value=tok.value, is_real=False, line=tok.line, col=tok.column)
        if tok.type is TokenType.REAL:
            self.pos += 1
            return NumberNode(value=tok.value, is_real=True, line=tok.line, col=tok.column)
        if tok.type is TokenType.STRING:
            self.pos += 1
            return StringNode(value=tok.value, line=tok.line, col=tok.column)
        if tok.type in (TokenType.TRUE, TokenType.FALSE):
            self.pos += 1
            return BoolNode(value=bool(tok.value), line=tok.line, col=tok.column)
        if tok.type is TokenType.LPAREN:
            self.pos += 1
            expr = self._expression()
            self._consume(TokenType.RPAREN, "se esperaba ')'")
            return expr
        if tok.type is TokenType.IDENT or tok.type is TokenType.PRINT:
            # PRINT permitido aquí solo si se usa como llamada (defensivo)
            name = tok.lexeme
            self.pos += 1
            if self._match(TokenType.LPAREN):
                args: list[Node] = []
                if not self._check(TokenType.RPAREN):
                    args.append(self._expression())
                    while self._match(TokenType.COMMA):
                        args.append(self._expression())
                self._consume(TokenType.RPAREN, "se esperaba ')' en llamada a función")
                return FuncCallNode(name=name, args=args, line=tok.line, col=tok.column)
            return VariableNode(name=name, line=tok.line, col=tok.column)

        self._error(f"token inesperado {tok.lexeme!r}", tok)
        raise _ParseError()


def parse(tokens: list[Token]) -> tuple[ProgramNode, list[Diagnostic]]:
    return Parser(tokens).parse()
