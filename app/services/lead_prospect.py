"""Serviço de pesquisa de leads: cálculo de Score ICP/Fit/Gamificação/Bônus,
CRUD e promoção para companies. Item 9.1 da especificação técnica."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.models.company import Company, CompanyStatus, FunilEstagio
from app.models.lead_prospect import LeadProspect, LeadStatus
from app.repositories.company import CompanyRepository
from app.repositories.lead_prospect import LeadProspectRepository
from app.repositories.user import UserRepository
from app.schemas.lead_prospect import (
    CommercialIntelligenceRecord, CommercialIntelligenceResponse, IcpScoringRules, LeadProspectCreate,
    LeadProspectPageParams, LeadProspectRead, LeadProspectUpdate, MetaProgressResponse, MetaProgressRow,
    PerformanceReportResponse, PerformanceReportRow,
)
from app.services.icp_scoring import DEFAULT_ICP_RULES, calcular_icp
from app.services.tenant import TenantService


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
        icp = calcular_icp(
            setor=lead.setor, regiao=lead.regiao, uf=lead.uf,
            faixa_funcionarios=lead.faixa_funcionarios, rules=rules,
        )
        score, fit = icp.score, icp.fit
        gamificacao = self._gamificacao(lead, fit)
        recebe_bonus = lead.status == LeadStatus.PROMOVIDO.value and gamificacao > 70
        bonus_valor = rules["bonus_valor"] if recebe_bonus else 0.0
        return LeadProspectRead(
            id=lead.id, empresa=lead.empresa, cnpj=lead.cnpj, setor=lead.setor, segmento=lead.segmento,
            cidade=lead.cidade, uf=lead.uf,
            regiao=lead.regiao,
            faixa_funcionarios=lead.faixa_funcionarios,
            faixa_faturamento=lead.faixa_faturamento, origem=lead.origem,
            site=lead.site, telefone=lead.telefone, linkedin=lead.linkedin, email=lead.email,
            dor_sugerida=lead.dor_sugerida,
            contato_sugerido=lead.contato_sugerido, status=lead.status, pesquisado_por=lead.pesquisado_por,
            promoted_company_id=lead.promoted_company_id, created_at=lead.created_at,
            score_icp=score, icp_fit=fit, gamificacao=gamificacao, recebe_bonus=recebe_bonus,
            bonus_valor=bonus_valor, inteligencia_comercial=lead.inteligencia_comercial,
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
        if data.segmento is not None:
            payload["segmento"] = data.segmento.value
        lead = LeadProspect(**payload)
        lead = self.repo.add(lead)
        return self.to_read(lead)

    def update(self, lead_id: UUID, data: LeadProspectUpdate) -> LeadProspectRead:
        lead = self._get_orm(lead_id)
        payload = data.model_dump(exclude_unset=True)
        if payload.get("status") is not None:
            payload["status"] = payload["status"].value
        if payload.get("segmento") is not None:
            payload["segmento"] = payload["segmento"].value
        for field, value in payload.items():
            setattr(lead, field, value)
        lead = self.repo.save(lead)
        return self.to_read(lead)

    def delete(self, lead_id: UUID) -> None:
        lead = self._get_orm(lead_id)
        self.repo.delete(lead)

    def save_inteligencia_comercial(self, lead_id: UUID, data: CommercialIntelligenceResponse) -> LeadProspectRead:
        """Grava o resultado (já gerado pelo endpoint de geração) no lead — `gravado_em`
        é sempre o momento deste PATCH, não o momento em que a IA rodou."""
        lead = self._get_orm(lead_id)
        record = CommercialIntelligenceRecord(**data.model_dump(), gravado_em=datetime.now(timezone.utc))
        lead.inteligencia_comercial = record.model_dump_json()
        lead = self.repo.save(lead)
        return self.to_read(lead)

    def promote(self, lead_id: UUID, responsavel_id: UUID | None = None) -> LeadProspectRead:
        lead = self._get_orm(lead_id)
        if lead.promoted_company_id:
            raise ConflictError("Esta pesquisa já foi promovida a empresa")
        company = Company(
            razao_social=lead.empresa, cnpj=lead.cnpj, segmento=lead.segmento, setor=lead.setor,
            cidade=lead.cidade, uf=lead.uf,
            site=lead.site, linkedin=lead.linkedin, email=lead.email, telefone=lead.telefone,
            porte=lead.faixa_funcionarios,
            responsavel_id=responsavel_id,
            # faixa_faturamento não é copiada: é uma faixa (texto), não um número, e
            # Company.faturamento_estimado é Numeric — sem base pra converter uma faixa
            # num valor exato sem inventar dado. Fica só como texto na Pesquisa de Leads.
            #
            # dor_sugerida vira problemas_encontrados: mesmo conceito (hipótese de dor),
            # só muda de nome porque no Dossiê Comercial esse campo já existia com outro
            # rótulo. contato_sugerido tem campo próprio em Company (não é Contato de
            # verdade, ver comentário no model).
            contato_sugerido=lead.contato_sugerido,
            problemas_encontrados=lead.dor_sugerida,
            status=CompanyStatus.LEAD.value, origem=lead.origem or "Pesquisa de Leads",
            inteligencia_comercial=lead.inteligencia_comercial,
            # Central de Leads: toda promoção entra no funil como "novo" — ver
            # docs/PLANO_CENTRAL_DE_LEADS.md. Empresas criadas por outro caminho (cadastro
            # manual, importação) continuam de fora até serem atribuídas manualmente.
            funil_estagio=FunilEstagio.NOVO.value,
            funil_estagio_atualizado_em=datetime.now(timezone.utc),
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

    # ---- metas de pesquisa (semanal/mensal, individual por usuário) -----------------
    def metas_progress(self) -> MetaProgressResponse:
        """Progresso sempre relativo a "agora" (semana e mês correntes) — independente
        do mês escolhido no relatório de desempenho, que pode ser um mês passado."""
        now = datetime.now(timezone.utc)
        inicio_semana = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        leads_semana, _ = self.repo.list(LeadProspect.created_at >= inicio_semana, offset=0, limit=100_000)
        leads_mes, _ = self.repo.list(LeadProspect.created_at >= inicio_mes, offset=0, limit=100_000)
        contagem_semana = Counter(lead.pesquisado_por for lead in leads_semana)
        contagem_mes = Counter(lead.pesquisado_por for lead in leads_mes)

        users, _ = UserRepository(self.db).list(offset=0, limit=1000)
        rows = []
        for user in users:
            pesquisas_semana = contagem_semana.get(user.id, 0)
            pesquisas_mes = contagem_mes.get(user.id, 0)
            # Some da lista quem nunca pesquisou e não tem meta configurada — não é um
            # SDR relevante pra essa tela.
            if user.meta_pesquisa_semanal is None and user.meta_pesquisa_mensal is None \
                    and pesquisas_semana == 0 and pesquisas_mes == 0:
                continue
            rows.append(MetaProgressRow(
                pesquisador_id=user.id, pesquisador_nome=user.nome,
                pesquisas_semana=pesquisas_semana, meta_semanal=user.meta_pesquisa_semanal,
                pesquisas_mes=pesquisas_mes, meta_mensal=user.meta_pesquisa_mensal,
            ))
        rows.sort(key=lambda r: -r.pesquisas_semana)
        return MetaProgressResponse(rows=rows)
