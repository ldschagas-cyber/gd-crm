"""FinanceiroDashboardService — Visão Geral do módulo Financeiro (RF-DSH).

MRR vem do RevenueService (fonte única — decisão de PO: um só número de MRR no sistema).
Os demais indicadores vêm das cobranças e propostas do módulo. O card "A pagar no mês"
fica de fora até o Contas a Pagar existir.
"""
from calendar import monthrange
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.billing import CobrancaStatus
from app.models.contract import Contrato
from app.repositories.billing import CobrancaRepository
from app.repositories.contract import ContratoRepository
from app.repositories.proposal import PropostaRepository
from app.repositories.user import UserRepository
from app.schemas.finance_dashboard import (
    FinanceiroResumo, MargemVendedorRead, PendenciaRead,
)
from app.services.revenue import RevenueService


class FinanceiroDashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.cobrancas = CobrancaRepository(db)
        self.contratos = ContratoRepository(db)
        self.propostas = PropostaRepository(db)
        self.users = UserRepository(db)

    def resumo(self) -> FinanceiroResumo:
        hoje = date.today()
        self.cobrancas.marcar_vencidas(hoje)
        primeiro = date(hoje.year, hoje.month, 1)
        ultimo = date(hoje.year, hoje.month, monthrange(hoje.year, hoje.month)[1])
        trimestre_inicio = hoje - timedelta(days=90)

        mrr = RevenueService(self.db).resumo().mrr  # fonte única de MRR
        ativos = self.contratos.list_ativos()
        a_receber = self.cobrancas.soma_por_status(
            CobrancaStatus.ABERTA.value, venc_inicio=primeiro, venc_fim=ultimo
        )
        vencidos = self.cobrancas.soma_por_status(CobrancaStatus.VENCIDA.value)
        vencidos_qtd = self.cobrancas.count_por_status(CobrancaStatus.VENCIDA.value)
        margem = float(self.propostas.desconto_medio(trimestre_inicio, hoje))

        return FinanceiroResumo(
            mrr=mrr, contratos_ativos=len(ativos), a_receber_mes=round(a_receber, 2),
            vencidos=round(vencidos, 2), vencidos_qtd=vencidos_qtd,
            margem_cedida_pct=round(margem, 3),
            pendencias=self._pendencias(ativos, hoje),
            margem_por_vendedor=self._margem_por_vendedor(trimestre_inicio, hoje),
        )

    def _pendencias(self, contratos_ativos: list[Contrato], hoje: date) -> list[PendenciaRead]:
        pend: list[PendenciaRead] = []
        for c in self.cobrancas.list_por_status(CobrancaStatus.VENCIDA.value, limit=10):
            dias = (hoje - c.vencimento).days
            pend.append(PendenciaRead(
                tipo="vencida", titulo=f"Cobrança {c.competencia} vencida há {dias} dia(s)",
                valor=float(c.valor), referencia_id=c.id,
            ))
        for c in contratos_ativos:
            if c.vigencia_meses is None:
                continue
            fim = self._add_months(c.data_inicio, c.vigencia_meses)
            dias = (fim - hoje).days
            if 0 <= dias <= 60:
                pend.append(PendenciaRead(
                    tipo="vigencia", titulo=f"Contrato {c.numero} vence em {dias} dia(s)",
                    valor=float(c.valor_mensal), referencia_id=c.id,
                ))
        return pend

    def _margem_por_vendedor(self, inicio: date, fim: date) -> list[MargemVendedorRead]:
        linhas = []
        for vendedor_id, qtd, media, maximo in self.propostas.margem_por_vendedor(inicio, fim):
            nome = "Sem vendedor"
            if vendedor_id is not None:
                user = self.users.get(vendedor_id)
                nome = user.nome if user else str(vendedor_id)
            linhas.append(MargemVendedorRead(
                vendedor_id=vendedor_id, vendedor_nome=nome, propostas=int(qtd),
                desconto_medio_pct=round(float(media), 3), desconto_max_pct=round(float(maximo), 3),
            ))
        return linhas

    @staticmethod
    def _add_months(d: date, months: int) -> date:
        total = d.month - 1 + months
        ano = d.year + total // 12
        mes = total % 12 + 1
        dia = min(d.day, monthrange(ano, mes)[1])
        return date(ano, mes, dia)
