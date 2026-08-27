// Definições da extensão: URL do backend, chave Anthropic (BYOK), modelo, e
// limpar memória local.

const backendInput = document.getElementById("backendUrl");
const apiKeyInput = document.getElementById("apiKey");
const modelSelect = document.getElementById("model");
const savedLabel = document.getElementById("saved");

async function load() {
  const cfg = await chrome.storage.local.get(["backendUrl", "apiKey", "model"]);
  backendInput.value = cfg.backendUrl || "http://localhost:8000";
  apiKeyInput.value = cfg.apiKey || "";
  modelSelect.value = cfg.model || "claude-opus-5";
}

document.getElementById("save").addEventListener("click", async () => {
  await chrome.storage.local.set({
    backendUrl: backendInput.value.trim() || "http://localhost:8000",
    apiKey: apiKeyInput.value.trim(),
    model: modelSelect.value,
  });
  savedLabel.textContent = "Guardado ✓";
  setTimeout(() => (savedLabel.textContent = ""), 1500);
});

document.getElementById("clear").addEventListener("click", async () => {
  // Preserva as definições (backend/chave/modelo); apaga histórico e análises.
  const cfg = await chrome.storage.local.get(["backendUrl", "apiKey", "model"]);
  await chrome.storage.local.clear();
  await chrome.storage.local.set(cfg);
  savedLabel.textContent = "Memória limpa ✓";
  setTimeout(() => (savedLabel.textContent = ""), 1500);
});

load();
