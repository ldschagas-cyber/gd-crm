"""Repositório de eventos de timeline."""
from uuid import UUID

from app.models.timeline import TimelineEvent
from app.repositories.base import BaseRepository


class TimelineRepository(BaseRepository[TimelineEvent]):
    model = TimelineEvent

    def list_by_company(self, company_id: UUID, offset: int, limit: int) -> tuple[list[TimelineEvent], int]:
        return self.list(
            TimelineEvent.company_id == company_id,
            offset=offset,
            limit=limit,
            order_by=TimelineEvent.created_at.desc(),
        )

    def list_by_deal(self, deal_id: UUID, offset: int, limit: int) -> tuple[list[TimelineEvent], int]:
        return self.list(
            TimelineEvent.deal_id == deal_id,
            offset=offset,
            limit=limit,
            order_by=TimelineEvent.created_at.desc(),
        )

    def list_by_contact(self, contact_id: UUID, offset: int, limit: int) -> tuple[list[TimelineEvent], int]:
        return self.list(
            TimelineEvent.contact_id == contact_id,
            offset=offset,
            limit=limit,
            order_by=TimelineEvent.created_at.desc(),
        )

    def get_by_call_sid(self, call_sid: str) -> TimelineEvent | None:
        """Localiza o evento 'ligacao' já criado por record_call_status (evento_meta
        carrega call_sid) — usado pelo webhook da AssemblyAI pra gravar a transcrição
        no mesmo evento, sem precisar de mais uma FK dedicada."""
        return self.db.execute(
            self._base_query().where(
                TimelineEvent.evento_meta["call_sid"].astext == call_sid
            )
        ).scalar_one_or_none()
