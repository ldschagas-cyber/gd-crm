"""add recording fields to calls

Revision ID: d2e4f6a8b0c1
Revises: a4c8e1f6d3b7
Create Date: 2026-08-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd2e4f6a8b0c1'
down_revision: Union[str, None] = 'a4c8e1f6d3b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('calls', sa.Column('recording_sid', sa.String(length=64), nullable=True))
    op.add_column('calls', sa.Column('assemblyai_transcript_id', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_calls_assemblyai_transcript_id'), 'calls', ['assemblyai_transcript_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_calls_assemblyai_transcript_id'), table_name='calls')
    op.drop_column('calls', 'assemblyai_transcript_id')
    op.drop_column('calls', 'recording_sid')
