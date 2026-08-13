"""Serviço de contatos."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.contact import Contact
from app.repositories.company import CompanyRepository
from app.repositories.contact import ContactRepository
from app.schemas.common import PageParams
from app.schemas.contact import ContactCreate, ContactFilterOptions, ContactUpdate
from app.services.workflow_events import publish_event


class ContactService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ContactRepository(db)
        self.companies = CompanyRepository(db)

    def list(self, params: PageParams, company_id: UUID | None = None, busca: str | None = None,
             cargo: str | None = None, tem_whatsapp: bool | None = None) -> tuple[list[Contact], int]:
        filters = self._filters(company_id, busca, cargo, tem_whatsapp)
        return self.repo.list(*filters, offset=params.offset, limit=params.size,
                              order_by=Contact.nome)

    def list_for_export(self, company_id: UUID | None = None, busca: str | None = None,
                        cargo: str | None = None, tem_whatsapp: bool | None = None) -> "list[Contact]":
        # anotação em string: `list` já é sombreado pelo método list() desta classe
        filters = self._filters(company_id, busca, cargo, tem_whatsapp)
        items, _ = self.repo.list(*filters, offset=0, limit=1_000_000, order_by=Contact.nome)
        return items

    def _filters(self, company_id, busca, cargo, tem_whatsapp):
        filters = []
        if company_id:
            filters.append(Contact.company_id == company_id)
        if busca:
            filters.append(self.repo.search_filter(busca))
        if cargo:
            filters.append(Contact.cargo.ilike(f"%{cargo}%"))
        if tem_whatsapp:
            filters.append(Contact.whatsapp.isnot(None))
            filters.append(Contact.whatsapp != "")
        return filters

    def filter_options(self) -> ContactFilterOptions:
        return ContactFilterOptions(cargo=self.repo.distinct_values(Contact.cargo))

    def get(self, contact_id: UUID) -> Contact:
        contact = self.repo.get(contact_id)
        if contact is None:
            raise NotFoundError("Contato não encontrado")
        return contact

    def create(self, data: ContactCreate) -> Contact:
        company = self.companies.get(data.company_id)
        if company is None:
            raise NotFoundError("Empresa do contato não encontrada")
        # Mesmo e-mail na mesma empresa = mesmo contato — evita duplicar quando o
        # formulário/import é reenviado (ex.: duplo clique em "Salvar", reenvio do mesmo
        # arquivo de importação). Só se aplica quando há e-mail informado.
        if data.email and self.repo.get_by_company_and_email(data.company_id, data.email):
            raise ConflictError("Já existe um contato com este e-mail nesta empresa")
        # Contato nunca tem dono independente da empresa — responsavel_id não existe em
        # ContactCreate (ver app/schemas/contact.py), é sempre herdado daqui.
        contact = Contact(**data.model_dump(), responsavel_id=company.responsavel_id)
        contact = self.repo.add(contact)
        publish_event(self.db, "contato_criado", contact.id, {
            "cargo": contact.cargo, "_entidade_tipo": "contact", "_company_id": str(contact.company_id),
        })
        return contact

    def update(self, contact_id: UUID, data: ContactUpdate) -> Contact:
        contact = self.get(contact_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(contact, field, value)
        return self.repo.save(contact)

    def delete(self, contact_id: UUID) -> None:
        contact = self.get(contact_id)
        self.repo.delete(contact)
