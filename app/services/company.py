"""Serviço de empresas: CRUD, dedupe por CNPJ, status, timeline e Central de Leads."""
from datetime import datetime, time as dt_time, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant, get_current_user_id
from app.core.exceptions import ConflictError, NotFoundError
from app.models.company import Company, CompanyStatus, FunilEstagio
from app.models.sequence import SequenceEnrollment
from app.models.task import Task, TaskStatus
from app.models.timeline import TimelineEvent, TimelineType
from app.repositories.company import CompanyRepository
from app.schemas.common import PageParams
from app.schemas.company import (
    CadenciaInfoRead, CentralLeadRead, CentralLeadsResumo, CompanyCreate, CompanyDossierUpdate,
    CompanyFilterOptions, CompanyFunilEstagioUpdate, CompanyIcpRead, CompanyStatusUpdate, CompanyUpdate,
    EstagioCountRead, LeadScoreRules, ProximaAcaoRead,
)
from app.services.engagement_scoring import DEFAULT_ENGAGEMENT_RULES, JANELA_DIAS, calcular_engajamento, temperatura
from app.services.icp_scoring import DEFAULT_ICP_RULES, calcular_icp, faixa_de_num_funcionarios
from app.services.tenant import TenantService
from app.services.timeline import TimelineService
from app.services.workflow_events import publish_event


class CompanyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CompanyRepository(db)
        self.timeline = TimelineService(db)

    def list(self, params: PageParams, status: str | None = None, uf: str | None = None,
             busca: str | None = None, responsavel_id: UUID | None = None,
             segmento: str | None = None, porte: str | None = None,
             origem: str | None = None) -> tuple[list[Company], int]:
        filters = self._filters(status, uf, busca, responsavel_id, segmento, porte, origem)
        return self.repo.list(*filters, offset=params.offset, limit=params.size,
                              order_by=Company.razao_social)

    def list_for_export(self, status: str | None = None, uf: str | None = None, busca: str | None = None,
                        responsavel_id: UUID | None = None, segmento: str | None = None,
                        porte: str | None = None, origem: str | None = None) -> "list[Company]":
        # anotação em string: `list` já é sombreado pelo método list() desta classe
        filters = self._filters(status, uf, busca, responsavel_id, segmento, porte, origem)
        items, _ = self.repo.list(*filters, offset=0, limit=1_000_000, order_by=Company.razao_social)
        return items

    def _filters(self, status, uf, busca, responsavel_id, segmento, porte, origem):
        filters = [Company.deleted_at.is_(None)]
        if status:
            filters.append(Company.status == status)
        if uf:
            filters.append(Company.uf == uf)
        if busca:
            filters.append(self.repo.search_filter(busca))
        if responsavel_id:
            filters.append(Company.responsavel_id == responsavel_id)
        if segmento:
            filters.append(Company.segmento.ilike(f"%{segmento}%"))
        if porte:
            filters.append(Company.porte.ilike(f"%{porte}%"))
        if origem:
            filters.append(Company.origem.ilike(f"%{origem}%"))
        return filters

    def filter_options(self) -> CompanyFilterOptions:
        return CompanyFilterOptions(
            segmento=self.repo.distinct_values(Company.segmento),
            porte=self.repo.distinct_values(Company.porte),
            origem=self.repo.distinct_values(Company.origem),
            uf=self.repo.distinct_values(Company.uf),
        )

    def get(self, company_id: UUID) -> Company:
        company = self.repo.get(company_id)
        if company is None or company.deleted_at is not None:
            raise NotFoundError("Empresa não encontrada")
        return company

    def create(self, data: CompanyCreate) -> Company:
        if data.cnpj and self.repo.get_by_cnpj(data.cnpj):
            raise ConflictError("CNPJ já cadastrado neste tenant")
        payload = data.model_dump()
        payload["status"] = data.status.value
        # Empresa nasce já "desde quando" está no status inicial — sem isso, uma regra de
        # SLA Comercial tipo "Novo lead: responder em 24h" nunca dispararia pra leads recém
        # criados (a imensa maioria: quase nada passa por set_status() logo na criação).
        company = Company(**payload, created_by=get_current_user_id(),
                          status_atualizado_em=datetime.now(timezone.utc))
        company = self.repo.add(company)
        self.timeline.registrar(company.id, TimelineType.CADASTRO.value,
                                "Empresa cadastrada", f"Status inicial: {company.status}")
        publish_event(self.db, "empresa_criada", company.id, {
            "origem": company.origem, "segmento": company.segmento, "uf": company.uf, "porte": company.porte,
            "_entidade_tipo": "company",
        })
        return company

    def update(self, company_id: UUID, data: CompanyUpdate) -> Company:
        company = self.get(company_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        company = self.repo.save(company)
        self.timeline.registrar(company.id, TimelineType.CADASTRO.value,
                                "Dados cadastrais atualizados")
        return company

    def set_status(self, company_id: UUID, data: CompanyStatusUpdate) -> Company:
        company = self.get(company_id)
        anterior = company.status
        company.status = data.status.value
        # Alimenta o SLA Comercial por status (ver docs/PLANO_SLA_COMERCIAL.md e
        # app/services/activity_sla.py) — só atualiza quando o status de fato muda, senão um
        # PUT idempotente reabriria a régua de prazo sem uma transição real ter acontecido.
        if anterior != company.status:
            company.status_atualizado_em = datetime.now(timezone.utc)
        company = self.repo.save(company)
        self.timeline.registrar(
            company.id, TimelineType.CADASTRO.value, "Mudança de status",
            f"{anterior} -> {company.status}", meta={"de": anterior, "para": company.status},
        )
        return company

    def soft_delete(self, company_id: UUID) -> None:
        company = self.get(company_id)
        company.deleted_at = datetime.now(timezone.utc)
        company.status = CompanyStatus.INATIVO.value
        self.repo.save(company)

    # ---- Dossiê Comercial ---------------------------------------------------
    def _icp_rules(self) -> dict:
        tenant = TenantService(self.db).get_current()
        stored = (tenant.config or {}).get("icp_scoring_rules") if tenant.config else None
        return {**DEFAULT_ICP_RULES, **(stored or {})}

    def _icp_result(self, company: Company, rules: dict):
        # `porte` já guarda a faixa exata quando a empresa veio de uma promoção de
        # lead (ver LeadProspectService.promote); senão, deriva do número de
        # funcionários cadastrado manualmente.
        faixa = company.porte if company.porte in rules["faixa_funcionarios"] else (
            faixa_de_num_funcionarios(company.num_funcionarios)
        )
        return calcular_icp(setor=company.setor, regiao=None, uf=company.uf,
                            faixa_funcionarios=faixa, rules=rules)

    def get_icp(self, company_id: UUID) -> CompanyIcpRead:
        company = self.get(company_id)
        icp = self._icp_result(company, self._icp_rules())
        return CompanyIcpRead(score=icp.score, fit=icp.fit, breakdown=[
            {"criterio": b.criterio, "valor": b.valor, "pontos": b.pontos} for b in icp.breakdown
        ])

    def update_dossier(self, company_id: UUID, data: CompanyDossierUpdate) -> Company:
        company = self.get(company_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        company = self.repo.save(company)
        self.timeline.registrar(company.id, TimelineType.CADASTRO.value,
                                "Dados do Dossiê Comercial atualizados")
        from app.services.company_ai import schedule_resumo_regeneration
        schedule_resumo_regeneration(self.db, company.id)
        return company

    # ---- Central de Leads -----------------------------------------------------
    # Ver docs/PLANO_CENTRAL_DE_LEADS.md. `funil_estagio` só é atribuído por: promoção
    # de LeadProspect (-> novo), primeira interação registrada (-> qualificando),
    # inscrição em Sequência (-> cadência), criação de Negócio (-> convertido) — todos
    # em outros services, que chamam os `advance_funil_on_*` abaixo — ou por PATCH
    # explícito em `/companies/{id}/funil-estagio` (única porta pra mql/sql: elas nunca
    # têm gatilho automático, mesmo quando o Lead Score cruza o corte configurado).

    def get_lead_score_rules(self) -> dict:
        tenant = TenantService(self.db).get_current()
        stored = (tenant.config or {}).get("lead_score_rules") if tenant.config else None
        return {**DEFAULT_ENGAGEMENT_RULES, **(stored or {})}

    def update_lead_score_rules(self, data: LeadScoreRules) -> dict:
        tenant = TenantService(self.db).get_current()
        config = dict(tenant.config or {})
        config["lead_score_rules"] = data.model_dump()
        tenant.config = config
        self.db.flush()
        return config["lead_score_rules"]

    def set_funil_estagio(self, company_id: UUID, data: CompanyFunilEstagioUpdate) -> Company:
        company = self.get(company_id)
        anterior = company.funil_estagio
        novo = data.funil_estagio.value
        company.funil_estagio = novo
        company.funil_estagio_atualizado_em = datetime.now(timezone.utc)
        company = self.repo.save(company)
        self.timeline.registrar(
            company.id, TimelineType.PIPELINE.value, "Estágio no funil de leads alterado",
            f"{anterior or '—'} → {novo}", meta={"de": anterior, "para": novo},
        )
        return company

    def advance_funil_on_interaction(self, company_id: UUID, tipo: str) -> None:
        """novo -> qualificando, só pra tipos que são contato de verdade. Nunca mexe se
        a empresa está fora do funil ou já saiu do estágio 'novo' — não reabre nem pula
        etapa. Chamado por TimelineService.registrar."""
        if tipo not in {"ligacao", "email", "reuniao", "nota"}:
            return
        company = self.repo.get(company_id)
        if company is None or company.funil_estagio != FunilEstagio.NOVO.value:
            return
        company.funil_estagio = FunilEstagio.QUALIFICANDO.value
        company.funil_estagio_atualizado_em = datetime.now(timezone.utc)
        self.repo.save(company)

    def advance_funil_on_cadencia(self, company_id: UUID) -> None:
        """-> cadência, só se a empresa já estiver no funil e ainda não tiver saído de
        'novo'/'qualificando'/'cadência' — nunca rebaixa mql/sql/convertido. Chamado
        por SequenceService.enroll."""
        company = self.repo.get(company_id)
        if company is None or company.funil_estagio is None:
            return
        if company.funil_estagio in (FunilEstagio.MQL.value, FunilEstagio.SQL.value, FunilEstagio.CONVERTIDO.value,
                                     FunilEstagio.CADENCIA.value):
            return
        company.funil_estagio = FunilEstagio.CADENCIA.value
        company.funil_estagio_atualizado_em = datetime.now(timezone.utc)
        self.repo.save(company)

    def advance_funil_on_convertido(self, company_id: UUID) -> None:
        """-> convertido, só se a empresa já estava sendo acompanhada no funil — criar um
        negócio para uma empresa que nunca passou pela Central de Leads (cliente antigo,
        upsell) não a insere retroativamente no funil. Chamado por DealService.create."""
        company = self.repo.get(company_id)
        if company is None or company.funil_estagio is None or company.funil_estagio == FunilEstagio.CONVERTIDO.value:
            return
        company.funil_estagio = FunilEstagio.CONVERTIDO.value
        company.funil_estagio_atualizado_em = datetime.now(timezone.utc)
        self.repo.save(company)

    # Anotações abaixo em string: `list` já é sombreado pelo método list() desta classe
    # (mesmo motivo do comentário em list_for_export, acima) — sem aspas, o `def` quebra
    # em tempo de definição (a anotação é avaliada no namespace da classe, onde `list`
    # essa altura já é o método, não o builtin).
    def _active_enrollments_by_company(self, company_ids: "list[UUID]") -> "dict[UUID, SequenceEnrollment]":
        # Só considera inscrições com `company_id` preenchido diretamente — o caso comum
        # pra leads em estágio inicial do funil (ainda sem negócio/contato específico
        # cadastrado). Uma inscrição feita só por contato ou negócio não aparece aqui como
        # "cadência ativa" da empresa; ver SequenceService.enroll, que resolve a empresa
        # nesses casos só pra fins do gatilho de estágio, não pra exibição.
        if not company_ids:
            return {}
        stmt = (
            select(SequenceEnrollment)
            .where(
                SequenceEnrollment.tenant_id == get_current_tenant(),
                SequenceEnrollment.company_id.in_(company_ids),
                SequenceEnrollment.status == "ativa",
            )
            .order_by(SequenceEnrollment.iniciado_em.desc())
        )
        result: "dict[UUID, SequenceEnrollment]" = {}
        for enr in self.db.execute(stmt).scalars().all():
            result.setdefault(enr.company_id, enr)  # desc: primeira ocorrência = mais recente
        return result

    def _next_open_task_by_company(self, company_ids: "list[UUID]") -> "dict[UUID, Task]":
        if not company_ids:
            return {}
        stmt = (
            select(Task)
            .where(
                Task.tenant_id == get_current_tenant(),
                Task.company_id.in_(company_ids),
                Task.status == TaskStatus.PENDENTE.value,
            )
            .order_by(Task.data.asc(), Task.hora.asc())
        )
        result: "dict[UUID, Task]" = {}
        for t in self.db.execute(stmt).scalars().all():
            result.setdefault(t.company_id, t)  # asc por data/hora -> primeira ocorrência = mais próxima
        return result

    def _recent_events_by_company(self, company_ids: "list[UUID]") -> "dict[UUID, list[str]]":
        if not company_ids:
            return {}
        desde = datetime.now(timezone.utc) - timedelta(days=JANELA_DIAS)
        stmt = select(TimelineEvent.company_id, TimelineEvent.tipo).where(
            TimelineEvent.tenant_id == get_current_tenant(),
            TimelineEvent.company_id.in_(company_ids),
            TimelineEvent.created_at >= desde,
        )
        result: "dict[UUID, list[str]]" = {}
        for company_id, tipo in self.db.execute(stmt).all():
            result.setdefault(company_id, []).append(tipo)
        return result

    def _resolve_proxima_acao(self, company: Company, task: Task | None) -> ProximaAcaoRead | None:
        if task is not None:
            data_hora = datetime.combine(task.data, task.hora or dt_time.min, tzinfo=timezone.utc) if task.data else None
            return ProximaAcaoRead(tipo="tarefa", texto=task.titulo, data=data_hora)
        if company.proxima_acao_sugerida:
            return ProximaAcaoRead(tipo="ia", texto=company.proxima_acao_sugerida)
        return None

    def _resolve_cadencia_info(self, enrollment: SequenceEnrollment) -> CadenciaInfoRead:
        sequence = enrollment.sequence
        return CadenciaInfoRead(
            enrollment_id=enrollment.id, sequence_id=enrollment.sequence_id,
            nome=sequence.nome if sequence else "(sequência removida)",
            etapa_atual=enrollment.step_atual, total_etapas=len(sequence.steps) if sequence else 0,
        )

    def list_central_leads(
        self, *, funil_estagio: str | None = None, responsavel_id: UUID | None = None,
        busca: str | None = None, lead_score_min: int | None = None,
        em_cadencia: bool | None = None, esconder_convertidos_apos_dias: int | None = None,
    ) -> "list[CentralLeadRead]":
        # Mesma lógica de volume de app/services/lead_prospect.py: busca tudo (teto
        # alto) e filtra/enriquece em memória — score e cadência são calculados, não
        # colunas, e o volume esperado (leads ativos no funil) é baixo.
        filters = [Company.deleted_at.is_(None), Company.funil_estagio.isnot(None)]
        if funil_estagio:
            filters.append(Company.funil_estagio == funil_estagio)
        if responsavel_id:
            filters.append(Company.responsavel_id == responsavel_id)
        if busca:
            filters.append(self.repo.search_filter(busca))
        companies, _ = self.repo.list(*filters, offset=0, limit=500, order_by=Company.razao_social)
        if not companies:
            return []

        ids = [c.id for c in companies]
        icp_rules = self._icp_rules()
        eng_rules = self.get_lead_score_rules()
        enrollments = self._active_enrollments_by_company(ids)
        next_tasks = self._next_open_task_by_company(ids)
        recent_events = self._recent_events_by_company(ids)
        agora = datetime.now(timezone.utc)

        results: "list[CentralLeadRead]" = []
        for c in companies:
            icp = self._icp_result(c, icp_rules)
            enrollment = enrollments.get(c.id)
            dias_desde = (agora - c.ultima_interacao).days if c.ultima_interacao else None
            eng = calcular_engajamento(
                eventos_tipos=recent_events.get(c.id, []),
                etapas_cadencia_concluidas=enrollment.step_atual if enrollment else 0,
                dias_desde_ultima_interacao=dias_desde,
                rules=eng_rules,
            )
            lead_score = round(icp.score * 0.6 + eng.score * 0.4)

            if lead_score_min is not None and lead_score < lead_score_min:
                continue
            if em_cadencia and enrollment is None:
                continue
            convertido_em = c.funil_estagio_atualizado_em if c.funil_estagio == FunilEstagio.CONVERTIDO.value else None
            if esconder_convertidos_apos_dias is not None and convertido_em is not None:
                if (agora - convertido_em).days > esconder_convertidos_apos_dias:
                    continue

            results.append(CentralLeadRead(
                id=c.id, razao_social=c.razao_social, nome_fantasia=c.nome_fantasia,
                segmento=c.segmento, uf=c.uf, origem=c.origem, responsavel_id=c.responsavel_id,
                funil_estagio=c.funil_estagio, funil_estagio_atualizado_em=c.funil_estagio_atualizado_em,
                ultima_interacao=c.ultima_interacao, score_icp=icp.score, score_engajamento=eng.score,
                lead_score=lead_score, temperatura=temperatura(lead_score, eng_rules),
                proxima_acao=self._resolve_proxima_acao(c, next_tasks.get(c.id)),
                cadencia=self._resolve_cadencia_info(enrollment) if enrollment else None,
                convertido_em=convertido_em,
            ))
        return results

    def resumo_central_leads(self) -> CentralLeadsResumo:
        leads = self.list_central_leads()  # sem filtro de "esconder convertidos" — resumo é sempre completo
        total = len(leads)
        ativos = [l for l in leads if l.funil_estagio != FunilEstagio.CONVERTIDO.value]
        contagem = {e.value: 0 for e in FunilEstagio}
        for l in leads:
            contagem[l.funil_estagio] = contagem.get(l.funil_estagio, 0) + 1
        agora = datetime.now(timezone.utc)
        parados = sum(1 for l in ativos if (agora - l.ultima_interacao).days >= 7)
        return CentralLeadsResumo(
            total=total, total_ativos=len(ativos),
            por_estagio=[EstagioCountRead(estagio=k, total=v) for k, v in contagem.items()],
            score_medio=round(sum(l.lead_score for l in leads) / total) if total else 0,
            parados=parados,
        )
