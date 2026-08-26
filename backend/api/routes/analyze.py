"""POST /api/analyze — recebe a página extraída e devolve a análise enriquecida."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.models.schemas import AnalyzeRequest, AnalyzeResponse
from backend.api.services import analyze_service

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    return await analyze_service.analyze(req)
