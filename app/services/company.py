"""Serviço de empresas: CRUD, dedupe por CNPJ, status, timeline e Central de Leads."""
from datetime import datetime, time as dt_time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant, get_current_user_id
from app.core.exceptions import ConflictError, NotFoundError
from app.models.company import Company, CompanyStatus, CsFase, FunilEstagio
from app.models.deal import Deal, DealStatus, DealTipo
from app.models.onboarding import OnboardingChecklistItem, OnboardingItemStatus
from app.models.sequence import SequenceEnrollment
from app.models.subscription import Assinatura, AssinaturaStatus
from app.models.task import Task, TaskStatus
from app.models.timeline import TimelineEvent, TimelineType
from app.repositories.company import CompanyRepository
from app.repositories.contact import ContactRepository
from app.repositories.onboarding import OnboardingChecklistItemRepository
from app.repositories.subscription import AssinaturaRepository
from app.repositories.user import UserRepository
from app.schemas.common import PageParams
from app.schemas.company import (
    AssinaturaResumoRead, CadenciaInfoRead, CentralLeadRead, CentralLeadsResumo, ClienteRead, ClientesResumo,
    CompanyCreate, CompanyCsFaseUpdate, CompanyCsUpdate, CompanyDossierUpdate, CompanyFilterOptions,
    CompanyFunilEstagioUpdate, CompanyIcpRead, CompanyStatusUpdate, CompanyUpdate, CsCheckinCreate,
    CsFaseCountRead, EstagioCountRead, HealthBreakdownItemRead, HealthScoreRead, LeadScoreRules, ProximaAcaoRead,
)
from app.services.company_dedupe import find_duplicate_company
from app.services.engagement_scoring import DEFAULT_ENGAGEMENT_RULES, JANELA_DIAS, calcular_engajamento, temperatura
from app.services.health_scoring import DEFAULT_HEALTH_RULES, calcular_saude
from app.services.health_scoring import faixa as health_faixa
from app.services.icp_scoring import DEFAULT_ICP_RULES, calcular_icp, faixa_de_num_funcionarios
from app.services.onboarding import OnboardingService
from app.services.tenant import TenantService
from app.services.timeline import TimelineService
from app.services.workflow_events import publish_event


class CompanyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CompanyRepository(db)
        self.timeline = TimelineService(db)
        self.onboarding = OnboardingService(db)
        self.assinaturas = AssinaturaRepository(db)
        self.checklist_items = OnboardingChecklistItemRepository(db)

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
        # Cascata CNPJ -> domínio corporativo -> nome normalizado+UF (ver
        # app/services/company_dedupe.py) — cobre também empresas sem CNPJ, que antes não
        # tinham proteção nenhuma contra duplicidade neste cadastro manual.
        duplicate = find_duplicate_company(
            self.repo, razao_social=data.razao_social, uf=data.uf,
            cnpj=data.cnpj, site=data.site, email=data.email,
        )
        if duplicate is not None:
            if duplicate.responsavel_id == data.responsavel_id:
                raise ConflictError("Empresa já cadastrada")
            dono = UserRepository(self.db).get(duplicate.responsavel_id) if duplicate.responsavel_id else None
            detalhe = f": {dono.nome} ({dono.email})" if dono else ""
            raise ConflictError(f"Empresa já cadastrada para outro responsável{detalhe}")
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
        payload = data.model_dump(exclude_unset=True)
        responsavel_mudou = "responsavel_id" in payload and payload["responsavel_id"] != company.responsavel_id
        for field, value in payload.items():
            setattr(company, field, value)
        company = self.repo.save(company)
        if responsavel_mudou:
            # Contato nunca tem dono independente da empresa — propaga o novo
            # responsável pra todos os contatos dela (ver app/models/contact.py).
            ContactRepository(self.db).update_responsavel_for_company(company.id, company.responsavel_id)
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

    # ---- Customer Success -------------------------------------------------------
    # Ver docs/PLANO_CUSTOMER_SUCCESS.md. `cs_fase` só é atribuído por: negócio ganho
    # (-> implantação, ver advance_cs_on_deal_ganho, chamado por DealService), checklist
    # de onboarding concluído (-> ativo), health score cruzando o corte (-> em_risco/
    # ativo), negócio de expansão aberto/fechado (-> em_expansão/ativo) — ou por PATCH
    # explícito em `/empresas/{id}/cs-fase` (nunca pra `churn`: encerramento só acontece
    # via cancelamento de Assinatura, ver advance_cs_on_assinatura_cancelada).

    def get_health_rules(self) -> dict:
        tenant = TenantService(self.db).get_current()
        stored = (tenant.config or {}).get("health_score_rules") if tenant.config else None
        return {**DEFAULT_HEALTH_RULES, **(stored or {})}

    def _transition_cs_fase(self, company: Company, nova_fase: str, *, titulo: str, descricao: str | None = None) -> Company:
        anterior = company.cs_fase
        if anterior == nova_fase:
            return company
        company.cs_fase = nova_fase
        company.cs_fase_atualizada_em = datetime.now(timezone.utc)
        company = self.repo.save(company)
        self.timeline.registrar(
            company.id, TimelineType.PIPELINE.value, titulo, descricao or f"{anterior or '—'} → {nova_fase}",
            meta={"de": anterior, "para": nova_fase},
        )
        return company

    def set_cs(self, company_id: UUID, data: CompanyCsUpdate) -> Company:
        company = self.get(company_id)
        company.cs_responsavel_id = data.cs_responsavel_id
        return self.repo.save(company)

    def set_cs_fase(self, company_id: UUID, data: CompanyCsFaseUpdate) -> Company:
        company = self.get(company_id)
        if company.cs_fase is None:
            raise ConflictError("Empresa ainda não é acompanhada pelo Customer Success")
        nova = data.cs_fase.value
        if nova == CsFase.CHURN.value:
            raise ConflictError(
                "Encerramento não é uma troca de fase direta — cancele a Assinatura "
                "(Receita Recorrente) desta empresa; a fase muda para 'churn' automaticamente."
            )
        return self._transition_cs_fase(company, nova, titulo="Fase de Customer Success alterada")

    def advance_cs_on_deal_ganho(self, company_id: UUID, deal_tipo: str, deal_responsavel_id: UUID) -> None:
        """Chamado por DealService quando um negócio entra em etapa GANHO. Só "cria" o
        cliente no Customer Success na primeira vez (cs_fase ainda None) e só para
        negócio do tipo `novo_negocio` — outro negócio novo ganho num cliente que já é
        acompanhado não regride a fase atual (ver DealTipo.EXPANSAO, tratado à parte)."""
        if deal_tipo != DealTipo.NOVO_NEGOCIO.value:
            return
        company = self.repo.get(company_id)
        if company is None or company.cs_fase is not None:
            return
        if company.status != CompanyStatus.CLIENTE.value:
            company.status = CompanyStatus.CLIENTE.value
            company.status_atualizado_em = datetime.now(timezone.utc)
        company.cs_responsavel_id = company.cs_responsavel_id or deal_responsavel_id
        company = self.repo.save(company)
        company = self._transition_cs_fase(
            company, CsFase.IMPLANTACAO.value, titulo="Negócio ganho — implantação iniciada",
            descricao="Cliente criado automaticamente no Customer Success",
        )
        self.onboarding.create_for_company(company.id)

    def advance_cs_on_expansao_aberta(self, company_id: UUID) -> None:
        """Chamado por DealService.create quando o negócio é do tipo `expansao`."""
        company = self.repo.get(company_id)
        if company is None or company.cs_fase not in (CsFase.ATIVO.value, CsFase.EM_RISCO.value):
            return
        self._transition_cs_fase(company, CsFase.EM_EXPANSAO.value, titulo="Negócio de expansão aberto")

    def advance_cs_on_expansao_fechada(self, company_id: UUID) -> None:
        """Chamado por DealService quando um negócio `expansao` fecha (ganho ou
        perdido). Só volta pra `ativo` se não houver outro negócio de expansão ainda
        aberto pra essa empresa."""
        company = self.repo.get(company_id)
        if company is None or company.cs_fase != CsFase.EM_EXPANSAO.value:
            return
        outros_abertos = self.db.execute(
            select(func.count()).select_from(Deal).where(
                Deal.tenant_id == get_current_tenant(), Deal.company_id == company_id,
                Deal.tipo == DealTipo.EXPANSAO.value, Deal.status == DealStatus.ABERTO.value,
            )
        ).scalar_one()
        if outros_abertos:
            return
        self._transition_cs_fase(company, CsFase.ATIVO.value, titulo="Negócio de expansão encerrado")

    def advance_cs_on_onboarding_completo(self, company_id: UUID) -> None:
        """Chamado por OnboardingService quando o último item do checklist fecha."""
        company = self.repo.get(company_id)
        if company is None or company.cs_fase != CsFase.IMPLANTACAO.value:
            return
        self._transition_cs_fase(
            company, CsFase.ATIVO.value, titulo="Implantação concluída",
            descricao="Checklist de onboarding 100% concluído",
        )

    def advance_cs_on_assinatura_cancelada(self, company_id: UUID) -> None:
        """Chamado por AssinaturaService.cancelar — único caminho até `churn` (ver
        set_cs_fase, que bloqueia essa fase por PATCH direto)."""
        company = self.repo.get(company_id)
        if company is None or company.cs_fase is None or company.cs_fase == CsFase.CHURN.value:
            return
        self._transition_cs_fase(
            company, CsFase.CHURN.value, titulo="Assinatura cancelada",
            descricao="Cliente encerrado no Customer Success",
        )

    def _auto_transition_risco(self, company: Company, score: int, rules: dict) -> None:
        if company.cs_fase == CsFase.ATIVO.value and score < rules["atencao_a_partir_de"]:
            self._transition_cs_fase(
                company, CsFase.EM_RISCO.value, titulo="Fase alterada para Em risco",
                descricao=f"Health Score caiu para {score}pt, abaixo do corte de {rules['atencao_a_partir_de']}pt",
            )
        elif company.cs_fase == CsFase.EM_RISCO.value and score >= rules["atencao_a_partir_de"]:
            self._transition_cs_fase(
                company, CsFase.ATIVO.value, titulo="Fase alterada para Ativo",
                descricao=f"Health Score recuperado para {score}pt",
            )

    def _health_result_read(self, result, rules: dict) -> HealthScoreRead:
        return HealthScoreRead(
            score=result.score, faixa=health_faixa(result.score, rules), engajamento=result.engajamento,
            uso=result.uso, satisfacao=result.satisfacao, financeiro=result.financeiro,
            precisa_checkin=result.precisa_checkin,
            breakdown=[HealthBreakdownItemRead(criterio=b.criterio, valor=b.valor, pontos=b.pontos)
                      for b in result.breakdown],
        )

    def get_health(self, company_id: UUID) -> HealthScoreRead:
        """Recalcula na leitura (mesmo espírito do Lead Score na Central de Leads: nunca
        confia num valor persistido parado) e persiste o resultado em `health_score` só
        como cache informativo pra listagem/relatório — não é a fonte de verdade."""
        company = self.get(company_id)
        if company.cs_fase is None:
            raise ConflictError("Empresa ainda não é acompanhada pelo Customer Success")

        assinatura = self.assinaturas.get_ativa_por_empresa(company_id) or self._latest_assinatura(company_id)
        checkin = self._latest_checkin_by_company([company_id]).get(company_id)
        recent_events = self._recent_events_by_company([company_id]).get(company_id, [])
        rules = self.get_health_rules()
        agora = datetime.now(timezone.utc)

        result = calcular_saude(
            eventos_tipos=recent_events,
            dias_desde_ultima_interacao=(agora - company.ultima_interacao).days if company.ultima_interacao else None,
            uso_percebido=(checkin.evento_meta or {}).get("uso_percebido") if checkin else None,
            ultima_satisfacao=(checkin.evento_meta or {}).get("satisfacao") if checkin else None,
            dias_desde_ultimo_checkin=(agora - checkin.created_at).days if checkin else None,
            assinatura_status=assinatura.status if assinatura else None,
            dias_ate_renovacao=(assinatura.data_renovacao - agora.date()).days if assinatura and assinatura.data_renovacao else None,
            rules=rules,
        )
        company.health_score = result.score
        company.health_score_atualizado_em = agora
        company = self.repo.save(company)
        self._auto_transition_risco(company, result.score, rules)

        return self._health_result_read(result, rules)

    def register_checkin(self, company_id: UUID, data: CsCheckinCreate) -> HealthScoreRead:
        company = self.get(company_id)
        if company.cs_fase is None:
            raise ConflictError("Empresa ainda não é acompanhada pelo Customer Success")
        self.timeline.registrar(
            company.id, TimelineType.CS_CHECKIN.value, "Check-in de Customer Success", data.notas,
            meta={"uso_percebido": data.uso_percebido, "satisfacao": data.satisfacao},
        )
        return self.get_health(company_id)

    # ---- bulk helpers pra list_clientes/resumo_clientes -----------------------

    def _latest_assinatura(self, company_id: UUID) -> Assinatura | None:
        return self._assinatura_by_company([company_id]).get(company_id)

    def _assinatura_by_company(self, company_ids: "list[UUID]") -> "dict[UUID, Assinatura]":
        if not company_ids:
            return {}
        stmt = (
            select(Assinatura)
            .where(Assinatura.tenant_id == get_current_tenant(), Assinatura.company_id.in_(company_ids))
            .order_by(Assinatura.created_at.desc())
        )
        result: "dict[UUID, Assinatura]" = {}
        for a in self.db.execute(stmt).scalars().all():
            result.setdefault(a.company_id, a)  # desc: primeira ocorrência = mais recente
        return result

    def _onboarding_progress_by_company(self, company_ids: "list[UUID]") -> "dict[UUID, int]":
        if not company_ids:
            return {}
        stmt = select(OnboardingChecklistItem.company_id, OnboardingChecklistItem.status).where(
            OnboardingChecklistItem.tenant_id == get_current_tenant(),
            OnboardingChecklistItem.company_id.in_(company_ids),
        )
        por_empresa: "dict[UUID, list[str]]" = {}
        for company_id, item_status in self.db.execute(stmt).all():
            por_empresa.setdefault(company_id, []).append(item_status)
        return {
            company_id: round(sum(1 for s in statuses if s == OnboardingItemStatus.CONCLUIDO.value) / len(statuses) * 100)
            for company_id, statuses in por_empresa.items()
        }

    def _expansao_aberta_by_company(self, company_ids: "list[UUID]") -> "set[UUID]":
        if not company_ids:
            return set()
        stmt = select(Deal.company_id).where(
            Deal.tenant_id == get_current_tenant(), Deal.company_id.in_(company_ids),
            Deal.tipo == DealTipo.EXPANSAO.value, Deal.status == DealStatus.ABERTO.value,
        ).distinct()
        return set(self.db.execute(stmt).scalars().all())

    def _latest_checkin_by_company(self, company_ids: "list[UUID]") -> "dict[UUID, TimelineEvent]":
        if not company_ids:
            return {}
        stmt = (
            select(TimelineEvent)
            .where(
                TimelineEvent.tenant_id == get_current_tenant(), TimelineEvent.company_id.in_(company_ids),
                TimelineEvent.tipo == TimelineType.CS_CHECKIN.value,
            )
            .order_by(TimelineEvent.created_at.desc())
        )
        result: "dict[UUID, TimelineEvent]" = {}
        for e in self.db.execute(stmt).scalars().all():
            result.setdefault(e.company_id, e)
        return result

    def list_clientes(
        self, *, cs_fase: str | None = None, cs_responsavel_id: UUID | None = None, busca: str | None = None,
        health_score_max: int | None = None, renovacao_ate_dias: int | None = None,
        somente_em_risco: bool = False,
    ) -> "list[ClienteRead]":
        # Mesmo racional de volume de list_central_leads: busca tudo (teto alto) e
        # enriquece em memória — Health Score é calculado, não coluna confiável pra
        # filtro no banco, e o volume esperado (clientes ativos) é baixo.
        filters = [Company.deleted_at.is_(None), Company.cs_fase.isnot(None)]
        if cs_fase:
            filters.append(Company.cs_fase == cs_fase)
        if cs_responsavel_id:
            filters.append(Company.cs_responsavel_id == cs_responsavel_id)
        if busca:
            filters.append(self.repo.search_filter(busca))
        companies, _ = self.repo.list(*filters, offset=0, limit=500, order_by=Company.razao_social)
        if not companies:
            return []

        ids = [c.id for c in companies]
        assinaturas = self._assinatura_by_company(ids)
        progresso = self._onboarding_progress_by_company(ids)
        expansoes = self._expansao_aberta_by_company(ids)
        checkins = self._latest_checkin_by_company(ids)
        recent_events = self._recent_events_by_company(ids)
        rules = self.get_health_rules()
        agora = datetime.now(timezone.utc)

        results: "list[ClienteRead]" = []
        for c in companies:
            assinatura = assinaturas.get(c.id)
            checkin = checkins.get(c.id)
            dias_renovacao = (
                (assinatura.data_renovacao - agora.date()).days
                if assinatura and assinatura.data_renovacao else None
            )
            health = calcular_saude(
                eventos_tipos=recent_events.get(c.id, []),
                dias_desde_ultima_interacao=(agora - c.ultima_interacao).days if c.ultima_interacao else None,
                uso_percebido=(checkin.evento_meta or {}).get("uso_percebido") if checkin else None,
                ultima_satisfacao=(checkin.evento_meta or {}).get("satisfacao") if checkin else None,
                dias_desde_ultimo_checkin=(agora - checkin.created_at).days if checkin else None,
                assinatura_status=assinatura.status if assinatura else None,
                dias_ate_renovacao=dias_renovacao,
                rules=rules,
            )

            if health_score_max is not None and health.score > health_score_max:
                continue
            if renovacao_ate_dias is not None and (dias_renovacao is None or dias_renovacao > renovacao_ate_dias):
                continue
            if somente_em_risco and c.cs_fase != CsFase.EM_RISCO.value:
                continue

            results.append(ClienteRead(
                id=c.id, razao_social=c.razao_social, nome_fantasia=c.nome_fantasia, segmento=c.segmento, uf=c.uf,
                cs_fase=c.cs_fase, cs_fase_atualizada_em=c.cs_fase_atualizada_em, cs_responsavel_id=c.cs_responsavel_id,
                ultima_interacao=c.ultima_interacao, health_score=health.score,
                health_faixa=health_faixa(health.score, rules), onboarding_progresso=progresso.get(c.id, 100),
                assinatura=AssinaturaResumoRead(
                    id=assinatura.id, nome_plano=assinatura.nome_plano, valor_mensal=float(assinatura.valor_mensal),
                    status=assinatura.status, data_inicio=assinatura.data_inicio,
                    ciclo_renovacao_meses=assinatura.ciclo_renovacao_meses, data_renovacao=assinatura.data_renovacao,
                ) if assinatura else None,
                expansao_aberta=c.id in expansoes,
            ))
        return results

    def resumo_clientes(self) -> ClientesResumo:
        clientes = self.list_clientes()  # sempre completo, sem filtro
        ativos = [c for c in clientes if c.cs_fase != CsFase.CHURN.value]
        total = len(ativos)
        mrr_total = sum(
            c.assinatura.valor_mensal for c in ativos if c.assinatura and c.assinatura.status == AssinaturaStatus.ATIVA.value
        )
        health_medio = (
            round(sum(c.health_score for c in ativos if c.health_score is not None) / total) if total else 0
        )
        em_risco = sum(1 for c in clientes if c.cs_fase == CsFase.EM_RISCO.value)
        hoje = datetime.now(timezone.utc).date()
        renovacao_60d = sum(
            1 for c in ativos if c.assinatura and c.assinatura.data_renovacao
            and 0 <= (c.assinatura.data_renovacao - hoje).days <= 60
        )
        contagem = {f.value: 0 for f in CsFase}
        for c in clientes:
            contagem[c.cs_fase] = contagem.get(c.cs_fase, 0) + 1
        return ClientesResumo(
            total=total, mrr_total=mrr_total, arr_total=mrr_total * 12, health_medio=health_medio,
            em_risco=em_risco, renovacao_60d=renovacao_60d,
            por_fase=[CsFaseCountRead(fase=k, total=v) for k, v in contagem.items()],
        )
