// Popup — a lógica da interface. Junta: extração da página (content script),
// estado do backend (service worker), análise em segundo plano, e o chat em
// streaming (SSE) diretamente contra o backend.

const DEFAULT_BACKEND = "http://localhost:8000";

const el = {
  status: document.getElementById("status"),
  pageTitle: document.getElementById("pageTitle"),
  pageMeta: document.getElementById("pageMeta"),
  banner: document.getElementById("banner"),
  chat: document.getElementById("chat"),
  input: document.getElementById("input"),
  send: document.getElementById("send"),
  composer: document.getElementById("composer"),
  quickActions: document.getElementById("quickActions"),
  clearBtn: document.getElementById("clearBtn"),
  optionsLink: document.getElementById("optionsLink"),
};

const state = {
  page: null,
  domain: "",
  backend: DEFAULT_BACKEND,
  apiKey: "",
  model: "",
  history: [],
  canChat: false,
};

// ── Helpers ──────────────────────────────────────────────────────────
function domainOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch (_) {
    return "";
  }
}

function setStatus(kind, label) {
  el.status.className = `status ${kind}`;
  el.status.textContent = label;
}

function showBanner(text) {
  el.banner.textContent = text;
  el.banner.classList.remove("hidden");
}

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = role === "assistant" ? window.renderMarkdown(text) : escapeText(text);
  el.chat.appendChild(div);
  el.chat.scrollTop = el.chat.scrollHeight;
  return div;
}

function escapeText(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

async function saveHistory() {
  await chrome.storage.local.set({ [`history:${state.domain}`]: state.history });
}

// ── Init ─────────────────────────────────────────────────────────────
async function init() {
  const cfg = await chrome.storage.local.get(["backendUrl", "apiKey", "model"]);
  state.backend = cfg.backendUrl || DEFAULT_BACKEND;
  state.apiKey = cfg.apiKey || "";
  state.model = cfg.model || "";

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !/^https?:/.test(tab.url || "")) {
    el.pageTitle.textContent = "Página não suportada";
    el.pageMeta.textContent = "Abre uma página http(s) normal.";
    setStatus("down", "n/d");
    return;
  }
  state.domain = domainOf(tab.url);

  // 1. Extrair a página (content script).
  let page = null;
  try {
    const res = await chrome.tabs.sendMessage(tab.id, { type: "EXTRACT_PAGE" });
    page = res?.page;
  } catch (_) {
    /* content script não injetado (ex.: página aberta antes de instalar) */
  }
  if (!page) {
    el.pageTitle.textContent = "Não consegui ler a página";
    el.pageMeta.textContent = "Recarrega a página e reabre o PageBrain.";
    setStatus("down", "n/d");
    return;
  }
  state.page = page;
  el.pageTitle.textContent = page.title || state.domain;
  el.pageMeta.textContent = state.domain;

  // 2. Estado do backend.
  const health = await ask({ type: "HEALTH" });
  const h = health?.health || { status: "down" };
  const userHasKey = !!state.apiKey;
  if (h.status === "down") {
    setStatus("down", "offline");
    showBanner("Backend offline — modo básico. Corre o backend (make run) para ativar o chat.");
  } else if (!h.anthropic_key && !userHasKey) {
    // Nem o servidor nem o utilizador têm chave → pede a chave nas Definições (BYOK).
    setStatus("basic", "sem chave");
    showBanner("Adiciona a tua Anthropic API key nas Definições para ativar o chat (BYOK).");
    state.canChat = true; // deixamos tentar; o backend devolve um aviso claro
  } else {
    // Usa a chave do utilizador se existir; senão a do servidor.
    setStatus("ok", state.model || h.model || "pronto");
    state.canChat = true;
  }

  // 3. Analisar em segundo plano (scraping + RAG). Não bloqueia o chat.
  if (h.status !== "down") {
    ask({ type: "ANALYZE", page }).then((r) => {
      const a = r?.analysis;
      if (a) el.pageMeta.textContent = `${state.domain} · ${a.page_type} · ${a.chunks_indexed} excertos`;
    });
  }

  // 4. Histórico guardado deste domínio.
  const stored = await chrome.storage.local.get(`history:${state.domain}`);
  state.history = stored[`history:${state.domain}`] || [];
  state.history.forEach((m) => addMessage(m.role, m.content));
}

function ask(msg) {
  return new Promise((resolve) => chrome.runtime.sendMessage(msg, resolve));
}

// ── Chat (streaming SSE) ─────────────────────────────────────────────
async function sendMessage(text) {
  if (!text.trim() || !state.canChat) return;
  addMessage("user", text);
  state.history.push({ role: "user", content: text });
  el.input.value = "";
  el.send.disabled = true;

  const assistantEl = addMessage("assistant", "…");
  let answer = "";

  try {
    const resp = await fetch(`${state.backend}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        domain: state.domain,
        message: text,
        history: state.history.slice(0, -1), // sem a última (já é a pergunta)
        page: state.page,
        api_key: state.apiKey || undefined, // BYOK: chave do utilizador
        model: state.model || undefined,
      }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";
      for (const ev of events) {
        const { event, data } = parseSse(ev);
        if (event === "token") {
          answer += data;
          assistantEl.innerHTML = window.renderMarkdown(answer);
          el.chat.scrollTop = el.chat.scrollHeight;
        } else if (event === "error") {
          assistantEl.innerHTML = window.renderMarkdown(`⚠️ ${data}`);
        }
      }
    }
  } catch (err) {
    assistantEl.innerHTML = window.renderMarkdown(`⚠️ Erro de ligação ao backend: ${err}`);
  }

  if (answer) {
    state.history.push({ role: "assistant", content: answer });
    await saveHistory();
  }
  el.send.disabled = false;
  el.input.focus();
}

function parseSse(block) {
  let event = "message";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) {
      try {
        data += JSON.parse(line.slice(5).trim());
      } catch (_) {
        data += line.slice(5).trim();
      }
    }
  }
  return { event, data };
}

// ── Eventos da UI ────────────────────────────────────────────────────
el.composer.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(el.input.value);
});
el.quickActions.addEventListener("click", (e) => {
  const btn = e.target.closest(".qa");
  if (btn) sendMessage(btn.dataset.q);
});
el.clearBtn.addEventListener("click", async () => {
  state.history = [];
  await saveHistory();
  el.chat.innerHTML = "";
});
el.optionsLink.addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

init();
