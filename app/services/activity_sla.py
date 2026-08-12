"""SLA Comercial: CRUD de regras + motor de cálculo (ver docs/PLANO_SLA_COMERCIAL.md).

O SLA por etapa de negócio já existe (`PipelineStage.sla_horas`, usado por
`DashboardService._sla_breaches`) — este serviço soma os dois gatilhos que faltavam
(`company_status`/`milestone`) e devolve os três juntos numa única lista (`resumo()`), sem
alterar o cálculo de `deal_stage` já em produção.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.core.exceptions import NotFoundError
from app.models.activity_sla_rule import ActivitySlaMilestoneHit, ActivitySlaRule, SlaGatilhoTipo
from app.models.company import Company
from app.models.deal import Deal, DealStatus
from app.models.pipeline import PipelineStage
from app.models.task import Task, TaskStatus
from app.repositories.activity_sla_rule import ActivitySlaMilestoneHitRepository, ActivitySlaRuleRepository
from app.schemas.activity_sla_rule import (
    ActivitySlaRuleCreate, ActivitySlaRuleUpdate, SlaResumoItem, SlaResumoResponse, SlaResumoStats,
)


class ActivitySlaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ActivitySlaRuleRepository(db)
        self.hits = ActivitySlaMilestoneHitRepository(db)

    # ---- CRUD de regras -----------------------------------------------------
    def list_rules(self) -> list[ActivitySlaRule]:
        items, _ = self.repo.list(limit=500, order_by=ActivitySlaRule.ordem)
        return items

    def get_rule(self, rule_id: UUID) -> ActivitySlaRule:
        rule = self.repo.get(rule_id)
        if rule is None:
            raise NotFoundError("Regra de SLA não encontrada")
        return rule

    def create_rule(self, data: ActivitySlaRuleCreate) -> ActivitySlaRule:
        rule = ActivitySlaRule(
            nome=data.nome, gatilho_tipo=data.gatilho_tipo.value, gatilho_valor=data.gatilho_valor.value,
            prazo_horas=data.prazo_horas,
            tipo_atividade_esperado=data.tipo_atividade_esperado.value if data.tipo_atividade_esperado else None,
            ativo=data.ativo, ordem=data.ordem,
        )
        return self.repo.add(rule)

    def update_rule(self, rule_id: UUID, data: ActivitySlaRuleUpdate) -> ActivitySlaRule:
        rule = self.get_rule(rule_id)
        payload = data.model_dump(exclude_unset=True)
        for field, value in payload.items():
            rule_value = value.value if hasattr(value, "value") else value
            setattr(rule, field, rule_value)
        return self.repo.save(rule)

    def delete_rule(self, rule_id: UUID) -> None:
        rule = self.get_rule(rule_id)
        self.repo.delete(rule)

    # ---- Motor de cálculo -----------------------------------------------------
    # "Em risco" = falta 25% ou menos do prazo total pra vencer. Mesmo corte pros três
    # gatilhos — não é configurável por regra nesta primeira fase (ver plano §6).
    RISCO_FRACAO = 0.25

    @staticmethod
    def estado_regra(gatilho_em: datetime, prazo_horas: int, cumprida_em: datetime | None,
                     agora: datetime | None = None) -> dict:
        """Puro — sem I/O — testável sem banco (ver tests/test_activity_sla.py). Devolve
        {estado, prazo_em, horas_restantes, horas_atraso}."""
        agora = agora or datetime.now(timezone.utc)
        prazo_em = gatilho_em + timedelta(hours=prazo_horas)
        if cumprida_em is not None and cumprida_em <= prazo_em:
            return {"estado": "cumprido", "prazo_em": prazo_em, "horas_restantes": None, "horas_atraso": None}
        if agora > prazo_em:
            atraso = (agora - prazo_em).total_seconds() / 3600
            return {"estado": "estourado", "prazo_em": prazo_em, "horas_restantes": None,
                    "horas_atraso": round(atraso, 1)}
        restante = (prazo_em - agora).total_seconds() / 3600
        estado = "em_risco" if restante <= prazo_horas * ActivitySlaService.RISCO_FRACAO else "em_andamento"
        return {"estado": estado, "prazo_em": prazo_em, "horas_restantes": round(restante, 1), "horas_atraso": None}

    def _cumprida_em(self, company_id: UUID, desde: datetime, tipo_atividade: str | None) -> datetime | None:
        """Primeira tarefa concluída da empresa, do tipo certo (quando exigido), depois do
        gatilho — "cumprir" o SLA é uma atividade real registrada, não só o prazo não ter
        vencido ainda (ver plano §1, decisão 1)."""
        stmt = select(Task.concluida_em).where(
            Task.tenant_id == get_current_tenant(), Task.company_id == company_id,
            Task.status == TaskStatus.CONCLUIDA.value, Task.concluida_em.isnot(None),
            Task.concluida_em >= desde,
        )
        if tipo_atividade:
            stmt = stmt.where(Task.tipo == tipo_atividade)
        stmt = stmt.order_by(Task.concluida_em.asc())
        return self.db.execute(stmt).scalars().first()

    def _company_status_items(self, rules: list[ActivitySlaRule]) -> list[SlaResumoItem]:
        by_status: dict[str, list[ActivitySlaRule]] = {}
        for r in rules:
            if r.gatilho_tipo == SlaGatilhoTipo.COMPANY_STATUS.value and r.ativo:
                by_status.setdefault(r.gatilho_valor, []).append(r)
        if not by_status:
            return []
        stmt = select(Company).where(
            Company.tenant_id == get_current_tenant(), Company.deleted_at.is_(None),
            Company.status.in_(list(by_status.keys())),
            # Sem `status_atualizado_em` não há de quando contar o prazo — empresas que já
            # existiam antes desta coluna simplesmente ficam fora até a próxima mudança de
            # status (ver plano §2, sem backfill por inferência).
            Company.status_atualizado_em.isnot(None),
        )
        items = []
        for company in self.db.execute(stmt).scalars().all():
            for rule in by_status[company.status]:
                cumprida_em = self._cumprida_em(company.id, company.status_atualizado_em,
                                                rule.tipo_atividade_esperado)
                calc = self.estado_regra(company.status_atualizado_em, rule.prazo_horas, cumprida_em)
                items.append(SlaResumoItem(
                    origem="company_status", regra_id=rule.id, regra_nome=rule.nome,
                    company_id=company.id, empresa_nome=company.razao_social,
                    responsavel_id=company.responsavel_id, gatilho_em=company.status_atualizado_em,
                    cumprida_em=cumprida_em, prazo_horas=rule.prazo_horas, **calc,
                ))
        return items

    def _milestone_items(self, rules: list[ActivitySlaRule]) -> list[SlaResumoItem]:
        milestone_rules = [r for r in rules if r.gatilho_tipo == SlaGatilhoTipo.MILESTONE.value and r.ativo]
        if not milestone_rules:
            return []
        by_status: dict[str, list[ActivitySlaRule]] = {}
        for r in milestone_rules:
            by_status.setdefault(r.gatilho_valor, []).append(r)
        stmt = select(Company).where(
            Company.tenant_id == get_current_tenant(), Company.deleted_at.is_(None),
            Company.status.in_(list(by_status.keys())),
        )
        companies = self.db.execute(stmt).scalars().all()
        if not companies:
            return []

        company_ids = [c.id for c in companies]
        rule_ids = [r.id for r in milestone_rules]
        existentes = {(h.rule_id, h.company_id): h for h in self.hits.get_by_rule_and_companies(rule_ids, company_ids)}

        items = []
        for company in companies:
            for rule in by_status[company.status]:
                hit = existentes.get((rule.id, company.id))
                if hit is None:
                    # Primeira vez que vemos esta empresa neste status pra esta regra — grava
                    # o marco agora (side effect intencional deste GET, análogo ao que
                    # `advance_funil_on_*` já faz em CompanyService pra outros gatilhos
                    # automáticos). Ancorado em `status_atualizado_em` quando disponível
                    # (honra a data real da transição, mesmo pra empresa que já estava neste
                    # status antes da regra existir); cai pro momento atual senão.
                    gatilho_em = company.status_atualizado_em or datetime.now(timezone.utc)
                    hit = ActivitySlaMilestoneHit(rule_id=rule.id, company_id=company.id, disparado_em=gatilho_em)
                    hit = self.hits.add(hit)
                    existentes[(rule.id, company.id)] = hit
                cumprida_em = self._cumprida_em(company.id, hit.disparado_em, rule.tipo_atividade_esperado)
                calc = self.estado_regra(hit.disparado_em, rule.prazo_horas, cumprida_em)
                items.append(SlaResumoItem(
                    origem="milestone", regra_id=rule.id, regra_nome=rule.nome,
                    company_id=company.id, empresa_nome=company.razao_social,
                    responsavel_id=company.responsavel_id, gatilho_em=hit.disparado_em,
                    cumprida_em=cumprida_em, prazo_horas=rule.prazo_horas, **calc,
                ))
        return items

    def _deal_stage_items(self) -> list[SlaResumoItem]:
        """Mesmo dado-fonte de `DashboardService._sla_breaches` (não reaproveitado direto pra
        não criar dependência cruzada entre services de domínios diferentes), só que devolvido
        pra todos os estados, não só o estourado — o gatilho aqui é "sem interação" (igual ao
        Dashboard já mede), não "tarefa concluída": etapa de negócio não tem
        `tipo_atividade_esperado`, então não existe um "cumprido" pontual pra ela."""
        t = get_current_tenant()
        rows = self.db.execute(
            select(Deal, PipelineStage, Company)
            .join(PipelineStage, Deal.stage_id == PipelineStage.id)
            .join(Company, Deal.company_id == Company.id)
            .where(Deal.tenant_id == t, Deal.status == DealStatus.ABERTO.value,
                   PipelineStage.sla_horas.isnot(None))
        ).all()
        items = []
        for deal, stage, company in rows:
            calc = self.estado_regra(deal.ultima_interacao, stage.sla_horas, None)
            if calc["estado"] == "cumprido":  # nunca deveria ocorrer (cumprida_em=None acima), defensivo
                calc["estado"] = "em_andamento"
            items.append(SlaResumoItem(
                origem="deal_stage", regra_id=stage.id, regra_nome=f"{stage.nome} (Pipeline)",
                company_id=company.id, empresa_nome=company.razao_social,
                responsavel_id=deal.responsavel_id, gatilho_em=deal.ultima_interacao,
                cumprida_em=None, prazo_horas=stage.sla_horas, deal_id=deal.id, deal_nome=deal.nome, **calc,
            ))
        return items

    def resumo(self) -> SlaResumoResponse:
        rules = self.list_rules()
        items = self._company_status_items(rules) + self._milestone_items(rules) + self._deal_stage_items()
        stats = SlaResumoStats(
            em_dia=sum(1 for i in items if i.estado == "em_andamento"),
            em_risco=sum(1 for i in items if i.estado == "em_risco"),
            estourado=sum(1 for i in items if i.estado == "estourado"),
            cumprido=sum(1 for i in items if i.estado == "cumprido"),
            regras_ativas=sum(1 for r in rules if r.ativo),
            regras_total=len(rules),
        )
        return SlaResumoResponse(stats=stats, items=items)
