"""add resultado_ligacao to tasks

Revision ID: c2f7a4e8b1d3
Revises: a8d4f1c6b3e9
Create Date: 2026-08-10 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2f7a4e8b1d3'
down_revision: Union[str, None] = 'a8d4f1c6b3e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Desfecho da ligação (atendeu/caixa postal/não atendeu/...), preenchido ao
    # concluir uma tarefa de ligação pela fila de execução (Tarefas → Iniciar
    # tarefas). Texto livre no banco (igual a tipo/prioridade/status) — validado
    # pelo enum ResultadoLigacao na camada de schema, não como enum nativo do Postgres.
    op.add_column('tasks', sa.Column('resultado_ligacao', sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'resultado_ligacao')
