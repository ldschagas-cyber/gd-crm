"""Team — equipe de vendas. Hierarquia gestor → equipe → vendedores; um tenant tem
várias equipes. O vendedor é ligado pela coluna `users.team_id` (ver User); a meta
da equipe não é armazenada aqui — é sempre a soma das metas dos seus vendedores no
mês (ver MetasVendaService). Ver docs/PLANO_METAS_VENDA.md."""
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class Team(Base, TenantMixin, TimestampMixin):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    # Gestor responsável pela equipe (opcional). FK para users; nullable porque uma
    # equipe pode ser criada antes de ter um gestor definido.
    gestor_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
