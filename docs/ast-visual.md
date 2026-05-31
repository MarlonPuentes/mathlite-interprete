# AST de MathLite — funcionamiento y representación gráfica

Este documento describe cómo se construye el árbol de sintaxis abstracta (AST) en MathLite y cómo el frontend lo dibuja en la pestaña **AST** del IDE web.

## 1. Qué es el AST

El AST (*Abstract Syntax Tree*) es la representación jerárquica del programa fuente después del análisis sintáctico. Cada nodo describe una construcción del lenguaje (asignación, llamada, operador binario, bloque, etc.) y referencia a sus hijos. A diferencia de la lista plana de tokens, el AST captura la estructura anidada del código — qué expresión está dentro de qué sentencia, qué operador tiene mayor precedencia, qué pertenece al cuerpo de qué función.

## 2. Pipeline de generación

El AST se obtiene en la segunda fase del pipeline definido en `mathlite/pipeline.py`:

```
source ──► tokenize ──► parse ──► (AST) ──► semántico ──► interpreter
```

1. El **lexer** (`mathlite/lexer.py`) convierte el código fuente en una lista de tokens.
2. El **parser** (`mathlite/parser.py`) consume los tokens siguiendo la gramática del lenguaje y construye los nodos definidos en `mathlite/ast_nodes.py`.
3. El resultado (un `ProgramNode` raíz con sus hijos) se serializa de dos formas para el frontend:
   - `ast_pretty` — texto indentado, útil para depuración.
   - `ast_json` — diccionario jerárquico `{label, kind, children}`, pensado para dibujar el árbol.

## 3. Tipos de nodos

Todos los nodos heredan de la clase base `Node` y guardan `line`/`col` para reportar errores con precisión. Las categorías son:

**Expresiones**
- `NumberNode` — literal entero o real (`is_real` distingue ambos).
- `StringNode`, `BoolNode` — literales de cadena y booleano.
- `VariableNode` — referencia a una variable por nombre.
- `UnaryOpNode` — operador unario (`-x`, `!x`).
- `BinOpNode` — operador binario (`a + b`, `a * b`, comparaciones).
- `FuncCallNode` — llamada a función con lista de argumentos.

**Sentencias**
- `AssignNode` — declaración/asignación `let nombre = expr`.
- `FuncDefNode` — definición `def nombre(params) { body }`.
- `IfNode` — condicional con bloque `then` y opcional `else`.
- `WhileNode` — bucle con condición y cuerpo.
- `ReturnNode`, `PrintNode`, `ExprStmtNode` — sentencias de control y de E/S.

**Contenedores**
- `BlockNode` — secuencia de sentencias dentro de `{ }`.
- `ProgramNode` — raíz del árbol; contiene las sentencias top-level.

## 4. Serialización JSON para el frontend

La función `to_json(node)` en `mathlite/ast_nodes.py` recorre el AST recursivamente y produce un diccionario con tres campos por nodo:

| Campo | Propósito |
|-------|-----------|
| `label` | Texto corto que se muestra dentro del nodo (`"Assign(base)"`, `"BinOp(*)"`, `"Int(5)"`). |
| `kind` | Categoría para colorear el nodo (`program`, `block`, `assign`, `funcdef`, `control`, `operator`, `call`, `variable`, `literal`, `io`, `stmt`, `label`). |
| `children` | Lista ordenada de hijos (ya serializados). |

Por ejemplo, el programa:

```mathlite
let base = 5
def area(b, h) { return (b * h) / 2 }
print(area(base, 3))
```

produce un `ast_json` cuya raíz es:

```json
{
  "label": "Program",
  "kind": "program",
  "children": [
    { "label": "Assign(base)", "kind": "assign", "children": [
        { "label": "Int(5)", "kind": "literal", "children": [] }
    ]},
    { "label": "FuncDef(area, [b, h])", "kind": "funcdef", "children": [
        { "label": "Block", "kind": "block", "children": [
            { "label": "Return", "kind": "control", "children": [
                { "label": "BinOp(/)", "kind": "operator", "children": [...] }
            ]}
        ]}
    ]},
    { "label": "Print", "kind": "io", "children": [
        { "label": "Call(area)", "kind": "call", "children": [
            { "label": "Var(base)", "kind": "variable", "children": [] },
            { "label": "Int(3)",   "kind": "literal",  "children": [] }
        ]}
    ]}
  ]
}
```

Las construcciones con varias ramas semánticamente distintas (`if`, `while`) inyectan **nodos etiqueta** (`cond`, `then`, `else`, `body`) entre el padre y los sub-árboles para que el dibujo refleje el rol de cada rama.

## 5. Cómo se grafica el árbol

El render vive en `web/app.js`, función `renderAstGraph(astJson)`. Usa **D3.js v7** para el layout y dibuja directamente sobre SVG.

### 5.1. Construcción de la jerarquía

```js
const root = d3.hierarchy(astJson, (d) => d.children);
```

`d3.hierarchy` convierte el diccionario en un objeto navegable que sabe quién es padre/hijo, profundidad de cada nodo, etc.

### 5.2. Cálculo del layout

```js
d3.tree()
  .nodeSize([maxW + hGap, vGap])
  .separation((a, b) => (a.parent === b.parent ? 1 : 1.2))
  (root);
```

