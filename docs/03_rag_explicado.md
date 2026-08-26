# O RAG explicado de forma simples

> RAG = *Retrieval-Augmented Generation*. A ideia: antes de o Claude responder,
> vamos buscar os excertos certos da página/site e entregamos-lhos. Aqui, com uma
> particularidade importante: **memória por domínio**.

---

## O problema

O conteúdo de um site inteiro é grande demais para enviar ao modelo em cada
pergunta (caro e lento). E querias que uma pergunta encontrasse o excerto certo
**por significado**, não por palavras exatas.

---

## A ideia: significado vira geometria

- Um **embedding** transforma um texto num **vetor** (uma lista de números).
- Textos com significado parecido ficam com vetores **próximos**.
- "Procurar" passa a ser **achar os pontos mais perto** do ponto da pergunta.

Assim, "quanto custa?" encontra o excerto sobre "planos e preços" mesmo sem
partilharem palavras.

---

## A particularidade: uma coleção por domínio

Cada site tem a **sua própria** base de conhecimento no ChromaDB. Porquê?

- **Isolamento:** uma pergunta sobre `acme.com` nunca recupera excertos de
  `outrosite.com`.
- **Memória:** revisitar um site já indexado é instantâneo — o índice já lá está.

```
acme.com      →  coleção "dom_acme_com"     (N excertos)
stripe.com    →  coleção "dom_stripe_com"   (M excertos)
```

---

## A viagem (duas partes)

```
INGEST (uma vez por site)         RETRIEVE (a cada pergunta)
texto → chunk → embed → Chroma    pergunta → embed → top-k mais próximos
```

---

## Recursos: leve de propósito

O modelo de embeddings (`bge-small`, ~130 MB) corre **em CPU** e é carregado só na
1ª vez que é preciso. Num Mac de 8 GB isto é deliberado: correr na GPU (Metal)
competiria por memória com o resto. Em CPU é mais lento, mas os textos aqui são
curtos e o custo é aceitável.

---

## As partes mais importantes do código

### Peça 1 — Cortar em chunks · `rag/chunker.py`

```python
def chunk_text(text, size=512, overlap=50):
    tokens = _encoder().encode(text)
    if len(tokens) <= size:
        return [text]
    step = size - overlap                     # sobreposição p/ não partir ideias
    return [enc.decode(tokens[s:s+size]) for s in range(0, len(tokens), step)]
```

Pedaços de ~512 tokens com 50 de sobreposição. Pequenos e focados = mais fáceis de
encontrar por significado; a sobreposição evita cortar uma ideia a meio.

### Peça 2 — Texto vira vetor, em CPU · `rag/embedder.py`

```python
@lru_cache
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.embedding_model, device="cpu")  # CPU!

def embed_texts(texts):
    return [v.tolist() for v in _model().encode(texts, normalize_embeddings=True)]
```

`@lru_cache` → o modelo carrega **uma só vez** (é a parte cara). `device="cpu"` é a
decisão de recursos. `normalize_embeddings` põe todos os vetores do mesmo
"tamanho" para a comparação ser justa.

### Peça 3 — Uma coleção por domínio · `rag/store.py`

```python
def _collection(domain):
    return _client().get_or_create_collection(
        name=_collection_name(domain),           # "dom_acme_com"
        metadata={"hnsw:space": "cosine"},
    )

def search(domain, query_vector, top_k=5):
    res = _collection(domain).query(query_embeddings=[query_vector], n_results=top_k)
    # Chroma devolve DISTÂNCIA (0=idêntico) → convertemos para score (maior=melhor)
    return [Hit(..., score=1.0 - dist) for ...]
```

O coração da memória por domínio. Cada site tem a sua coleção; a busca é sempre
dentro do domínio certo.

### Peça 4 — Juntar tudo · `rag/pipeline.py`

```python
def ingest(domain, pages):                       # pages = [(url, texto), ...]
    chunks = [c for url, txt in pages for c in chunk_page(url, txt, domain)]
    store.add_chunks(domain, chunks, embed_texts([c.text for c in chunks]))
    return len(chunks)

def retrieve(domain, question, top_k=5):
    return store.search(domain, embed_query(question), top_k)
```

Duas funções simples que escondem toda a complexidade: `ingest` para preparar,
`retrieve` para responder.

---

**Resumo numa frase:** o RAG transforma o conteúdo do site num "mapa de
significados" por domínio (chunk → embed em CPU → ChromaDB), e a cada pergunta vai
buscar os excertos mais próximos desse mapa para o Claude responder com base neles.
