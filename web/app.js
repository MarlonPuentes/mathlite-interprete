/* MathLite — frontend.
   Editor (CodeMirror) + tabs Output/Diag/Tokens/AST/Cases + persistencia. */

const EXAMPLES = {
  "ex-area": `-- Área de triángulo + while
let base = 5
let altura = 3.0

def area(b, h) {
  return (b * h) / 2
}

let resultado = area(base, altura)
print(resultado)

let i = 1
while i <= 5 {
  print(i * i)
  let i = i + 1
}`,
  "ex-fact": `-- Factorial recursivo
def fact(n) {
  if n <= 1 { return 1 }
  return n * fact(n - 1)
}
print(fact(6))`,
  "ex-precedence": `-- Precedencia mixta
print((3 + 4 * 2) / (1 - 5) ^ 2)`,
  "ex-trig": `-- Trigonometría y raíz compuesta
let x = sin(0) + cos(0) + sqrt(16)
print(x)`,
  "ex-call-call": `-- Una función que llama a otra
def cuad(n) { return n * n }
def hipot(a, b) { return sqrt(cuad(a) + cuad(b)) }
print(hipot(3, 4))`,
  "ex-lex-err": `-- Carácter inválido (@)
let x = @ + 1`,
  "ex-syn-err": `-- Paréntesis sin cerrar
print((3 + 4 * 2)`,
  "ex-sem-err": `-- Variable no declarada
print(x)`,
  "ex-rt-err": `-- División por cero
let r = 10 / 0`,
};

let editor;
let lastAstJson = null;

document.addEventListener("DOMContentLoaded", () => {
  const ta = document.getElementById("editor");
  editor = CodeMirror.fromTextArea(ta, {
    mode: "python",
    theme: "dracula",
    lineNumbers: true,
    indentUnit: 2,
    tabSize: 2,
    smartIndent: true,
  });
  editor.setValue(EXAMPLES["ex-area"]);

  document.getElementById("examples").addEventListener("change", (e) => {
    const key = e.target.value;
    if (key && EXAMPLES[key]) {
      editor.setValue(EXAMPLES[key]);
    }
  });

  document.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => activateTab(btn.dataset.tab));
  });

  document.getElementById("btn-run").addEventListener("click", runCode);
  document.getElementById("btn-save").addEventListener("click", saveCase);
  document.getElementById("btn-refresh-cases").addEventListener("click", loadCases);


  // Atajos
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      runCode();
    }
  });

  checkHealth();
  loadCases();
  renderAstGraph(null); // estado vacío inicial
  // Auto-ejecutar para tener AST listo al abrir la pestaña
  setTimeout(runCode, 200);
});

function activateTab(name) {
  document.querySelectorAll(".tabs button").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === name)
  );
  document.querySelectorAll(".panel").forEach((p) =>
    p.classList.toggle("active", p.id === `panel-${name}`)
  );
  // Al activar la pestaña AST, redibujar con tamaño real del contenedor
  if (name === "ast") {
    requestAnimationFrame(() => renderAstGraph(lastAstJson));
  }
}

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const badge = document.getElementById("storage-badge");
    badge.textContent = `storage: ${data.storage}`;
    if (data.storage === "mongodb-atlas") badge.classList.add("mongo");
  } catch (e) {
    document.getElementById("storage-badge").textContent = "API offline";
  }
}

async function runCode() {
  const source = editor.getValue();
  const out = document.getElementById("output");
  out.textContent = "Ejecutando...";
  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, execute: true }),
    });
    const data = await res.json();
    renderResult(data);
  } catch (e) {
    out.textContent = `Error de red: ${e}`;
  }
}

