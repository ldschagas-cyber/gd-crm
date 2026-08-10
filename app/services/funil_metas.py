"""Metas do Funil — controle de mudança de fase por percentual (Anexo 1).

Cruza domínios que já existem (LeadProspect, TimelineEvent, Deal) sem nenhuma tabela
nova — ver docs/PLANO_METAS_FUNIL.md. Dois modos de leitura (§4 do plano):

- "atividade": conta eventos ocorridos dentro do período, qualquer que seja a origem
  da empresa (mais simples, mais estável mês a mês).
- "coorte": fixa o conjunto de LeadProspect criados no período e mede, para essas
  mesmas empresas, quanto avançaram até hoje — é a leitura literal do Anexo 1 (uma
  leva de 300 vira, no fim, 10 clientes), mas coortes recentes vão aparecer com
  números baixos nas últimas etapas simplesmente porque o ciclo ainda não correu.
"""
from datetime import datetime, timezone
from uuid import UUID

from app.core.exceptions import AppException
from app.models.deal import Deal, DealStatus
from app.models.lead_prospect import LeadProspect
from app.models.pipeline import PipelineStage
from app.models.timeline import TimelineEvent, TimelineType
from app.repositories.deal import DealRepository
from app.repositories.lead_prospect import LeadProspectRepository
from app.repositories.pipeline import StageRepository
from app.repositories.timeline import TimelineRepository
from app.schemas.funil_metas import ETAPAS_CHAVES, FunilEtapaResumo, FunilMetasConfig, FunilMetasResumo
from app.services.tenant import TenantService

NOMES = {
    "pesquisadas": "Empresas pesquisadas",
    "decisores": "Decisores identificados",
    "contatos": "Contatos realizados",
    "reunioes": "Reuniões marcadas",
    "diagnosticos": "Diagnósticos realizados",
    "propostas": "Propostas enviadas",
    "fechados": "Clientes fechados",
}
CADEIA = ["pesquisadas"] + ETAPAS_CHAVES  # ordem fixa, topo -> fundo do funil


