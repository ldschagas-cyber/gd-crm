"""OnboardingService — checklist de implantação do Customer Success.

Ver docs/PLANO_CUSTOMER_SUCCESS.md §2 e §4. Template único por tenant nesta primeira
fase (sem variação por segmento/produto) — mesmo padrão de config por tenant já usado
por `icp_scoring_rules`/`lead_score_rules` (ver CompanyService), guardado em
`Tenant.config["onboarding_template"]`.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.onboarding import OnboardingChecklistItem, OnboardingItemStatus
from app.repositories.onboarding import OnboardingChecklistItemRepository
from app.schemas.onboarding import OnboardingItemStatusUpdate
from app.services.tenant import TenantService

DEFAULT_ONBOARDING_TEMPLATE = [
    "Kickoff com o time do cliente",
    "Configuração inicial da conta",
    "Importação de base de contatos",
    "Treinamento do time comercial",
    "Integração com ERP/TMS",
    "Validação de resultados da 1ª semana",
]


class OnboardingService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OnboardingChecklistItemRepository(db)

    def get_template(self) -> list[str]:
        tenant = TenantService(self.db).get_current()
        stored = (tenant.config or {}).get("onboarding_template") if tenant.config else None
        return stored or DEFAULT_ONBOARDING_TEMPLATE

    def update_template(self, titulos: list[str]) -> list[str]:
        tenant = TenantService(self.db).get_current()
        config = dict(tenant.config or {})
        config["onboarding_template"] = titulos
        tenant.config = config
        self.db.flush()
        return titulos

    def create_for_company(self, company_id: UUID) -> list[OnboardingChecklistItem]:
        """Chamado por CompanyService.advance_cs_on_deal_ganho quando a empresa entra
        na fase `implantacao`. Idempotente: não duplica se a empresa já tem checklist
        (ex.: negócio reaberto/ganho de novo, ou chamada repetida)."""
        existentes = self.repo.list_by_company(company_id)
        if existentes:
            return existentes
        itens = [
            self.repo.add(OnboardingChecklistItem(company_id=company_id, titulo=titulo, ordem=i))
            for i, titulo in enumerate(self.get_template())
        ]
        return itens

    def list_by_company(self, company_id: UUID) -> list[OnboardingChecklistItem]:
        return self.repo.list_by_company(company_id)

    def progress(self, company_id: UUID) -> int:
        itens = self.repo.list_by_company(company_id)
        if not itens:
            return 0
        concluidos = sum(1 for i in itens if i.status == OnboardingItemStatus.CONCLUIDO.value)
        return round(concluidos / len(itens) * 100)

    def set_item_status(self, company_id: UUID, item_id: UUID, data: OnboardingItemStatusUpdate) -> OnboardingChecklistItem:
        item = self.repo.get(item_id)
        if item is None or item.company_id != company_id:
            raise NotFoundError("Item de checklist não encontrado")
        if data.status not in (OnboardingItemStatus.PENDENTE.value, OnboardingItemStatus.CONCLUIDO.value):
            raise ConflictError("Status inválido")
        item.status = data.status
        item.concluido_em = datetime.now(timezone.utc) if data.status == OnboardingItemStatus.CONCLUIDO.value else None
        item = self.repo.save(item)

        # implantacao -> ativo é automático quando o checklist inteiro fecha (import
        # tardio: CompanyService importa serviços que podem tocar onboarding no futuro,
        # mesmo padrão de import cíclico já usado em TimelineService/CompanyService).
        itens = self.repo.list_by_company(company_id)
        if itens and all(i.status == OnboardingItemStatus.CONCLUIDO.value for i in itens):
            from app.services.company import CompanyService
            CompanyService(self.db).advance_cs_on_onboarding_completo(company_id)
        return item
