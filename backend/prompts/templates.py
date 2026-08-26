"""Templates que montam o texto de contexto enviado ao Claude.

Separado do system prompt: aqui está a parte VARIÁVEL (muda a cada página/pergunta).
"""
from __future__ import annotations

from backend.api.models.schemas import CompanyInfo


def build_context_block(
    *,
    domain: str,
    page_type: str,
    retrieved_chunks: list[str],
    company: CompanyInfo | None = None,
) -> str:
    """Constrói o bloco de CONTEXTO que precede a pergunta do utilizador."""
    parts: list[str] = [f"[DOMÍNIO] {domain}", f"[TIPO DE PÁGINA] {page_type}"]

    if company and (company.name or company.description):
        parts.append("\n[EMPRESA]")
        if company.name:
            parts.append(f"Nome: {company.name}")
        if company.description:
            parts.append(f"Descrição: {company.description}")
        if company.industry:
            parts.append(f"Indústria: {company.industry}")
        if company.employees:
            parts.append(f"Equipa: {company.employees}")
        if company.funding:
            parts.append(f"Funding: {company.funding}")
        if company.competitors:
            parts.append(f"Concorrentes: {', '.join(company.competitors)}")
        if company.tech_stack:
            parts.append(f"Tech stack: {', '.join(company.tech_stack)}")
        if company.news:
            parts.append("Notícias recentes:\n- " + "\n- ".join(company.news))

    if retrieved_chunks:
        parts.append("\n[EXCERTOS RELEVANTES DA PÁGINA/SITE]")
        for i, chunk in enumerate(retrieved_chunks, 1):
            parts.append(f"({i}) {chunk}")
    else:
        parts.append("\n[EXCERTOS RELEVANTES DA PÁGINA/SITE]\n(nenhum indexado ainda)")

    return "\n".join(parts)


def build_user_turn(context_block: str, question: str) -> str:
    """Junta o contexto + a pergunta numa única mensagem de utilizador."""
    return (
        f"{context_block}\n\n"
        f"[PERGUNTA]\n{question}\n\n"
        "Responde usando o contexto acima. Cita as fontes no fim."
    )
