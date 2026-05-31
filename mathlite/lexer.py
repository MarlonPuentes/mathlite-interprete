"""Analizador léxico de MathLite.

Implementa el reconocimiento de tokens según los AFD documentados en
`docs/spec.md`. No usa generadores; el escaneo es carácter a carácter.

Si encuentra un carácter inválido o una cadena sin cerrar, registra un
`Diagnostic` léxico y continúa con el siguiente carácter para no abortar.
"""
from __future__ import annotations

from .errors import Diagnostic, ErrorPhase
from .tokens import KEYWORDS, Token, TokenType


class Lexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []
        self.errors: list[Diagnostic] = []

    # ---------- helpers ----------
    def _peek(self, offset: int = 0) -> str:
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else ""

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _add(self, ttype: TokenType, lexeme: str, line: int, col: int, value=None) -> None:
        self.tokens.append(Token(ttype, lexeme, line, col, value))

    def _error(self, message: str, line: int, col: int) -> None:
        self.errors.append(Diagnostic(ErrorPhase.LEXICAL, message, line, col))

    # ---------- main entry ----------
    def tokenize(self) -> tuple[list[Token], list[Diagnostic]]:
        while self.pos < len(self.source):
            ch = self._peek()

            # Whitespace
            if ch in " \t\r\n":
                self._advance()
                continue

            # Comentarios "-- ..."
            if ch == "-" and self._peek(1) == "-":
                while self.pos < len(self.source) and self._peek() != "\n":
                    self._advance()
                continue

            line, col = self.line, self.col

            # Identificadores / palabras reservadas
            if ch.isalpha() or ch == "_":
                self._scan_ident(line, col)
                continue

            # Números
            if ch.isdigit():
                self._scan_number(line, col)
                continue

            # Cadenas
            if ch == '"':
                self._scan_string(line, col)
                continue

            # Operadores y delimitadores
            if self._scan_operator(line, col):
                continue

            # Carácter inválido
            self._error(f"carácter inválido {ch!r}", line, col)
            self._advance()

        self._add(TokenType.EOF, "", self.line, self.col)
        return self.tokens, self.errors

    # ---------- scanners ----------
    def _scan_ident(self, line: int, col: int) -> None:
        start = self.pos
        while self.pos < len(self.source) and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        lexeme = self.source[start:self.pos]
        ttype = KEYWORDS.get(lexeme, TokenType.IDENT)
        value = None
        if ttype is TokenType.TRUE:
            value = True
        elif ttype is TokenType.FALSE:
            value = False
        self._add(ttype, lexeme, line, col, value)

    def _scan_number(self, line: int, col: int) -> None:
        start = self.pos
        while self.pos < len(self.source) and self._peek().isdigit():
            self._advance()
        # Posible parte decimal
        if self._peek() == "." and self._peek(1).isdigit():
            self._advance()  # consumir '.'
            while self.pos < len(self.source) and self._peek().isdigit():
                self._advance()
            lexeme = self.source[start:self.pos]
            self._add(TokenType.REAL, lexeme, line, col, float(lexeme))
        else:
            lexeme = self.source[start:self.pos]
            self._add(TokenType.INT, lexeme, line, col, int(lexeme))

    def _scan_string(self, line: int, col: int) -> None:
        self._advance()  # consume "
        start = self.pos
        while self.pos < len(self.source) and self._peek() != '"' and self._peek() != "\n":
            self._advance()
        if self.pos >= len(self.source) or self._peek() == "\n":
            self._error("cadena sin comilla de cierre", line, col)
            # No consumimos el \n; el siguiente paso seguirá tokenizando.
            value = self.source[start:self.pos]
            self._add(TokenType.STRING, '"' + value, line, col, value)
            return
        value = self.source[start:self.pos]
        self._advance()  # consume "
        self._add(TokenType.STRING, '"' + value + '"', line, col, value)

    def _scan_operator(self, line: int, col: int) -> bool:
        """Devuelve True si consumió uno o dos chars como operador."""
        ch = self._peek()
        nxt = self._peek(1)

        # Operadores de dos caracteres
        two = ch + nxt
        two_map = {
            "==": TokenType.EQ,
            "!=": TokenType.NEQ,
            "<=": TokenType.LE,
            ">=": TokenType.GE,
        }
        if two in two_map:
            self._advance(); self._advance()
            self._add(two_map[two], two, line, col)
            return True

        single_map = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "%": TokenType.PERCENT,
            "^": TokenType.CARET,
            "<": TokenType.LT,
            ">": TokenType.GT,
            "=": TokenType.ASSIGN,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            ",": TokenType.COMMA,
        }
        if ch in single_map:
            self._advance()
            self._add(single_map[ch], ch, line, col)
            return True

        # '!' suelto sin '=' → error específico
        if ch == "!":
            self._error("operador '!' debe ir seguido de '='", line, col)
            self._advance()
            return True

        return False


def tokenize(source: str) -> tuple[list[Token], list[Diagnostic]]:
    """Función conveniente."""
    return Lexer(source).tokenize()


def dump_tokens(source: str) -> str:
    """Helper para mostrar el flujo de tokens (usado en pruebas y demo)."""
    toks, errs = tokenize(source)
    lines = [repr(t) for t in toks]
    if errs:
        lines.append("--- errores ---")
        lines += [str(e) for e in errs]
    return "\n".join(lines)


if __name__ == "__main__":  # demo CLI
    import sys
    src = sys.stdin.read() if not sys.argv[1:] else open(sys.argv[1]).read()
    print(dump_tokens(src))
