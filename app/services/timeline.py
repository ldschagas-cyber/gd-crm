"""Serviço de timeline: registra eventos de interação por empresa."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import get_current_user_id
from app.models.timeline import TimelineEvent, TimelineType
from app.repositories.timeline import TimelineRepository
from app.schemas.timeline import TimelineNoteCreate
from app.services.graph_client import GraphClient


class TimelineService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TimelineRepository(db)

    def registrar(
        self,
        company_id: UUID,
        tipo: str,
        titulo: str,
        descricao: str | None = None,
        deal_id: UUID | None = None,
        contact_id: UUID | None = None,
        meta: dict | None = None,
    ) -> TimelineEvent:
        evento = TimelineEvent(
            company_id=company_id,
            deal_id=deal_id,
            contact_id=contact_id,
            tipo=tipo,
            titulo=titulo,
            descricao=descricao,
            evento_meta=meta,
            user_id=get_current_user_id(),
        )
        evento = self.repo.add(evento)

        from app.services.company_ai import schedule_if_relevant
        schedule_if_relevant(self.db, evento)

        return evento

    def registrar_from_schema(
        self, company_id: UUID, data: TimelineNoteCreate, deal_id: UUID | None = None,
    ) -> TimelineEvent:
        """Além de gravar a nota, despacha e-mail de verdade (Mail.Send) ou cria o
        evento de verdade na agenda (com Teams opcional) quando os campos extras
        da conexão Microsoft 365 vierem preenchidos — ver TimelineNoteCreate."""
        deal_id = deal_id or data.deal_id
        meta: dict | None = None
        user_id = get_current_user_id()

        if data.tipo == TimelineType.EMAIL and data.destinatario:
            GraphClient(self.db).send_mail(user_id, data.destinatario, data.titulo, data.descricao or "")
            meta = {"enviado": True, "destinatario": data.destinatario}
        elif data.tipo == TimelineType.REUNIAO and data.inicio and data.fim:
            evento_ms = GraphClient(self.db).create_meeting(
                user_id, data.titulo, data.inicio.isoformat(), data.fim.isoformat(), data.criar_teams,
            )
            meta = {
                "inicio": data.inicio.isoformat(),
                "fim": data.fim.isoformat(),
                "evento_ms_id": evento_ms.get("id"),
                "teams_join_url": (evento_ms.get("onlineMeeting") or {}).get("joinUrl"),
            }

        return self.registrar(
            company_id, data.tipo.value, data.titulo, data.descricao,
            deal_id=deal_id, contact_id=data.contact_id, meta=meta,
        )