class FunilMetasService:
    def __init__(self, db):
        self.db = db
        self.leads = LeadProspectRepository(db)
        self.timeline = TimelineRepository(db)
        self.deals = DealRepository(db)
        self.stages = StageRepository(db)
        self.tenant_service = TenantService(db)

    # ---- config (por tenant, mesmo container de icp_scoring_rules) --------
    def get_config(self) -> dict:
        tenant = self.tenant_service.get_current()
        stored = (tenant.config or {}).get("funil_metas") if tenant.config else None
        return stored if stored else FunilMetasConfig().model_dump()

    def update_config(self, data: FunilMetasConfig) -> dict:
        tenant = self.tenant_service.get_current()
        config = dict(tenant.config or {})
        config["funil_metas"] = data.model_dump()
        tenant.config = config
        self.db.flush()
        return config["funil_metas"]

    # ---- resumo -------------------------------------------------------
    def resumo(self, modo: str, mes: str) -> FunilMetasResumo:
        if modo not in ("coorte", "atividade"):
            raise AppException("Modo inválido — use 'coorte' ou 'atividade'")
        start, end = self._periodo_bounds(mes)
        reais = self._reais_atividade(start, end) if modo == "atividade" else self._reais_coorte(start, end)
        return self._montar_resumo(modo, mes, self.get_config(), reais)

    def _periodo_bounds(self, mes: str) -> tuple[datetime, datetime]:
        try:
            year, month = (int(p) for p in mes.split("-"))
            if not 1 <= month <= 12:
                raise ValueError
        except ValueError:
            raise AppException("Mês inválido — use o formato AAAA-MM")
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if month == 12 else datetime(year, month + 1, 1, tzinfo=timezone.utc)
        return start, end

    def _stage_ids_for_marco(self, marco: str) -> list[UUID]:
        stages, _ = self.stages.list(PipelineStage.marco_funil == marco, limit=1000)
        return [s.id for s in stages]

    def _deal_ids_reached_marco(
        self, marco: str, *, deal_ids: "set[UUID] | None" = None, deals: "list[Deal] | None" = None,
        start: datetime | None = None, end: datetime | None = None,
    ) -> "set[UUID]":
        """Negócios que já passaram pela etapa marcada como `marco` — pela posição
        atual (`deals`, se vier) ou pelo histórico de TimelineEvent tipo=pipeline
        (`meta.para`, gravado tanto na criação quanto em toda movimentação — ver
        DealService.create/move_stage). Sem etapa marcada no Pipeline, a contagem é
        sempre zero (nada a comparar) — ver seletor em Configuração > Pipeline."""
        stage_ids = self._stage_ids_for_marco(marco)
        if not stage_ids:
            return set()
        reached: "set[UUID]" = set()
        if deals is not None:
            reached |= {d.id for d in deals if d.stage_id in stage_ids}
        if deal_ids is not None and not deal_ids:
            return reached
        filters = [
            TimelineEvent.tipo == TimelineType.PIPELINE.value,
            TimelineEvent.evento_meta["para"].astext.in_([str(s) for s in stage_ids]),
        ]
        if deal_ids is not None:
            filters.append(TimelineEvent.deal_id.in_(deal_ids))
        if start is not None:
            filters.append(TimelineEvent.created_at >= start)
        if end is not None:
            filters.append(TimelineEvent.created_at < end)
        events, _ = self.timeline.list(*filters, limit=100_000)
        reached |= {e.deal_id for e in events if e.deal_id is not None}
        return reached

    def _reais_atividade(self, start: datetime, end: datetime) -> dict:
        leads, _ = self.leads.list(LeadProspect.created_at >= start, LeadProspect.created_at < end, limit=100_000)
        pesquisadas = len(leads)
        decisores = sum(1 for l in leads if l.contato_sugerido)

        contatos_ev, _ = self.timeline.list(
            TimelineEvent.tipo.in_([TimelineType.LIGACAO.value, TimelineType.EMAIL.value]),
            TimelineEvent.created_at >= start, TimelineEvent.created_at < end, limit=100_000,
        )
        contatos = len({e.company_id for e in contatos_ev})

        reunioes_ev, _ = self.timeline.list(
            TimelineEvent.tipo == TimelineType.REUNIAO.value,
            TimelineEvent.created_at >= start, TimelineEvent.created_at < end, limit=100_000,
        )
        reunioes = len({e.company_id for e in reunioes_ev})

        diagnosticos = len(self._deal_ids_reached_marco("diagnostico", start=start, end=end))
        propostas = len(self._deal_ids_reached_marco("proposta", start=start, end=end))

        fechados_deals, _ = self.deals.list(
            Deal.status == DealStatus.GANHO.value,
            Deal.data_fechamento >= start, Deal.data_fechamento < end, limit=100_000,
        )
        fechados = len(fechados_deals)

        return {"pesquisadas": pesquisadas, "decisores": decisores, "contatos": contatos,
                "reunioes": reunioes, "diagnosticos": diagnosticos, "propostas": propostas,
                "fechados": fechados}

    def _reais_coorte(self, start: datetime, end: datetime) -> dict:
        leads, _ = self.leads.list(LeadProspect.created_at >= start, LeadProspect.created_at < end, limit=100_000)
        pesquisadas = len(leads)
        decisores = sum(1 for l in leads if l.contato_sugerido)
        company_ids = {l.promoted_company_id for l in leads if l.promoted_company_id}

        if not company_ids:
            return {"pesquisadas": pesquisadas, "decisores": decisores, "contatos": 0,
                    "reunioes": 0, "diagnosticos": 0, "propostas": 0, "fechados": 0}

        contatos_ev, _ = self.timeline.list(
            TimelineEvent.company_id.in_(company_ids),
            TimelineEvent.tipo.in_([TimelineType.LIGACAO.value, TimelineType.EMAIL.value]),
            limit=100_000,
        )
        contatos = len({e.company_id for e in contatos_ev})

        reunioes_ev, _ = self.timeline.list(
            TimelineEvent.company_id.in_(company_ids), TimelineEvent.tipo == TimelineType.REUNIAO.value,
            limit=100_000,
        )
        reunioes = len({e.company_id for e in reunioes_ev})

        deals_cohort, _ = self.deals.list(Deal.company_id.in_(company_ids), limit=100_000)
        deal_ids = {d.id for d in deals_cohort}

        diagnosticos = len(self._deal_ids_reached_marco("diagnostico", deal_ids=deal_ids, deals=deals_cohort))
        propostas = len(self._deal_ids_reached_marco("proposta", deal_ids=deal_ids, deals=deals_cohort))
        fechados = sum(1 for d in deals_cohort if d.status == DealStatus.GANHO.value)

        return {"pesquisadas": pesquisadas, "decisores": decisores, "contatos": contatos,
                "reunioes": reunioes, "diagnosticos": diagnosticos, "propostas": propostas,
                "fechados": fechados}

    def _montar_resumo(self, modo: str, mes: str, config: dict, reais: dict) -> FunilMetasResumo:
        base_meta = config["empresas_pesquisadas_meta"]
        pcts = {e["chave"]: e["pct_etapa_anterior"] for e in config["etapas"]}

        metas = {"pesquisadas": base_meta}
        for i, chave in enumerate(CADEIA[1:], start=1):
            metas[chave] = round(metas[CADEIA[i - 1]] * pcts[chave] / 100)

        etapas_resumo = []
        for i, chave in enumerate(CADEIA):
            meta, real = metas[chave], reais[chave]
            if i == 0:
                pct_meta_ant = pct_real_ant = diff = None
                # Sem etapa anterior pra comparar percentual — usa a própria meta
                # absoluta como referência (85% dela já conta como "no ritmo").
                status = "ok" if meta == 0 or real >= meta else ("atencao" if real >= meta * 0.85 else "critico")
            else:
                real_ant = reais[CADEIA[i - 1]]
                pct_meta_ant = float(pcts[chave])
                pct_real_ant = (real / real_ant * 100) if real_ant else 0.0
                diff = pct_real_ant - pct_meta_ant
                status = "ok" if diff >= -5 else ("atencao" if diff >= -15 else "critico")
            etapas_resumo.append(FunilEtapaResumo(
                chave=chave, nome=NOMES[chave], meta=meta, real=real,
                pct_meta_etapa_anterior=pct_meta_ant, pct_real_etapa_anterior=pct_real_ant,
                diferenca_pp=diff, status=status,
            ))
        return FunilMetasResumo(modo=modo, periodo=mes, etapas=etapas_resumo)
