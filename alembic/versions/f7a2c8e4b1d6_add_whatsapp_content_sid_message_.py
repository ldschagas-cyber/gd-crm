"""add whatsapp_content_sid to message_templates

Revision ID: f7a2c8e4b1d6
Revises: a1c4e8f2b6d9
Create Date: 2026-08-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7a2c8e4b1d6'
down_revision: Union[str, None] = 'a1c4e8f2b6d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Envio automático de WhatsApp em etapas de Sequência via Twilio (ver
    # app/services/twilio_whatsapp.py) — o SID do Content Template aprovado pela
    # Meta. Nullable e aditiva: templates existentes continuam gerando Tarefa
    # manual (comportamento de hoje) até alguém preencher esse campo.
    op.add_column('message_templates', sa.Column('whatsapp_content_sid', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('message_templates', 'whatsapp_content_sid')