function renderResult(data) {
  const out = document.getElementById("output");
  out.textContent = data.output.length ? data.output.join("\n") : (data.executed ? "(programa ejecutado sin salida)" : "(no se ejecutó)");

  const tokens = document.getElementById("tokens");
  tokens.textContent = data.tokens
    .map((t) => `${t.line}:${t.column}\t${t.type}\t${JSON.stringify(t.lexeme)}${t.value !== null && t.value !== undefined ? `  → ${JSON.stringify(t.value)}` : ""}`)
    .join("\n");

  document.getElementById("ast").textContent = data.ast;
  // Fallback: si el servidor no envía ast_json (porque no se reinició),
  // parseamos el árbol indentado de `data.ast` para tener algo que dibujar.
  lastAstJson = data.ast_json || parseAstText(data.ast || "");
  renderAstGraph(lastAstJson);

  const diagBox = document.getElementById("diagnostics");
  diagBox.innerHTML = "";
  if (data.diagnostics.length === 0) {
    diagBox.innerHTML = '<div class="diag" style="border-left-color: var(--accent-2);">Sin errores ✓</div>';
  } else {
    data.diagnostics.forEach((d) => {
      const row = document.createElement("div");
      row.className = `diag ${d.phase}`;
      row.innerHTML = `<span class="where">${d.phase} · ${d.line}:${d.column}</span>${escapeHtml(d.message)}`;
      diagBox.appendChild(row);
    });
  }
  const pill = document.getElementById("diag-count");
  if (data.diagnostics.length) {
    pill.textContent = data.diagnostics.length;
    pill.classList.add("visible");
  } else {
    pill.classList.remove("visible");
  }
}

async function saveCase() {
  const source = editor.getValue();
  const title = prompt("Nombre del caso:", "Caso " + new Date().toLocaleTimeString());
  if (!title) return;
  // Pre-ejecutar para almacenar resumen
  let summary = {};
  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, execute: true }),
    });
    const data = await res.json();
    summary = {
      diagnostics: data.diagnostics.length,
      executed: data.executed,
      output_lines: data.output.length,
    };
  } catch (_) {}
  try {
    await fetch("/api/cases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, source, result_summary: summary }),
    });
    await loadCases();
    activateTab("cases");
  } catch (e) {
    alert(`No se pudo guardar: ${e}`);
  }
}

