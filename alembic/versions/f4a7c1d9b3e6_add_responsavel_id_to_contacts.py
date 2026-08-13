"""add responsavel_id to contacts

Revision ID: f4a7c1d9b3e6
Revises: 5261237b4c9f
Create Date: 2026-08-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4a7c1d9b3e6'
down_revision: Union[str, None] = '5261237b4c9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Contato nunca tem dono independente da empresa (ver app/models/contact.py) —
    # nullable porque uma empresa pode não ter responsavel_id preenchido.
    op.add_column('contacts', sa.Column('responsavel_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_contacts_responsavel_id_users', 'contacts', 'users',
        ['responsavel_id'], ['id'],
    )
    op.create_index(op.f('ix_contacts_responsavel_id'), 'contacts', ['responsavel_id'], unique=False)

    # Backfill: todo contato existente herda o responsável da própria empresa, mantendo a
    # invariante "contact.responsavel_id == company.responsavel_id" desde o dia 1 — daqui
    # pra frente, CompanyService.update propaga qualquer mudança de responsável da
    # empresa pros contatos (ver ContactRepository.update_responsavel_for_company).
    op.execute(
        """
        UPDATE contacts
        SET responsavel_id = companies.responsavel_id
        FROM companies
        WHERE contacts.company_id = companies.id
          AND companies.responsavel_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_contacts_responsavel_id'), table_name='contacts')
    op.drop_constraint('fk_contacts_responsavel_id_users', 'contacts', type_='foreignkey')
    op.drop_column('contacts', 'responsavel_id')
