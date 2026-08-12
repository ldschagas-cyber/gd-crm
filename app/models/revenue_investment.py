"""RevenueInvestment — lançamento manual de investimento comercial, alimenta CAC/ROI.

Ver docs/PLANO_PREVISAO_COMERCIAL.md §8. Nenhum outro módulo do CRM grava custo/investimento
hoje — este é o único dado que faltava pra calcular CAC (custo por cliente) e ROI comercial.
Contagem de clientes fechados e receita realizada continuam vindas de FunilMetasService, não
duplicadas aqui (mesmo padrão de reaproveitamento já usado pela ponte com Previsão Comercial).
"""
import enum
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class InvestmentCategory(str, enum.Enum):
    MARKETING = "marketing"
    VENDAS = "vendas"
    FERRAMENTAS = "ferramentas"
    OUTROS = "outros"


class RevenueInvestment(Base, TenantMixin, TimestampMixin):
    __tablename__ = "revenue_investments"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Sempre dia 1 do mês — um lançamento representa o investimento daquele mês inteiro,
    # não uma data pontual. Normalizado em RevenueInvestmentService.create/update a partir
    # de um campo `mes` (AAAA-MM), mesmo formato usado por ForecastService/FunilMetasService.
    competencia: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    categoria: Mapped[str] = mapped_column(String(20), nullable=False, default=InvestmentCategory.OUTROS.value)
    valor: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    observacao: Mapped[str | None] = mapped_column(String(255))
    criado_por: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
