// Renderer de Markdown minúsculo e SEGURO (não usamos libs externas).
// Escapa HTML primeiro (evita injeção) e depois aplica um subconjunto de
// Markdown: **negrito**, *itálico*, `código`, blocos ```, listas, links, títulos.

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderMarkdown(md) {
  let text = escapeHtml(md || "");

  // Blocos de código ``` ``` (antes do resto).
  text = text.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code.trim()}</code></pre>`);

  // Código inline `x`
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Negrito e itálico
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  // Links [texto](url)
  text = text.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>'
  );

  // Linhas → parágrafos e listas
  const lines = text.split("\n");
  const out = [];
  let inList = false;
  for (const line of lines) {
    const item = line.match(/^\s*[-*]\s+(.*)/);
    if (item) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${item[1]}</li>`);
    } else {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      if (line.trim() === "") continue;
      if (line.startsWith("<pre>")) out.push(line);
      else out.push(`<p>${line}</p>`);
    }
  }
  if (inList) out.push("</ul>");
  return out.join("");
}

window.renderMarkdown = renderMarkdown;
