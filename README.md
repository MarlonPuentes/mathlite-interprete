# MathLite — Intérprete con Análisis Semántico

Proyecto Final · Lenguajes Formales, Autómatas e Investigación sobre Implementación de Compiladores · Período Académico 2026-1.

Intérprete completo para **MathLite**, un DSL imperativo de tipado dinámico para cálculos matemáticos. Incluye las fases clásicas de un compilador (léxico → sintáctico → semántico → interpretación), interfaz web, persistencia en MongoDB Atlas y suite de pruebas automatizadas.

## Stack

- **Lenguaje del intérprete:** Python 3.12+
- **Backend web:** FastAPI + Uvicorn
- **Frontend:** HTML + CodeMirror (CDN)
- **Persistencia:** MongoDB Atlas (NoSQL en la nube)
- **Tests:** pytest
- **Despliegue:** Render / Railway

## Estructura

```
.
├── mathlite/        # Intérprete: lexer, parser, AST, semántico, eval, REPL
├── api/             # FastAPI + integración Mongo
├── web/             # Frontend estático
├── tests/           # Suite pytest (≥25 casos)
├── docs/            # Especificación formal, AFD, FIRST/FOLLOW, árboles
└── requirements.txt
```

## Cómo correr en local

```bash
py -m venv .venv
source .venv\Scripts\activate 
pip install -r requirements.txt

# REPL interactivo
python -m mathlite.repl

# API web
cp .env.example .env   # editar con la URI real de Atlas
uvicorn api.main:app --reload
# abrir http://localhost:8000
```

## Lenguaje MathLite — vista rápida

```
-- Declaración de variables
let base = 5
let altura = 3.0

-- Función que calcula el área de un triángulo
def area(b, h) {
  return (b * h) / 2
}

let resultado = area(base, altura)
print(resultado)         -- 7.5

-- Ciclo while
let i = 1
while i <= 5 {
  print(i * i)
  let i = i + 1
}
```

Ver especificación completa en [`docs/spec.md`](docs/spec.md).
