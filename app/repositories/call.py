"""Repositório de chamadas (Twilio)."""
from sqlalchemy import select

from app.models.call import Call
from app.repositories.base import BaseRepository


class CallRepository(BaseRepository[Call]):
    model = Call

    def get_by_sid(self, call_sid: str) -> Call | None:
        return self.db.execute(
            self._base_query().where(Call.call_sid == call_sid)
        ).scalar_one_or_none()

    def get_by_sid_any_tenant(self, call_sid: str) -> Call | None:
        """Sem filtro de tenant — usado no status callback, que já resolveu o
        tenant a partir da própria Call criada no TwiML anterior (voice/inbound-voice),
        então a busca por tenant seria redundante e exigiria repetir a resolução."""
        return self.db.execute(
            select(Call).where(Call.call_sid == call_sid)
        ).scalar_one_or_none()

    def get_by_assemblyai_transcript_id_any_tenant(self, transcript_id: str) -> Call | None:
        """Sem filtro de tenant — usado no webhook de transcrição da AssemblyAI, que só
        recebe o transcript_id (nenhum tenant/JWT no contexto ainda)."""
        return self.db.execute(
            select(Call).where(Call.assemblyai_transcript_id == transcript_id)
        ).scalar_one_or_none()
