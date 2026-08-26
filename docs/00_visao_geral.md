# Visão geral · O PageBrain de ponta a ponta (explicado simples)

> **Lê este primeiro.** Conta a história completa sem jargão: o que é, como uma
> pergunta vira resposta, e o mapa das peças. Depois, cada `0X_*.md` aprofunda uma.

---

## O problema

Todos os sites têm um chatbot. Quase todos são inúteis: fazem-te andar às voltas
numa árvore de FAQs e não sabem nada específico sobre o produto ou a empresa.

O **PageBrain** é uma extensão que, ao clicares no ícone em qualquer página, te dá
um assistente que **entende aquela página** — o que a empresa faz, como o produto
funciona, e ajuda-te a usá-lo — usando o **Claude** como cérebro.

---

## A ideia (a intuição)

Sozinho, um modelo de IA não conhece a *tua* página. A sacada é a mesma do RAG:
**antes de o modelo responder, vamos buscar o conteúdo certo da página (e do site)
e entregamos-lho junto com a pergunta.** É "exame com consulta" em vez de "exame
de cabeça".

Mas há três problemas práticos além do "buscar conteúdo":
1. **Onde corre o cérebro?** Na cloud (Claude API) — assim funciona na máquina de
   qualquer utilizador e não pesa no teu portátil.
2. **Como é que a extensão vê a página?** Uma extensão tem peças separadas
   (content script, service worker, popup) que conversam por mensagens.
3. **Como não repetir trabalho?** Memória por domínio (cache + índice vetorial):
   revisitar um site já visto é instantâneo.

---

## A viagem de uma pergunta (passo a passo)

```
 [Página no browser]
        │  1. content script extrai texto/meta/links
        ▼
 [Service worker] ──2. POST /api/analyze──▶ [Backend FastAPI]
        │                                      │ 3. scrape páginas-chave (About/Pricing/FAQ)
        │                                      │ 4. enriquece (Clearbit/Brave, opcional)
        │                                      │ 5. chunk → embed → ChromaDB (por domínio)
        ▼                                      ▼
 [Popup: tu escreves] ──6. POST /api/chat──▶ [Backend]
                                               │ 7. recupera excertos relevantes (RAG)
                                               │ 8. monta prompt + contexto
                                               ▼
                                          [Claude API] ──9. streaming──▶ resposta no popup
```

- **Passos 1-5 (analyze):** preparar — feito uma vez por site, guardado em cache.
- **Passos 6-9 (chat):** responder — a cada pergunta, com contexto fresco do RAG.

---

## O mapa das peças (ficheiro ↔ papel)

| Camada | Ficheiro(s) | Faz o quê |
|---|---|---|
| Extração | `extension/content/content-script.js` | lê o DOM: texto, meta, OG, JSON-LD, links |
| Ponte | `extension/background/service-worker.js` | chama o backend, guarda por domínio |
| UI | `extension/popup/*` | chat, botões de ação, streaming, histórico |
| API | `backend/api/main.py` + `routes/*` | `/analyze`, `/chat`, `/cache`, `/health` |
| Scraping | `backend/scraper/*` | extrai texto limpo + segue links do site |
| Enriquecimento | `backend/enrichment/*` | dados de empresa (opcional, sem chave = vazio) |
| RAG | `backend/rag/*` | chunk → embed (CPU) → ChromaDB por domínio |
| Cérebro | `backend/api/services/chat_service.py` | chama o Claude com o contexto |
| Prompts | `backend/prompts/*` | system prompt + montagem do contexto |

---

## As decisões que importam (e porquê)

- **Claude na cloud, embeddings locais em CPU.** O modelo grande não corre no teu
  Mac (leve para os 8 GB); só o `bge-small` de embeddings, forçado a CPU.
- **Uma coleção ChromaDB por domínio.** Isolamento (um site nunca vê excertos de
  outro) + memória (revisitar é instantâneo).
- **Degradação graciosa.** Sem backend → a extensão mostra o conteúdo extraído
  (modo básico). Sem chaves de enriquecimento → salta essa parte. Sem
  `ANTHROPIC_API_KEY` → tudo funciona menos a resposta do chat, com aviso claro.
- **Streaming (SSE).** A resposta aparece a fluir, palavra a palavra.

---

## Como correr (resumo)

```bash
make setup && source .venv/bin/activate
cp .env.example .env        # põe a ANTHROPIC_API_KEY
make run                    # backend em http://localhost:8000
# chrome://extensions → Developer mode → Load unpacked → pasta extension/
```

`make test` corre os testes **sem gastar tokens** (o Claude é mockado).

---

**Resumo numa frase:** o PageBrain extrai o conteúdo da página, constrói uma
memória por domínio (scraping + RAG local em CPU), e a cada pergunta entrega os
excertos certos ao Claude na cloud — que responde, em streaming, sobre *aquela*
página e empresa.