`d3.tree()` asigna coordenadas `(x, y)` a cada nodo siguiendo el algoritmo **Reingold–Tilford**: árbol top-down, hermanos lado a lado, sin solapamiento. Se usa `nodeSize` (no `size`) porque permite que el árbol crezca tanto como necesite sin comprimirse al contenedor; el ancho real depende del label más largo del árbol.

### 5.3. Dimensiones intrínsecas del SVG

Tras el layout, se calcula el *bounding box* real de todos los nodos:

```js
let x0 = +Infinity, x1 = -Infinity, y1 = -Infinity;
root.each((d) => { if (d.x < x0) x0 = d.x; if (d.x > x1) x1 = d.x; if (d.y > y1) y1 = d.y; });
const svgW = (x1 - x0) + maxW + pad * 2;
const svgH = y1 + nodeH + pad * 2;
```

El `<svg>` se crea con `width` y `height` en píxeles exactos, no en porcentaje. Esto es deliberado: el árbol determina su tamaño y el panel hace scroll si es mayor que la pantalla. Así el render no depende de que la pestaña AST esté visible al momento de dibujarse.

### 5.4. Líneas (links)

```js
const linkGen = d3.linkVertical().x(d => d.x).y(d => d.y);
g.append("g").attr("class", "links")
  .selectAll("path").data(root.links())
  .join("path").attr("class", "link").attr("d", linkGen);
```

`linkVertical` genera curvas Bézier suaves de padre a hijo, dando al árbol un aspecto orgánico en lugar de zig-zag de ángulos rectos.

### 5.5. Nodos

```js
const nodes = g.append("g").attr("class", "nodes")
  .selectAll("g").data(root.descendants())
  .join("g")
  .attr("class", d => `node ${d.data.kind || "unknown"}`)
  .attr("transform", d => `translate(${d.x},${d.y})`);

nodes.append("rect")
  .attr("height", nodeH)
  .attr("y", -nodeH / 2)
  .attr("width", d => d._w)
  .attr("x", d => -d._w / 2)
  .attr("rx", 6).attr("ry", 6);

nodes.append("text")
  .attr("text-anchor", "middle")
  .attr("dominant-baseline", "middle")
  .text(d => d.data.label);
```

Cada nodo es un grupo `<g>` que contiene un `<rect>` redondeado y un `<text>` centrado. El ancho del rectángulo se calcula a partir de la longitud del label (`Math.max(70, label.length * 7.5 + 22)`) para que cualquier texto quepa sin recortes.

### 5.6. Colores por categoría

El color de cada caja se aplica vía CSS usando la clase `kind` del nodo (`web/style.css`):

| Categoría | Color | Significado |
|-----------|-------|-------------|
| `program` / `block` | azul claro / lila | Contenedores estructurales |
| `assign` | azul | Asignaciones `let` |
| `funcdef` | cian | Definiciones de función |
| `control` | púrpura | `if`, `while`, `return` |
| `operator` | naranja | Operadores binarios/unarios |
| `call` | verde | Llamadas a función |
| `variable` | turquesa | Referencias a variables |
| `literal` | amarillo | Números, strings, booleanos |
| `io` | rosa | `print` |
| `label` | gris oscuro | Etiquetas `cond`/`then`/`else`/`body` |

Esta codificación permite identificar la estructura del programa de un vistazo: las hojas amarillas son literales, las naranjas son cómputo, las verdes son llamadas, las azules son almacenamiento.

### 5.7. Interacción

El SVG está envuelto en `d3.zoom()` con factor de escala entre 0.3× y 3×. Esto habilita:

- **Zoom**: rueda del ratón.
- **Pan**: arrastrar con el botón izquierdo.

No hay botones en la interfaz para mantener el panel limpio. El árbol también es scrolleable verticalmente si excede el alto del panel.

### 5.8. Parser de fallback

Como medida defensiva, `parseAstText(text)` en `web/app.js` reconstruye el JSON jerárquico a partir del texto indentado `ast_pretty`. Esto permite que el dibujo funcione aunque el backend (versión vieja) no envíe `ast_json`. La función reasigna `kind` heurísticamente con `kindFromLabel(label)`.

## 6. Flujo end-to-end

```
┌──────────────┐  POST /api/run  ┌──────────────┐
│  Editor JS   │ ───────────────►│  FastAPI     │
└──────────────┘                 └──────┬───────┘
                                        │
                                  pipeline.run_source(src)
                                        │
                            ┌───────────┴───────────┐
                            ▼                       ▼
                     ast_pretty (texto)     ast_json (dict)
                            │                       │
                            └───────────┬───────────┘
                                        ▼
                            JSON response a frontend
                                        │
                              renderAstGraph(astJson)
                                        │
                              ┌─────────┴─────────┐
                              ▼                   ▼
                       d3.hierarchy          d3.tree (layout)
                                                  │
                                              SVG con
                                              rects + paths
                                              coloreados
```

## 7. Ficheros relevantes

| Archivo | Rol |
|---------|-----|
| `mathlite/ast_nodes.py` | Definición de nodos, `pretty()` y `to_json()` |
| `mathlite/parser.py` | Construye el AST a partir de tokens |
| `mathlite/pipeline.py` | Ejecuta lex→parse→sem→eval y serializa el resultado |
| `api/main.py` | Endpoint `/api/run` que entrega el JSON |
| `web/index.html` | Panel `#panel-ast` con el contenedor `#ast-graph` |
| `web/app.js` | `renderAstGraph()`, `parseAstText()`, `kindFromLabel()` |
| `web/style.css` | Estilos de nodos, links y panel del AST |
