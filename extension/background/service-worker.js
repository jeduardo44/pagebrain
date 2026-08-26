// Service worker (background) — a ponte entre a extensão e o backend.
// Em MV3 corre isolado, sem DOM. Responsabilidades:
//   - saber a URL do backend (configurável nas opções);
//   - chamar /api/health e /api/analyze;
//   - guardar a análise por domínio em chrome.storage.local.
// O streaming do chat (/api/chat) é feito no próprio popup (mais simples que
// reencaminhar pedaços SSE por mensagens).

const DEFAULT_BACKEND = "http://localhost:8000";

async function getBackendUrl() {
  const { backendUrl } = await chrome.storage.local.get("backendUrl");
  return backendUrl || DEFAULT_BACKEND;
}

function domainOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch (_) {
    return "";
  }
}

async function checkHealth() {
  const base = await getBackendUrl();
  try {
    const resp = await fetch(`${base}/api/health`, { method: "GET" });
    if (!resp.ok) return { status: "down" };
    return await resp.json();
  } catch (_) {
    return { status: "down" }; // backend em baixo → modo básico
  }
}

async function analyzePage(page, forceRefresh = false) {
  const base = await getBackendUrl();
  const resp = await fetch(`${base}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page, force_refresh: forceRefresh }),
  });
  if (!resp.ok) throw new Error(`analyze falhou: ${resp.status}`);
  const analysis = await resp.json();

  // Memória por domínio.
  const domain = domainOf(page.url);
  const key = `analysis:${domain}`;
  await chrome.storage.local.set({ [key]: { analysis, at: Date.now() } });
  return analysis;
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    try {
      if (msg.type === "HEALTH") {
        sendResponse({ ok: true, health: await checkHealth() });
      } else if (msg.type === "ANALYZE") {
        sendResponse({ ok: true, analysis: await analyzePage(msg.page, msg.forceRefresh) });
      } else {
        sendResponse({ ok: false, error: "unknown message" });
      }
    } catch (err) {
      sendResponse({ ok: false, error: String(err) });
    }
  })();
  return true; // resposta assíncrona
});
