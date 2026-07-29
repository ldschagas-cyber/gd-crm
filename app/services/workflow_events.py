"""Publicação de eventos de domínio para o motor de Workflows (RF018, §7.9).

Os services de domínio (Company/Contact/Deal) chamam `publish_event()` depois de uma mutação
bem-sucedida. O envio pro Celery só acontece depois que a transação atual for commitada — sem
isso, o worker (processo/conexão separada do Postgres) poderia tentar ler um registro que, do
ponto de vista dele, ainda não existe: a transação HTTP que disparou o evento só commita depois
que o service retorna (ver `get_db()` em app/core/database.py).
"""
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.context import get_current_tenant


def publish_event(db: Session, gatilho: str, entidade_ref: UUID, payload: dict) -> None:
    tenant_id = get_current_tenant()
    if tenant_id is None:
        return

    def _fire(_session):
        from app.workers.tasks import dispatch_workflow_event
        dispatch_workflow_event.delay(str(tenant_id), gatilho, str(entidade_ref), payload)

    event.listen(db, "after_commit", _fire, once=True)
