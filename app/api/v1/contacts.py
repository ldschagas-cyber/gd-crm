"""Rotas de contatos, incluindo importação e exportação."""
import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.context import get_current_user_id
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AppException
from app.models.import_job import ImportType
from app.models.user import User
from app.repositories.company import CompanyRepository
from app.repositories.timeline import TimelineRepository
from app.schemas.common import Page, PageParams
from app.schemas.contact import ContactCreate, ContactEmailRead, ContactFilterOptions, ContactRead, ContactUpdate
from app.schemas.import_job import ImportJobRead
from app.schemas.timeline import TimelineEventRead, TimelineNoteCreate
from app.services.contact import ContactService
from app.services.graph_client import GraphClient
from app.services.import_job import ImportJobService
from app.services.timeline import TimelineService

router = APIRouter(prefix="/contacts", tags=["Contatos"])


@router.get("", response_model=Page[ContactRead])
def list_contacts(params: PageParams = Depends(), company_id: UUID | None = None,
                  busca: str | None = None, cargo: str | None = None,
                  tem_whatsapp: bool | None = None,
                  _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = ContactService(db).list(
        params, company_id=company_id, busca=busca, cargo=cargo, tem_whatsapp=tem_whatsapp,
    )
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
def create_contact(data: ContactCreate, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return ContactService(db).create(data)


@router.get("/export")
def export_contacts(company_id: UUID | None = None, busca: str | None = None,
                    cargo: str | None = None, tem_whatsapp: bool | None = None,
                    _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = ContactService(db).list_for_export(
        company_id=company_id, busca=busca, cargo=cargo, tem_whatsapp=tem_whatsapp,
    )
    companies = CompanyRepository(db)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["nome", "empresa", "cargo", "email", "telefone", "whatsapp", "linkedin",
                     "data_nascimento", "observacoes"])
    for c in items:
        empresa = companies.get(c.company_id)
        writer.writerow([
            c.nome, empresa.cnpj if empresa else "", c.cargo or "", c.email or "",
            c.telefone or "", c.whatsapp or "", c.linkedin or "",
            c.data_nascimento.isoformat() if c.data_nascimento else "", c.observacoes or "",
        ])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contatos.csv"},
    )


@router.post("/import", response_model=ImportJobRead, status_code=status.HTTP_202_ACCEPTED)
def import_contacts(file: UploadFile = File(...), user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=422, detail="Envie um arquivo .csv ou .xlsx")
    content = file.file.read()
    return ImportJobService(db).create_and_dispatch(
        tipo=ImportType.CONTATOS.value, filename=file.filename, content=content,
        tenant_id=user.tenant_id, user_id=user.id,
    )


@router.get("/import/{job_id}", response_model=ImportJobRead)
def get_import_job(job_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = ImportJobService(db).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job de importação não encontrado")
    return job


@router.get("/filter-options", response_model=ContactFilterOptions)
def filter_options(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ContactService(db).filter_options()


@router.get("/{contact_id}", response_model=ContactRead)
def get_contact(contact_id: UUID, _: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return ContactService(db).get(contact_id)


@router.put("/{contact_id}", response_model=ContactRead)
def update_contact(contact_id: UUID, data: ContactUpdate, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    return ContactService(db).update(contact_id, data)


@router.get("/{contact_id}/emails", response_model=list[ContactEmailRead])
def get_contact_emails(contact_id: UUID, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Busca sob demanda na caixa conectada — nada fica salvo no CRM."""
    contact = ContactService(db).get(contact_id)
    if not contact.email:
        raise AppException("Este contato não tem e-mail cadastrado.")

    user_id = get_current_user_id()
    messages = GraphClient(db).search_mail(user_id, contact.email)

    result = []
    for m in messages:
        from_addr = ((m.get("from") or {}).get("emailAddress") or {}).get("address", "").lower()
        direcao = "recebido" if from_addr == contact.email.lower() else "enviado"
        result.append(ContactEmailRead(
            assunto=m.get("subject") or "(sem assunto)",
            resumo=m.get("bodyPreview") or "",
            quando=m.get("receivedDateTime"),
            direcao=direcao,
        ))
    return result


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: UUID, _: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    ContactService(db).delete(contact_id)
    return None


@router.get("/{contact_id}/timeline", response_model=Page[TimelineEventRead])
def get_contact_timeline(contact_id: UUID, params: PageParams = Depends(),
                         _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ContactService(db).get(contact_id)  # valida existência/tenant
    items, total = TimelineRepository(db).list_by_contact(contact_id, params.offset, params.size)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("/{contact_id}/timeline", response_model=TimelineEventRead, status_code=status.HTTP_201_CREATED)
def add_contact_note(contact_id: UUID, data: TimelineNoteCreate, _: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    contact = ContactService(db).get(contact_id)
    return TimelineService(db).registrar_from_schema(contact.company_id, data, contact_id=contact.id)
