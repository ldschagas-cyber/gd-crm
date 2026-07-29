"""remap lead_prospects status values

Revision ID: 6da712e0d874
Revises: fcf64430cfe5
Create Date: 2026-07-28 20:36:37.335481
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6da712e0d874'
down_revision: Union[str, None] = 'fcf64430cfe5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_UPGRADE_MAP = {
    "pesquisando": "novo",
    "enriquecido": "enriquecer",
    "pronto_para_cadencia": "qualificado",
}
_DOWNGRADE_MAP = {v: k for k, v in _UPGRADE_MAP.items()}


def upgrade() -> None:
    for old, new in _UPGRADE_MAP.items():
        op.execute(
            sa.text("UPDATE lead_prospects SET status = :new WHERE status = :old")
            .bindparams(new=new, old=old)
        )


def downgrade() -> None:
    for new, old in _DOWNGRADE_MAP.items():
        op.execute(
            sa.text("UPDATE lead_prospects SET status = :old WHERE status = :new")
            .bindparams(old=old, new=new)
        )
