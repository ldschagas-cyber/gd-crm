"""Serviço de empresas: CRUD, dedupe por CNPJ, status e timeline."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import get_current_user_id
from app.core.exceptions import ConflictError, NotFoundError
from app.models.company import Company, CompanyStatus
from app.models.timeline import TimelineType
from app.repositories.company import CompanyRepository
from app.schemas.common import PageParams
from app.schemas.company import CompanyCreate, CompanyFilterOptions, CompanyStatusUpdate, CompanyUpdate
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
        company = Company(**payload, created_by=get_current_user_id())
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
