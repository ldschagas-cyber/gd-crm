"""Cliente do endpoint interno de Benchmark Setorial do GD Diagnóstico.

Serviço-a-serviço, autenticado por chave estática (não é OAuth/JWT de usuário)
— ver `INTERNAL_API_KEY` no Diagnóstico e `DIAGNOSTICO_INTERNAL_API_KEY` aqui.
Sem cache: uso é sob demanda (clique manual na Inteligência Comercial), não
em lote nem automático.
"""
import requests

from app.core.config import settings
from app.core.exceptions import ConflictError


class BenchmarkClient:
    def listar_segmentos(self) -> list[dict]:
        if not settings.DIAGNOSTICO_INTERNAL_URL or not settings.DIAGNOSTICO_INTERNAL_API_KEY:
            raise ConflictError(
                "Consulta ao Benchmark Logístico do Diagnóstico ainda não está configurada — "
                "falta DIAGNOSTICO_INTERNAL_URL/DIAGNOSTICO_INTERNAL_API_KEY no servidor."
            )
        try:
            resp = requests.get(
                f"{settings.DIAGNOSTICO_INTERNAL_URL}/api/v1/internal/benchmark-setorial",
                headers={"X-Internal-Api-Key": settings.DIAGNOSTICO_INTERNAL_API_KEY},
                timeout=8,
            )
        except requests.RequestException as e:
            raise ConflictError(f"Não foi possível consultar o Benchmark Logístico do Diagnóstico: {e}")
        if resp.status_code >= 400:
            raise ConflictError(f"O Diagnóstico recusou a consulta ao Benchmark Logístico ({resp.status_code}).")
        return resp.json()
