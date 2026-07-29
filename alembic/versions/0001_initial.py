"""Migração inicial — cria todas as tabelas do MVP e habilita RLS.

A criação das tabelas deriva diretamente do metadata dos modelos
(fonte única de verdade), evitando divergência entre schema e ORM.
As políticas RLS adicionam defesa em profundidade ao isolamento por tenant.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-18
"""
from typing import Sequence, Union

from alembic import op

from app.models import Base

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tabelas de negócio que recebem políticas RLS por tenant.
TENANT_TABLES = [
    "users", "companies", "contacts", "pipelines", "pipeline_stages",
    "deals", "tasks", "timeline_events", "import_jobs", "audit_logs",
]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    # Índices compostos adicionais (tenant-first) para consultas frequentes.
    op.create_index("ix_companies_tenant_status", "companies", ["tenant_id", "status"])
    op.create_index("ix_deals_tenant_stage", "deals", ["tenant_id", "stage_id"])
    op.create_index("ix_deals_tenant_resp", "deals", ["tenant_id", "responsavel_id"])
    op.create_index("ix_tasks_tenant_resp_status", "tasks", ["tenant_id", "responsavel_id", "status"])
    op.create_index("ix_timeline_tenant_company", "timeline_events", ["tenant_id", "company_id", "created_at"])

    # Row-Level Security: restringe linhas ao tenant da sessão (app.current_tenant).
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = current_setting('app.current_tenant', true)::uuid)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    Base.metadata.drop_all(bind=bind)
