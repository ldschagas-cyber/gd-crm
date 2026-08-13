"""Assinatura e AssinaturaEvento — receita recorrente (MRR/ARR).

Ver docs/PLANO_RECEITA_RECORRENTE.md. `Assinatura` guarda o estado atual (valor, status);
`AssinaturaEvento` é o livro-razão imutável de toda mudança de valor/status — é dele que
`RevenueService` deriva Novo MRR, Expansão, Contração, Churn e NRR por período, sem depender
de comparar snapshots entre meses (ver §2 do plano). Nenhum caminho de código deve alterar
`Assinatura.valor_mensal`/`status` sem gravar o evento correspondente — a garantia é de
`AssinaturaService`, não do banco.
"""
import enum
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class AssinaturaStatus(str, enum.Enum):
    ATIVA = "ativa"
    PAUSADA = "pausada"       # inadimplência/negociação — não conta como MRR ativo
    CANCELADA = "cancelada"


class CicloCobranca(str, enum.Enum):
    MENSAL = "mensal"
    ANUAL = "anual"            # valor_mensal já vem normalizado (valor_anual / 12)


class TipoEventoAssinatura(str, enum.Enum):
    NOVA = "nova"
    EXPANSAO = "expansao"      # upgrade de valor
    CONTRACAO = "contracao"    # downgrade de valor, sem cancelar
    CANCELAMENTO = "cancelamento"
    REATIVACAO = "reativacao"  # cliente cancelado que voltou


class Assinatura(Base, TenantMixin, TimestampMixin):
    __tablename__ = "assinaturas"

    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    # Rastreabilidade opcional até o negócio que originou a assinatura — não usado pra
    # nenhum cálculo, só contexto (ver §3 do plano: sem automação Deal->Assinatura na v1).
    deal_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("deals.id"))
    # Texto livre — sem catálogo formal de planos na v1 (§0.3 do plano): cada contrato é
    # negociado individualmente hoje.
    nome_plano: Mapped[str] = mapped_column(String(120), nullable=False)
    valor_mensal: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    ciclo_cobranca: Mapped[str] = mapped_column(String(10), nullable=False, default=CicloCobranca.MENSAL.value)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AssinaturaStatus.ATIVA.value, index=True)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_cancelamento: Mapped[date | None] = mapped_column(Date)
    motivo_cancelamento: Mapped[str | None] = mapped_column(String(255))
    responsavel_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class AssinaturaEvento(Base, TenantMixin, TimestampMixin):
    __tablename__ = "assinatura_eventos"

    id: Mapped[uuid.UUID] = uuid_pk()
    assinatura_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assinaturas.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    valor_anterior: Mapped[float | None] = mapped_column(Numeric(15, 2))
    valor_novo: Mapped[float | None] = mapped_column(Numeric(15, 2))
    # valor_novo - valor_anterior — negativo em contração/cancelamento. É a coluna que
    # RevenueService soma por tipo/período; nunca recalculada a partir de valor_anterior/novo
    # na leitura, pra sobreviver mesmo se um dos dois vier nulo (ex.: cancelamento).
    delta_mrr: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    # Data de competência (quando o reajuste vale), distinta de created_at (quando foi
    # lançado no sistema) — permite lançamento retroativo sem distorcer o mês de referência.
    data_evento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_por: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
