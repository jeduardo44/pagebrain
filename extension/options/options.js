// Definições da extensão: URL do backend + limpar memória local.

const backendInput = document.getElementById("backendUrl");
const savedLabel = document.getElementById("saved");

async function load() {
  const { backendUrl } = await chrome.storage.local.get("backendUrl");
  backendInput.value = backendUrl || "http://localhost:8000";
}

document.getElementById("save").addEventListener("click", async () => {
  const url = backendInput.value.trim() || "http://localhost:8000";
  await chrome.storage.local.set({ backendUrl: url });
  savedLabel.textContent = "Guardado ✓";
  setTimeout(() => (savedLabel.textContent = ""), 1500);
});

document.getElementById("clear").addEventListener("click", async () => {
  // Guarda o backendUrl; apaga histórico e análises.
  const { backendUrl } = await chrome.storage.local.get("backendUrl");
  await chrome.storage.local.clear();
  if (backendUrl) await chrome.storage.local.set({ backendUrl });
  savedLabel.textContent = "Memória limpa ✓";
  setTimeout(() => (savedLabel.textContent = ""), 1500);
});

load();
