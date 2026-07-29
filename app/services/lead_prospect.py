"""Serviço de pesquisa de leads: cálculo de Score ICP/Fit/Gamificação/Bônus,
CRUD e promoção para companies. Item 9.1 da especificação técnica."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.models.company import Company, CompanyStatus
from app.models.lead_prospect import LeadProspect, LeadStatus
from app.repositories.company import CompanyRepository
from app.repositories.lead_prospect import LeadProspectRepository
from app.repositories.user import UserRepository
from app.schemas.lead_prospect import (
    IcpScoringRules, LeadProspectCreate, LeadProspectPageParams, LeadProspectRead, LeadProspectUpdate,
    PerformanceReportResponse, PerformanceReportRow,
)
from app.services.tenant import TenantService

DEFAULT_ICP_RULES = {
    "setor": {
        "Farma": 40, "Alimentos": 40, "Autopeças": 40, "Etiquetas": 40,
        "Plástico": 30, "Máquinas e Equipamentos": 30, "Química": 30, "Cosmético": 30,
    },
    "setor_fallback": 10,
    "regiao": {"Sudeste": 30, "Sul": 30, "Nordeste": 30, "Norte": 0, "Centro-Oeste": 0},
    "faixa_funcionarios": {
        "1-50": 0, "51-200": 30, "201-500": 30, "501-1.000": 30,
        "1.001-5.000": 40, "5.001-10.000": 50, "+ de 10.001": 0,
    },
    "corte_a": 80, "corte_b": 70, "corte_c": 40,
    "bonus_valor": 1.00,
}

# Fallback para leads que só têm UF (sem região informada diretamente, ex.: pesquisa
# manual ou enriquecimento por IA, que só resolve estado). Quando `lead.regiao` vem
# preenchido (ex.: importação de fontes que só têm a macrorregião, sem UF), ele tem
# prioridade — ver `_regiao`.
UF_REGIAO = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste",
    "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}


class LeadProspectService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = LeadProspectRepository(db)
        self.tenant_service = TenantService(db)

    # ---- critérios de pontuação (por tenant) ------------------------------
    def get_rules(self) -> dict:
        tenant = self.tenant_service.get_current()
        stored = (tenant.config or {}).get("icp_scoring_rules") if tenant.config else None
        return {**DEFAULT_ICP_RULES, **(stored or {})}

    def update_rules(self, data: IcpScoringRules) -> dict:
        tenant = self.tenant_service.get_current()
        config = dict(tenant.config or {})
        config["icp_scoring_rules"] = data.model_dump()
        tenant.config = config
        self.db.flush()
        return config["icp_scoring_rules"]

    # ---- cálculo (nunca persistido, exceto regiao/uf que agora são colunas) ----
    def _regiao(self, lead: LeadProspect) -> str | None:
        """Região informada diretamente tem prioridade; se ausente, deriva da UF."""
        return lead.regiao or (UF_REGIAO.get(lead.uf) if lead.uf else None)

    def _score(self, lead: LeadProspect, rules: dict) -> int:
        setor_pts = rules["setor"].get(lead.setor, rules["setor_fallback"]) if lead.setor else 0
        regiao = self._regiao(lead)
        regiao_pts = rules["regiao"].get(regiao, 0) if regiao else 0
        faixa_pts = rules["faixa_funcionarios"].get(lead.faixa_funcionarios, 0) if lead.faixa_funcionarios else 0
        return min(100, setor_pts + regiao_pts + faixa_pts)

    def _fit(self, lead: LeadProspect, rules: dict, score: int) -> str:
        if score == 0 and not lead.setor and not lead.uf and not lead.regiao and not lead.faixa_funcionarios:
            return "Não avaliado"
        if score >= rules["corte_a"]:
            return "A"
        if score >= rules["corte_b"]:
            return "B"
        if score >= rules["corte_c"]:
            return "C"
        return "Sem Perfil"

    def _gamificacao(self, lead: LeadProspect, fit: str) -> int:
        if fit in ("C", "Sem Perfil", "Não avaliado") or lead.status == LeadStatus.DESCARTADO.value:
            return 0
        pontos = 0
        if lead.telefone:
            pontos += 40
        if lead.setor:
            pontos += 20
        if lead.uf or lead.regiao:
            pontos += 20
        if lead.faixa_funcionarios:
            pontos += 10
        if lead.site:
            pontos += 10
        return pontos

    def to_read(self, lead: LeadProspect, rules: dict | None = None) -> LeadProspectRead:
        rules = rules or self.get_rules()
        score = self._score(lead, rules)
        fit = self._fit(lead, rules, score)
        gamificacao = self._gamificacao(lead, fit)
        recebe_bonus = lead.status == LeadStatus.PROMOVIDO.value and gamificacao > 70
        bonus_valor = rules["bonus_valor"] if recebe_bonus else 0.0
        return LeadProspectRead(
            id=lead.id, empresa=lead.empresa, setor=lead.setor, segmento=lead.segmento, uf=lead.uf,
            regiao=lead.regiao,
            faixa_funcionarios=lead.faixa_funcionarios,
            faturamento=float(lead.faturamento) if lead.faturamento is not None else None,
            site=lead.site, telefone=lead.telefone, linkedin=lead.linkedin, dor_sugerida=lead.dor_sugerida,
            contato_sugerido=lead.contato_sugerido, status=lead.status, pesquisado_por=lead.pesquisado_por,
            promoted_company_id=lead.promoted_company_id, created_at=lead.created_at,
            score_icp=score, icp_fit=fit, gamificacao=gamificacao, recebe_bonus=recebe_bonus,
            bonus_valor=bonus_valor,
        )

    # ---- CRUD ---------------------------------------------------------------
    def list(self, params: LeadProspectPageParams, status: str | None = None, pesquisado_por: UUID | None = None,
             busca: str | None = None, icp_fit: str | None = None) -> tuple[list[LeadProspectRead], int]:
        filters = []
        if status:
            filters.append(LeadProspect.status == status)
        if pesquisado_por:
            filters.append(LeadProspect.pesquisado_por == pesquisado_por)
        if busca:
            filters.append(self.repo.search_filter(busca))
        # icp_fit é calculado (não é coluna): busca tudo que bate nos filtros de banco
        # e filtra/pagina em memória — volume esperado é baixo (pesquisa manual).
        items, _ = self.repo.list(*filters, offset=0, limit=100_000,
                                  order_by=LeadProspect.created_at.desc())
        rules = self.get_rules()
        read_items = [self.to_read(lead, rules) for lead in items]
        if icp_fit:
            read_items = [r for r in read_items if r.icp_fit == icp_fit]
        total = len(read_items)
        page_items = read_items[params.offset: params.offset + params.size]
        return page_items, total

    def _get_orm(self, lead_id: UUID) -> LeadProspect:
        lead = self.repo.get(lead_id)
        if lead is None:
            raise NotFoundError("Pesquisa não encontrada")
        return lead

    def get(self, lead_id: UUID) -> LeadProspectRead:
        return self.to_read(self._get_orm(lead_id))

    def get_orm(self, lead_id: UUID) -> LeadProspect:
        return self._get_orm(lead_id)

    def create(self, data: LeadProspectCreate) -> LeadProspectRead:
        payload = data.model_dump()
        payload["status"] = data.status.value
        lead = LeadProspect(**payload)
        lead = self.repo.add(lead)
        return self.to_read(lead)

    def update(self, lead_id: UUID, data: LeadProspectUpdate) -> LeadProspectRead:
        lead = self._get_orm(lead_id)
        payload = data.model_dump(exclude_unset=True)
        if payload.get("status") is not None:
            payload["status"] = payload["status"].value
        for field, value in payload.items():
            setattr(lead, field, value)
        lead = self.repo.save(lead)
        return self.to_read(lead)

    def delete(self, lead_id: UUID) -> None:
        lead = self._get_orm(lead_id)
        self.repo.delete(lead)

    def promote(self, lead_id: UUID) -> LeadProspectRead:
        lead = self._get_orm(lead_id)
        if lead.promoted_company_id:
            raise ConflictError("Esta pesquisa já foi promovida a empresa")
        company = Company(
            razao_social=lead.empresa, segmento=lead.segmento, uf=lead.uf, site=lead.site,
            telefone=lead.telefone, porte=lead.faixa_funcionarios, faturamento_estimado=lead.faturamento,
            status=CompanyStatus.LEAD.value, origem="Pesquisa de Leads",
        )
        company = CompanyRepository(self.db).add(company)
        lead.promoted_company_id = company.id
        lead.status = LeadStatus.PROMOVIDO.value
        lead = self.repo.save(lead)
        return self.to_read(lead)

    # ---- relatório de desempenho (§9.7) — só consulta, agregado por pesquisador -----
    def performance_report(self, mes: str) -> PerformanceReportResponse:
        try:
            year, month = (int(p) for p in mes.split("-"))
            if not 1 <= month <= 12:
                raise ValueError
        except ValueError:
            raise AppException("Mês inválido — use o formato AAAA-MM")
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if month == 12 else datetime(year, month + 1, 1, tzinfo=timezone.utc)

        items, _ = self.repo.list(
            LeadProspect.created_at >= start, LeadProspect.created_at < end,
            offset=0, limit=100_000,
        )
        rules = self.get_rules()
        users, _ = UserRepository(self.db).list(offset=0, limit=1000)
        nomes = {u.id: u.nome for u in users}

        agg: dict[UUID, dict] = {}
        for lead in items:
            read = self.to_read(lead, rules)
            row = agg.setdefault(lead.pesquisado_por, {
                "total": 0, "icp_a": 0, "icp_b": 0, "icp_c": 0, "sem_perfil": 0,
                "promovidos": 0, "bonus_valido": 0.0,
            })
            row["total"] += 1
            if read.icp_fit == "A":
                row["icp_a"] += 1
            elif read.icp_fit == "B":
                row["icp_b"] += 1
            elif read.icp_fit == "C":
                row["icp_c"] += 1
            else:
                row["sem_perfil"] += 1
            if lead.status == LeadStatus.PROMOVIDO.value:
                row["promovidos"] += 1
            if read.recebe_bonus:
                row["bonus_valido"] += read.bonus_valor

        rows = []
        for pesquisador_id, data in agg.items():
            taxa = round((data["icp_a"] + data["icp_b"]) / data["total"] * 100) if data["total"] else 0
            rows.append(PerformanceReportRow(
                pesquisador_id=pesquisador_id, pesquisador_nome=nomes.get(pesquisador_id, "—"),
                taxa_qualificacao=taxa, **data,
            ))
        rows.sort(key=lambda r: (-r.taxa_qualificacao, -r.promovidos))
        return PerformanceReportResponse(mes=mes, rows=rows)
