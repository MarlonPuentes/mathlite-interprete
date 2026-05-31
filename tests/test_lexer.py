"""Tests del lexer (Fase 2)."""
from mathlite.lexer import tokenize
from mathlite.tokens import TokenType


def types(src):
    toks, _ = tokenize(src)
    return [t.type for t in toks if t.type is not TokenType.EOF]


def test_lex_keywords_and_idents():
    toks, errs = tokenize("let x = 1")
    assert errs == []
    assert [t.type for t in toks[:-1]] == [
        TokenType.LET, TokenType.IDENT, TokenType.ASSIGN, TokenType.INT,
    ]
    assert toks[1].lexeme == "x"
    assert toks[3].value == 1


def test_lex_real_number():
    toks, errs = tokenize("3.14")
    assert errs == []
    assert toks[0].type is TokenType.REAL
    assert toks[0].value == 3.14


def test_lex_string_literal():
    toks, errs = tokenize('"hola mundo"')
    assert errs == []
    assert toks[0].type is TokenType.STRING
    assert toks[0].value == "hola mundo"


def test_lex_invalid_char_continues():
    toks, errs = tokenize("let x = @ + 1")
    assert any("inválido" in e.message for e in errs)
    # debe seguir tokenizando el resto
    assert TokenType.PLUS in [t.type for t in toks]
    assert TokenType.INT in [t.type for t in toks]


def test_lex_unterminated_string():
    _toks, errs = tokenize('print("hola)')
    assert any("comilla" in e.message for e in errs)


def test_lex_comparison_operators():
    expected = [TokenType.EQ, TokenType.NEQ, TokenType.LE, TokenType.GE,
                TokenType.LT, TokenType.GT]
    toks, _ = tokenize("== != <= >= < >")
    assert [t.type for t in toks[:-1]] == expected


def test_lex_comments_are_ignored():
    toks, errs = tokenize("-- comentario\nlet x = 1")
    assert errs == []
    assert toks[0].type is TokenType.LET