async function loadCases() {
  try {
    const res = await fetch("/api/cases");
    const data = await res.json();
    const ul = document.getElementById("cases-list");
    ul.innerHTML = "";
    if (!data.length) {
      ul.innerHTML = '<li><span class="meta">No hay casos guardados</span></li>';
      return;
    }
    data.forEach((c) => {
      const li = document.createElement("li");
      const summary = c.result_summary || {};
      const summaryTxt = summary.diagnostics !== undefined
        ? `diag=${summary.diagnostics}, exec=${summary.executed ? "✓" : "✗"}, salidas=${summary.output_lines}`
        : "";
      li.innerHTML = `
        <div>
          <div class="title">${escapeHtml(c.title)}</div>
          <div class="meta">${new Date(c.created_at).toLocaleString()} · ${summaryTxt}</div>
        </div>
        <div>
          <button class="load" data-id="${c._id}">Cargar</button>
          <button class="delete" data-id="${c._id}">Eliminar</button>
        </div>
      `;
      li.querySelector(".load").addEventListener("click", () => {
        editor.setValue(c.source);
        activateTab("output");
      });
      li.querySelector(".delete").addEventListener("click", async () => {
        if (!confirm(`Eliminar "${c.title}"?`)) return;
        await fetch(`/api/cases/${c._id}`, { method: "DELETE" });
        await loadCases();
      });
      ul.appendChild(li);
    });
  } catch (e) {
    console.error(e);
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/* ---------------- Render gráfico del AST con D3 ---------------- */

// Clasifica un label del AST en una "categoría" para colorearlo.
function kindFromLabel(label) {
  const s = String(label);
  if (s === "Program") return "program";
  if (s === "Block") return "block";
  if (s.startsWith("Assign")) return "assign";
  if (s.startsWith("FuncDef")) return "funcdef";
  if (s.startsWith("Call")) return "call";
  if (s.startsWith("Var")) return "variable";
  if (s.startsWith("Int") || s.startsWith("Real") || s.startsWith("String") || s.startsWith("Bool")) return "literal";
  if (s.startsWith("BinOp") || s.startsWith("Unary")) return "operator";
  if (s === "If" || s === "While" || s.startsWith("Return")) return "control";
  if (s === "Print") return "io";
  if (s === "ExprStmt") return "stmt";
  if (s === "cond" || s === "then" || s === "else" || s === "body" || s.endsWith(":")) return "label";
  return "unknown";
}

// Parser de fallback: convierte el texto indentado en JSON jerárquico.
// Necesario si el backend aún no envía `ast_json`.
function parseAstText(text) {
  const lines = String(text).split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (!lines.length) return null;
  const stack = []; // pila: { depth, node }
  let root = null;
  for (const line of lines) {
    const indent = line.match(/^ */)[0].length;
    const depth = Math.floor(indent / 2);
    const label = line.trim().replace(/:$/, "");
    const node = { label, kind: kindFromLabel(label), children: [] };
    while (stack.length && stack[stack.length - 1].depth >= depth) stack.pop();
    if (stack.length === 0) {
      root = node;
    } else {
      stack[stack.length - 1].node.children.push(node);
    }
    stack.push({ depth, node });
  }
  return root;
}

function renderAstGraph(astJson) {
  const container = document.getElementById("ast-graph");
  if (!container) return;
  container.innerHTML = "";

  if (!astJson) {
    container.innerHTML =
      '<div class="ast-empty">Ejecuta el código (▶) para visualizar el AST</div>';
    return;
  }
  if (typeof d3 === "undefined") {
    container.innerHTML =
      '<div class="ast-empty">No se pudo cargar D3 (revisa conexión a internet)</div>';
    return;
  }

  const root = d3.hierarchy(astJson, (d) => d.children);

  // Calcular ancho de cada nodo según el texto
  root.each((d) => {
    d._w = Math.max(70, String(d.data.label).length * 7.5 + 22);
  });
  const maxW = d3.max(root.descendants(), (d) => d._w) || 110;

  const nodeH = 32;
  const vGap = 70;   // separación vertical entre niveles
  const hGap = 22;   // separación horizontal entre hermanos

  d3.tree()
    .nodeSize([maxW + hGap, vGap])
    .separation((a, b) => (a.parent === b.parent ? 1 : 1.2))(root);

  // Bounding box real del árbol
  let x0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  root.each((d) => {
    if (d.x < x0) x0 = d.x;
    if (d.x > x1) x1 = d.x;
    if (d.y > y1) y1 = d.y;
  });
  const pad = 40;
  const svgW = Math.max(300, (x1 - x0) + maxW + pad * 2);
  const svgH = Math.max(200, y1 + nodeH + pad * 2);

  // Dimensiones EXPLÍCITAS — no dependemos del tamaño del contenedor
  const svg = d3.select(container)
    .append("svg")
    .attr("width", svgW)
    .attr("height", svgH)
    .attr("viewBox", [x0 - maxW / 2 - pad, -pad, svgW, svgH]);

  const g = svg.append("g");

  // Zoom + pan opcional con rueda / arrastrar
  svg.call(
    d3.zoom().scaleExtent([0.3, 3]).on("zoom", (ev) => g.attr("transform", ev.transform))
  );

  // Líneas entre nodos
  const linkGen = d3.linkVertical().x((d) => d.x).y((d) => d.y);
  g.append("g")
    .attr("class", "links")
    .selectAll("path")
    .data(root.links())
    .join("path")
    .attr("class", "link")
    .attr("d", linkGen);

  // Nodos
  const nodes = g.append("g")
    .attr("class", "nodes")
    .selectAll("g")
    .data(root.descendants())
    .join("g")
    .attr("class", (d) => `node ${d.data.kind || "unknown"}`)
    .attr("transform", (d) => `translate(${d.x},${d.y})`);

  nodes.append("rect")
    .attr("height", nodeH)
    .attr("y", -nodeH / 2)
    .attr("width", (d) => d._w)
    .attr("x", (d) => -d._w / 2)
    .attr("rx", 6)
    .attr("ry", 6);

  nodes.append("text")
    .attr("text-anchor", "middle")
    .attr("dominant-baseline", "middle")
    .text((d) => d.data.label);

  nodes.append("title").text((d) => d.data.label);
}
