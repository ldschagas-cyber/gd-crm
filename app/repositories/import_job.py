"""Repositório de jobs de importação."""
from app.models.import_job import ImportJob
from app.repositories.base import BaseRepository


class ImportJobRepository(BaseRepository[ImportJob]):
    model = ImportJob

    def list_recent(self, offset: int, limit: int) -> tuple[list[ImportJob], int]:
        return self.list(offset=offset, limit=limit, order_by=ImportJob.created_at.desc())
