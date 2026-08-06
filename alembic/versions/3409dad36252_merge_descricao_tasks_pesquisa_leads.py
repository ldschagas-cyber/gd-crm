"""merge heads: descricao em tasks + pesquisa de leads melhorias

Revision ID: 3409dad36252
Revises: a3f6c1d9e2b7, b8f2d4a6c9e1
Create Date: 2026-08-06 00:00:00.000000

Une as duas pontas que ficaram divergindo de fb11856ce211 (ver nota em
b8f2d4a6c9e1_pesquisa_leads_melhorias.py). Nenhuma DDL aqui — é só o
ponto de junção do grafo de revisões.
"""
from typing import Sequence, Union


revision: str = '3409dad36252'
down_revision: Union[str, Sequence[str], None] = ('a3f6c1d9e2b7', 'b8f2d4a6c9e1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
