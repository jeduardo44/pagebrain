// Content script — corre DENTRO da página. É a única peça que "vê" o DOM.
// Extrai o conteúdo útil da página e responde a pedidos do popup/service worker.
//
// Não faz chamadas ao backend diretamente: só extrai e devolve. O service worker
// é que orquestra a rede (separação de responsabilidades das extensões MV3).

function getMeta() {
  const meta = {};
  document.querySelectorAll("meta[name], meta[property]").forEach((el) => {
    const key = (el.getAttribute("name") || el.getAttribute("property") || "").toLowerCase();
    const content = el.getAttribute("content");
    if (key && content) meta[key] = content;
  });
  return meta;
}

function getJsonLd() {
  const blocks = [];
  document.querySelectorAll('script[type="application/ld+json"]').forEach((el) => {
    try {
      const data = JSON.parse(el.textContent);
      if (Array.isArray(data)) blocks.push(...data);
      else blocks.push(data);
    } catch (_) {
      /* ignora JSON-LD malformado */
    }
  });
  return blocks;
}

// Texto principal: junta os blocos de conteúdo mais prováveis, sem menus/scripts.
function getMainText() {
  const main = document.querySelector("main, article, [role=main]") || document.body;
  const clone = main.cloneNode(true);
  clone.querySelectorAll("script, style, noscript, nav, footer, header").forEach((n) => n.remove());
  return clone.innerText.replace(/\s+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim().slice(0, 20000);
}

// Links do mesmo domínio (candidatos a scraping extra: About/Pricing/FAQ/Docs).
function getSameDomainLinks() {
  const here = location.hostname.replace(/^www\./, "");
  const seen = new Set();
  const links = [];
  document.querySelectorAll("a[href]").forEach((a) => {
    try {
      const url = new URL(a.href);
      const host = url.hostname.replace(/^www\./, "");
      const clean = url.origin + url.pathname;
      if (host === here && !seen.has(clean)) {
        seen.add(clean);
        links.push(clean);
      }
    } catch (_) {
      /* href inválido */
    }
  });
  return links.slice(0, 40);
}

function extractPage() {
  const meta = getMeta();
  return {
    url: location.href,
    title: document.title || "",
    text: getMainText(),
    description: meta["description"] || meta["og:description"] || "",
    meta,
    jsonld: getJsonLd(),
    links: getSameDomainLinks(),
  };
}

// O popup pede a extração através do service worker.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "EXTRACT_PAGE") {
    sendResponse({ page: extractPage() });
  }
  return true; // resposta assíncrona
});
