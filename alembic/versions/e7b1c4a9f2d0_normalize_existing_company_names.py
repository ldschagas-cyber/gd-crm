"""normalize existing company names (lead_prospects + companies)

Backfill de exibição: converte nomes já gravados para Title Case usando
app.core.text.normalize_company_name (mesma regra da tela Buscar Empresas).

  - lead_prospects.empresa   -> normaliza TODAS as linhas (vêm da API pública
                                em CAIXA ALTA ou de cadastro manual).
  - companies.razao_social   -> normaliza SÓ as linhas 100% em CAIXA ALTA, para
                                não estragar grafia própria digitada/importada
                                (iFood, GD Conecta, siglas como CVC/TIM).

O usuário do banco em produção (POSTGRES_USER=crm) é superusuário e ignora RLS,
então o UPDATE abrange todos os tenants — mesmo padrão do backfill
f4a7c1d9b3e6, que também tocou `companies` sem setar tenant.

Revision ID: e7b1c4a9f2d0
Revises: 87bae0b12c44
Create Date: 2026-08-19 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.text import normalize_company_name


revision: str = 'e7b1c4a9f2d0'
down_revision: Union[str, None] = '87bae0b12c44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_all_caps(s: str) -> bool:
    """True se `s` tem ao menos uma letra e está inteiro em maiúsculas."""
    return any(c.isalpha() for c in s) and s == s.upper()


def _normalize_column(conn, tabela: str, coluna: str, so_caixa_alta: bool) -> None:
    rows = conn.execute(
        sa.text(f"SELECT id, {coluna} FROM {tabela} WHERE {coluna} IS NOT NULL AND {coluna} <> ''")
    ).fetchall()
    update = sa.text(f"UPDATE {tabela} SET {coluna} = :novo WHERE id = :id")
    for id_, valor in rows:
        if so_caixa_alta and not _is_all_caps(valor):
            continue
        novo = normalize_company_name(valor)
        if novo and novo != valor:
            conn.execute(update.bindparams(novo=novo, id=id_))


def upgrade() -> None:
    conn = op.get_bind()
    _normalize_column(conn, "lead_prospects", "empresa", so_caixa_alta=False)
    _normalize_column(conn, "companies", "razao_social", so_caixa_alta=True)


def downgrade() -> None:
    # Normalização é lossy: não guardamos a capitalização original, então não há
    # como reverter linha a linha. Downgrade é intencionalmente no-op.
    pass
