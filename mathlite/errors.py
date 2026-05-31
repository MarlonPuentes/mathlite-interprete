"""Errores y diagnósticos del intérprete MathLite."""
from dataclasses import dataclass
from enum import Enum


class ErrorPhase(str, Enum):
    LEXICAL = "lexical"
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    RUNTIME = "runtime"


@dataclass
class Diagnostic:
    phase: ErrorPhase
    message: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"[{self.phase.value}] line {self.line}:{self.column} — {self.message}"

    def to_dict(self) -> dict:
        return {
            "phase": self.phase.value,
            "message": self.message,
            "line": self.line,
            "column": self.column,
        }


class MathLiteError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(str(diagnostic))
        self.diagnostic = diagnostic


class LexicalError(MathLiteError):
    pass


class SyntaxError_(MathLiteError):
    pass


class SemanticError(MathLiteError):
    pass


class RuntimeError_(MathLiteError):
    pass


class ReturnSignal(Exception):
    """Señal interna usada por el intérprete para propagar `return`."""

    def __init__(self, value):
        self.value = value
