"""Serviço de jobs de importação: cria o registro e despacha a task Celery."""
import base64
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.import_job import ImportJob, ImportStatus, ImportType
from app.repositories.import_job import ImportJobRepository
from app.workers.tasks import (
    import_companies_contacts_task, import_companies_task, import_contacts_task, import_lead_prospects_task,
)

_TASK_BY_TYPE = {
    ImportType.EMPRESAS.value: import_companies_task,
    ImportType.CONTATOS.value: import_contacts_task,
    ImportType.EMPRESAS_CONTATOS.value: import_companies_contacts_task,
    ImportType.LEAD_PROSPECTS.value: import_lead_prospects_task,
}


class ImportJobService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ImportJobRepository(db)

    def create_and_dispatch(
        self, tipo: str, filename: str, content: bytes,
        tenant_id: UUID, user_id: UUID,
    ) -> ImportJob:
        job = ImportJob(
            tipo=tipo, arquivo=filename, status=ImportStatus.PENDENTE.value,
            created_by=user_id,
        )
        job = self.repo.add(job)
        # Celery usa serialização JSON: bytes precisam ir em base64.
        task = _TASK_BY_TYPE[tipo]
        task.delay(
            job_id=str(job.id), tenant_id=str(tenant_id), user_id=str(user_id),
            content=base64.b64encode(content).decode("ascii"), filename=filename,
        )
        return job

    def get(self, job_id: UUID) -> ImportJob | None:
        return self.repo.get(job_id)

    def list_recent(self, offset: int, limit: int) -> tuple[list[ImportJob], int]:
        return self.repo.list_recent(offset, limit)
