"""Busca de empresas na API pública do minha-receita (Buscar Empresas).

Só consulta a fonte externa — nunca grava nada sozinho (mesmo princípio do
LeadEnrichmentService, app/services/lead_enrichment.py). O bulk-add fica em
PublicCompanyService.bulk_add, separado, disparado por ação explícita do usuário.
"""
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.context import get_current_tenant
from app.core.exceptions import ConflictError
from app.models.company import Company
from app.models.lead_prospect import LeadProspect, LeadStatus
from app.schemas.public_company import (
    PublicCompanyBulkAddItem, PublicCompanyBulkAddResponse, PublicCompanyResult, PublicCompanySearchResponse,
)

# Mesmo mapeamento fixo já usado em app/services/lead_prospect.py — duplicado
# de propósito, seguindo a convenção já existente no projeto (também
# duplicado em frontend/src/pages/PesquisaLeadsPage.jsx).
UF_REGIAO = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste",
    "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}


class PublicCompanySearchService:
    def __init__(self, db: Session):
        self.db = db

    def search(
        self, cnae: list[str], regiao: list[str] | None, uf: list[str] | None,
        porte: str | None, cursor: str | None,
    ) -> PublicCompanySearchResponse:
        ufs = set(uf or [])
        for r in regiao or []:
            ufs |= {sigla for sigla, nome in UF_REGIAO.items() if nome == r}

        params: dict = {"cnae": ",".join(cnae), "limit": 1000}
        if ufs:
            params["uf"] = ",".join(sorted(ufs))
        if cursor:
            params["cursor"] = cursor

        try:
            resp = httpx.get(
                settings.MINHA_RECEITA_BASE_URL, params=params,
                timeout=settings.MINHA_RECEITA_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError:
            raise ConflictError(
                "A base pública de CNPJ (minha-receita) está indisponível no momento. Tente novamente em instantes."
            )

        empresas = payload.get("data", [])
        proximo_cursor = payload.get("cursor")

        resultado = [self._to_result(e) for e in empresas]
        resultado = [r for r in resultado if (r.situacao_cadastral or "").upper() == "ATIVA"]
        if porte:
            resultado = [r for r in resultado if r.porte == porte]

        self._marcar_ja_cadastrado(resultado)
        return PublicCompanySearchResponse(data=resultado, cursor=proximo_cursor)

    def _to_result(self, e: dict) -> PublicCompanyResult:
        cnae_fiscal = e.get("cnae_fiscal")
        return PublicCompanyResult(
            cnpj=e.get("cnpj", ""),
            razao_social=e.get("razao_social", ""),
            nome_fantasia=e.get("nome_fantasia") or None,
            uf=e.get("uf"),
            municipio=e.get("municipio"),
            cnae_fiscal=str(cnae_fiscal) if cnae_fiscal is not None else None,
            cnae_fiscal_descricao=e.get("cnae_fiscal_descricao"),
            porte=e.get("porte") or None,
            situacao_cadastral=e.get("descricao_situacao_cadastral"),
            capital_social=e.get("capital_social"),
        )

    def _marcar_ja_cadastrado(self, resultado: list[PublicCompanyResult]) -> None:
        cnpjs = [r.cnpj for r in resultado if r.cnpj]
        if not cnpjs:
            return
        tenant_id = get_current_tenant()
        existentes = set(
            self.db.execute(
                select(Company.cnpj).where(Company.tenant_id == tenant_id, Company.cnpj.in_(cnpjs))
            ).scalars().all()
        )
        existentes |= set(
            self.db.execute(
                select(LeadProspect.cnpj).where(LeadProspect.tenant_id == tenant_id, LeadProspect.cnpj.in_(cnpjs))
            ).scalars().all()
        )
        for r in resultado:
            r.ja_cadastrado = r.cnpj in existentes


class PublicCompanyService:
    def __init__(self, db: Session):
        self.db = db

    def bulk_add(self, empresas: list[PublicCompanyBulkAddItem], pesquisado_por) -> PublicCompanyBulkAddResponse:
        tenant_id = get_current_tenant()
        cnpjs = [e.cnpj for e in empresas]
        existentes = set(
            self.db.execute(
                select(Company.cnpj).where(Company.tenant_id == tenant_id, Company.cnpj.in_(cnpjs))
            ).scalars().all()
        )
        existentes |= set(
            self.db.execute(
                select(LeadProspect.cnpj).where(LeadProspect.tenant_id == tenant_id, LeadProspect.cnpj.in_(cnpjs))
            ).scalars().all()
        )

        criados = 0
        for e in empresas:
            if e.cnpj in existentes:
                continue
            lead = LeadProspect(
                tenant_id=tenant_id, empresa=e.razao_social, cnpj=e.cnpj, uf=e.uf,
                regiao=UF_REGIAO.get(e.uf) if e.uf else None,
                status=LeadStatus.NOVO.value, pesquisado_por=pesquisado_por,
            )
            self.db.add(lead)
            existentes.add(e.cnpj)
            criados += 1
        self.db.commit()
        return PublicCompanyBulkAddResponse(criados=criados, ignorados=len(empresas) - criados)
