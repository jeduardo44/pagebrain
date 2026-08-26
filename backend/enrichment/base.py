"""Interface comum dos enriquecedores externos.

Princípio central: DEGRADAÇÃO GRACIOSA. Sem chave de API → devolve vazio, sem
erro. Assim cada fonte é independente e o resto do sistema funciona na mesma.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from backend.api.models.schemas import CompanyInfo


class Enricher(ABC):
    """Um enriquecedor: dado um domínio, devolve (parcialmente) dados de empresa."""

    name: str = "base"

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """True apenas se a chave de API respetiva estiver configurada."""

    @abstractmethod
    async def enrich(self, domain: str) -> CompanyInfo:
        """Devolve CompanyInfo (pode vir vazio). Nunca deve lançar."""
