"""CnaeCode — tabela de referência estática da hierarquia CNAE 2.3 (IBGE/Concla).

Dado de classificação global, não pertence a nenhum tenant — por isso não usa
`TenantMixin` (diferente de todo outro model do domínio de negócio). Seed via
`app/seed_cnae.py` a partir de `app/data/cnae_hierarquia.csv`.
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CnaeCode(Base):
    __tablename__ = "cnae_codes"

    codigo: Mapped[str] = mapped_column(String(7), primary_key=True)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    secao: Mapped[str] = mapped_column(String(1), nullable=False, index=True)
    divisao: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    grupo: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    classe: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
