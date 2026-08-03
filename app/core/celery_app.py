"""Instância do Celery e configuração de filas."""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "crm",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_default_queue="default",
    task_routes={
        "app.workers.tasks.import_companies_task": {"queue": "default"},
        "app.workers.tasks.import_contacts_task": {"queue": "default"},
    },
    task_track_started=True,
    timezone="America/Sao_Paulo",
    # Sequências (RF010, §7.5): varredura diária de sequence_enrollments pendentes.
    # Requer o serviço `beat` (celery beat) rodando além do worker — ver docker-compose.yml.
    beat_schedule={
        "process-due-sequence-steps": {
            "task": "app.workers.tasks.process_due_sequence_steps",
            "schedule": crontab(hour=6, minute=0),
        },
    },
)
