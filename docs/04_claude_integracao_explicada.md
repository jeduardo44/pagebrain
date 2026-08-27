# A integração com o Claude explicada de forma simples

> O "cérebro" do PageBrain é a Claude API. Aqui vês como o contexto do RAG entra
> no prompt, como funciona o streaming, e as escolhas de modelo/custo.

---

## O problema

Já temos o contexto certo (RAG) e os dados de empresa. Falta a parte que
**raciocina e escreve** a resposta. E queremos que ela **apareça a fluir**, não
depois de uma pausa longa.

---

## A ideia

Usamos o **SDK oficial `anthropic`** (não HTTP à mão). O padrão é sempre o mesmo:
`system` (comportamento estável) + `messages` (o histórico + a pergunta com o
contexto). O contexto do RAG entra dentro da mensagem do utilizador.

```
system   = "És o PageBrain… responde com base no contexto… cita fontes…"
messages = histórico + [ {role: user, content: CONTEXTO + PERGUNTA} ]
```

---

## Streaming (SSE)

Pedir em modo *stream* faz o SDK devolver a resposta em pedaços. O backend
reencaminha-os como eventos SSE (`event: token`), e o popup vai desenhando. No fim,
um `event: done`.

---

## Escolha de modelo e custo

Por omissão usamos **`claude-opus-5`** (o mais capaz). Mas para um chat de páginas
é caro; a escolha é **configurável** por `CLAUDE_MODEL`:

| Modelo | Preço (in/out por 1M tokens) | Quando |
|---|---|---|
| `claude-opus-5` | $5 / $25 | qualidade máxima (default) |
| `claude-sonnet-5` | $2 / $10 | ótimo custo-qualidade p/ produção |
| `claude-haiku-4-5` | $1 / $5 | simples e rápido |

Como as respostas são curtas, usamos `max_tokens=4096` e `effort: "low"` — chat
leve, barato e rápido. (Nota: `thinking`/`effort` só são enviados a modelos que os
suportam — ex.: opus/sonnet-5; o haiku recebe o pedido sem eles, senão daria 400.)

## BYOK (bring your own key) — para distribuir ao público

A chave NUNCA vai na extensão nem no repo. Cada utilizador põe a **sua** chave nas
Definições da extensão; ela é guardada no `chrome.storage.local` dele e enviada ao
backend **a cada pergunta** (`api_key` no request). O backend resolve a chave por
esta ordem: **chave do utilizador (request) → chave do servidor (`.env`)**. Assim
cada um paga o seu uso e tu não arriscas a tua conta. O modelo também é escolhido
pelo utilizador (`model` no request).

---

## As partes mais importantes do código

### Peça 1 — Montar o contexto · `prompts/templates.py`

```python
def build_context_block(*, domain, page_type, retrieved_chunks, company):
    parts = [f"[DOMÍNIO] {domain}", f"[TIPO] {page_type}"]
    if company and company.name:
        parts += [f"[EMPRESA] {company.name}: {company.description}", ...]
    parts.append("[EXCERTOS RELEVANTES]")
    parts += [f"({i}) {c}" for i, c in enumerate(retrieved_chunks, 1)]
    return "\n".join(parts)
```

É aqui que juntamos as duas fontes — dados de empresa (enriquecimento) + excertos
(RAG) — num bloco de contexto legível que precede a pergunta.

### Peça 2 — Preparar a chamada · `services/chat_service.py`

```python
def _prepare(req):
    hits = pipeline.retrieve(domain, req.message, top_k=5)      # RAG
    cached = cache_service.get(domain)                          # empresa/tipo em cache
    context = build_context_block(domain=domain, page_type=...,
                                  retrieved_chunks=[h.text for h in hits],
                                  company=cached.company if cached else None)
    messages = [*history, {"role": "user", "content": build_user_turn(context, req.message)}]
    return SYSTEM_PROMPT, messages, citations
```

Junta tudo o que o modelo precisa: recupera excertos, puxa o que está em cache, e
monta as `messages`. As **citações** saem dos `hits` do RAG.

### Peça 3 — Chamar o Claude, em streaming · `services/chat_service.py`

```python
async with _client().messages.stream(
    model=settings.claude_model,
    max_tokens=4096,
    thinking={"type": "adaptive"},        # o modelo decide quanto "pensa"
    output_config={"effort": "low"},      # chat leve: barato/rápido
    system=SYSTEM_PROMPT,
    messages=messages,
) as stream:
    async for text in stream.text_stream:  # pedaços de texto
        yield text
```

O núcleo. `messages.stream` + `async for … text_stream` dá-nos a resposta em
pedaços, que o gerador vai devolvendo. O `_client()` é criado tardiamente e
cacheado — e nos **testes é mockado**, por isso os testes não gastam tokens.

### Peça 4 — Degradação graciosa · `services/chat_service.py` + `routes/chat.py`

```python
if not settings.has_anthropic_key:
    raise MissingAnthropicKey            # sem chave real (placeholder)
# ...na rota:
except MissingAnthropicKey:
    yield _sse("error", "Sem ANTHROPIC_API_KEY — modo básico. Põe a chave em backend/.env.")
```

Sem chave, não rebenta: devolve um aviso claro que a extensão mostra. Tudo o resto
(extração, scraping, RAG) continua a funcionar.

---

## Nota honesta (estado atual)

O projeto foi construído e verificado **sem** `ANTHROPIC_API_KEY` (modo básico):
`/api/health` responde, `/api/chat` devolve o aviso gracioso, e os 20 testes
passam. Para veres o Claude a responder de verdade, põe a chave em `backend/.env`
(ver README → *Getting an Anthropic API key*).

---

**Resumo numa frase:** o `chat_service` recupera os excertos do RAG, junta-os aos
dados de empresa num bloco de contexto, e chama o Claude (SDK oficial, streaming)
com um system prompt anti-alucinação — e, sem chave, degrada com um aviso claro em
vez de falhar.
