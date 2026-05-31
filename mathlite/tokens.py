"""Definición de tipos de token de MathLite."""
from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # Literales
    INT = auto()
    REAL = auto()
    STRING = auto()
    TRUE = auto()
    FALSE = auto()

    # Identificadores y palabras reservadas
    IDENT = auto()
    LET = auto()
    DEF = auto()
    RETURN = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    PRINT = auto()

    # Operadores aritméticos
    PLUS = auto()       # +
    MINUS = auto()      # -
    STAR = auto()       # *
    SLASH = auto()      # /
    PERCENT = auto()    # %
    CARET = auto()      # ^

    # Operadores relacionales
    EQ = auto()         # ==
    NEQ = auto()        # !=
    LT = auto()         # <
    GT = auto()         # >
    LE = auto()         # <=
    GE = auto()         # >=

    # Asignación
    ASSIGN = auto()     # =

    # Delimitadores
    LPAREN = auto()     # (
    RPAREN = auto()     # )
    LBRACE = auto()     # {
    RBRACE = auto()     # }
    COMMA = auto()      # ,

    # Fin de archivo
    EOF = auto()


KEYWORDS: dict[str, TokenType] = {
    "let": TokenType.LET,
    "def": TokenType.DEF,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "print": TokenType.PRINT,
}


@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int
    value: object = None  # valor interpretado (int, float, str, bool)

    def __repr__(self) -> str:
        v = f" value={self.value!r}" if self.value is not None else ""
        return f"Token({self.type.name}, {self.lexeme!r}, {self.line}:{self.column}{v})"

    def to_dict(self) -> dict:
        return {
            "type": self.type.name,
            "lexeme": self.lexeme,
            "line": self.line,
            "column": self.column,
            "value": self.value if not isinstance(self.value, bool) else self.value,
        }
