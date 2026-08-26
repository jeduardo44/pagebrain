# A extensão Chrome (MV3) explicada de forma simples

> Uma extensão Manifest V3 não é uma app só. São **três peças isoladas** que
> conversam por mensagens. Perceber quem faz o quê é metade da batalha.

---

## O problema

O browser, por segurança, não deixa uma peça fazer tudo. O código que **vê a
página** não é o mesmo que **faz pedidos à rede**, que não é o mesmo que **desenha
a interface**. Cada um tem poderes e limites diferentes.

---

## As três peças (e a analogia)

| Peça | Ficheiro | Vê o DOM? | Faz rede? | Analogia |
|---|---|---|---|---|
| **Content script** | `content/content-script.js` | ✅ sim | limitado | o *repórter* dentro da página |
| **Service worker** | `background/service-worker.js` | ❌ não | ✅ sim | a *central* que liga ao backend |
| **Popup** | `popup/*` | ❌ não | ✅ sim | a *sala de chat* que tu vês |

- O **content script** é injetado *dentro* de cada página. É o único que consegue
  ler `document` (texto, `<meta>`, JSON-LD, links). Mas é "preso" à página.
- O **service worker** corre em segundo plano, sem DOM. É a ponte para o backend e
  guarda dados por domínio (`chrome.storage.local`).
- O **popup** é a janelinha que abre ao clicar no ícone. Desenha o chat e faz o
  streaming da resposta.

---

## Como conversam (mensagens)

Não partilham variáveis — trocam **mensagens**:

```
popup  ──chrome.tabs.sendMessage("EXTRACT_PAGE")──▶  content script
popup  ◀──────────── { page: {...} } ──────────────  content script

popup  ──chrome.runtime.sendMessage("ANALYZE")────▶  service worker ──▶ backend
popup  ──fetch(/api/chat) [streaming SSE] ─────────────────────────▶ backend
```

Repara: o **chat faz `fetch` direto** ao backend a partir do popup (o streaming é
mais simples aí); o **analyze passa pelo service worker** (que guarda o resultado
por domínio). Duas rotas, cada uma no sítio mais natural.

---

## As 3 partes mais importantes do código

### Peça 1 — Extrair a página · `content-script.js`

```javascript
function extractPage() {
  const meta = getMeta();               // <meta name/property>
  return {
    url: location.href,
    title: document.title,
    text: getMainText(),                // <main>/<article>, sem menus/scripts
    description: meta["og:description"] || meta["description"] || "",
    meta, jsonld: getJsonLd(),          // structured data (schema.org)
    links: getSameDomainLinks(),        // candidatos a scraping extra
  };
}
```

O único sítio que "vê" a página. Repara em `getMainText`: clona o conteúdo
principal e **remove** `script/style/nav/footer` — queremos o texto útil, não o
menu. Isto é a matéria-prima de todo o resto.

### Peça 2 — A ponte · `service-worker.js`

```javascript
async function analyzePage(page) {
  const base = await getBackendUrl();               // configurável nas opções
  const resp = await fetch(`${base}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page }),
  });
  const analysis = await resp.json();
  await chrome.storage.local.set({ [`analysis:${domainOf(page.url)}`]: analysis });
  return analysis;
}
```

A central. Chama o backend e **guarda por domínio** — é aqui que nasce a "memória"
que torna revisitar um site instantâneo.

### Peça 3 — O streaming no popup · `popup.js`

```javascript
const reader = resp.body.getReader();     // resposta SSE do /api/chat
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  // ...parte em eventos "\n\n", lê event:/data: e vai acrescentando à bolha
}
```

É isto que faz a resposta **aparecer a fluir** em vez de surgir toda de uma vez.
Lê o corpo da resposta em pedaços e vai desenhando à medida que chega.

---

## Degradação graciosa

- Página `chrome://` ou PDF → não há content script → o popup avisa e não rebenta.
- Backend em baixo → `HEALTH` falha → banner "modo básico".
- Content script não injetado (página aberta antes de instalar) → "recarrega a página".

---

**Resumo numa frase:** a extensão são três peças — o repórter (content script)
que lê a página, a central (service worker) que fala com o backend e guarda
memória, e a sala de chat (popup) que mostra a resposta a fluir — a comunicar por
mensagens porque o browser as mantém isoladas por segurança.
