"""FaturamentoService — geração recorrente idempotente + pedido de NF ao contador (RF-FAT).

Gera uma cobrança por contrato ATIVO por competência (RN-F01/RN-F02); reprocessar a mesma
competência não duplica (UniqueConstraint tenant+contrato+competência). No fim, dispara o
pedido de NF ao contador para as cobranças da competência (gatilho no faturamento — decisão
de 2026-08-21). O envio é desacoplado: falha de e-mail não impede a geração.
"""
import calendar
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.core.money import dec, money
from app.models.billing import Cobranca, CobrancaStatus, CobrancaTipo
from app.models.contract import ContratoStatus
from app.models.tenant import Tenant
from app.repositories.billing import CobrancaRepository
from app.repositories.contract import ContratoRepository
from app.schemas.billing import CobrancaPontualCreate, FaturamentoResult

DIA_VENCIMENTO_PADRAO = 5


class FaturamentoService:
    def __init__(self, db: Session):
        self.db = db
        self.cobrancas = CobrancaRepository(db)
        self.contratos = ContratoRepository(db)

    @staticmethod
    def competencia_atual() -> str:
        hoje = date.today()
        return f"{hoje.year:04d}-{hoje.month:02d}"

    def _dia_vencimento(self) -> int:
        tenant = self.db.get(Tenant, get_current_tenant())
        cfg = (tenant.config or {}).get("financeiro", {}) if tenant else {}
        return int(cfg.get("dia_vencimento", DIA_VENCIMENTO_PADRAO))

    def _vencimento(self, competencia: str) -> date:
        ano, mes = (int(x) for x in competencia.split("-"))
        dia = min(self._dia_vencimento(), calendar.monthrange(ano, mes)[1])
        return date(ano, mes, dia)

    def listar_competencia(self, competencia: str | None = None) -> tuple[str, list[Cobranca]]:
        competencia = competencia or self.competencia_atual()
        self.cobrancas.marcar_vencidas(date.today())
        return competencia, self.cobrancas.list_por_competencia(competencia)

    def gerar(self, competencia: str | None = None) -> FaturamentoResult:
        competencia = competencia or self.competencia_atual()
        ano, mes = (int(x) for x in competencia.split("-"))
        fim_competencia = date(ano, mes, calendar.monthrange(ano, mes)[1])
        vencimento = self._vencimento(competencia)

        geradas = 0
        ja_existentes = 0
        valor_total = dec(0)
        for contrato in self.contratos.list_ativos():
            if contrato.data_inicio > fim_competencia:
                continue  # contrato começa depois desta competência
            if contrato.vigencia_meses is not None:
                fim_vigencia = self._add_months(contrato.data_inicio, contrato.vigencia_meses)
                if fim_competencia > fim_vigencia:
                    continue  # vigência já encerrada nesta competência
            if self.cobrancas.get_por_contrato_competencia(contrato.id, competencia):
                ja_existentes += 1
                continue
            valor = money(contrato.valor_mensal)
            self.cobrancas.add(Cobranca(
                contrato_id=contrato.id, company_id=contrato.company_id, competencia=competencia,
                descricao=f"Contrato {contrato.numero} — {competencia}", tipo=CobrancaTipo.RECORRENTE.value,
                valor=valor, vencimento=vencimento, status=CobrancaStatus.ABERTA.value,
            ))
            geradas += 1
            valor_total += valor

        self.cobrancas.marcar_vencidas(date.today())
        # Gatilho de NF: pede ao contador as NFs das cobranças da competência sem NF.
        from app.services.contador import ContadorService
        resultado_nf = ContadorService(self.db).solicitar_nf(
            self.cobrancas.list_sem_nf_por_competencia(competencia), competencia
        )
        return FaturamentoResult(
            competencia=competencia, geradas=geradas, ja_existentes=ja_existentes,
            valor_total=float(money(valor_total)), nf_solicitadas=resultado_nf.solicitadas,
            nf_email_enviado=resultado_nf.enviado, nf_aviso=resultado_nf.aviso,
        )

    def criar_pontual(self, data: CobrancaPontualCreate) -> Cobranca:
        competencia = data.competencia or self.competencia_atual()
        cobranca = Cobranca(
            contrato_id=None, company_id=data.company_id, categoria_id=data.categoria_id,
            competencia=competencia, descricao=data.descricao, tipo=CobrancaTipo.PONTUAL.value,
            valor=money(data.valor), vencimento=data.vencimento, status=CobrancaStatus.ABERTA.value,
        )
        return self.cobrancas.add(cobranca)

    def reenviar_nf(self, competencia: str) -> FaturamentoResult:
        """Reenvia o pedido de NF das cobranças pendentes da competência (botão manual)."""
        from app.services.contador import ContadorService
        resultado = ContadorService(self.db).solicitar_nf(
            self.cobrancas.list_sem_nf_por_competencia(competencia), competencia
        )
        return FaturamentoResult(
            competencia=competencia, geradas=0, ja_existentes=0, valor_total=0.0,
            nf_solicitadas=resultado.solicitadas, nf_email_enviado=resultado.enviado,
            nf_aviso=resultado.aviso,
        )

    @staticmethod
    def _add_months(d: date, months: int) -> date:
        total = d.month - 1 + months
        ano = d.year + total // 12
        mes = total % 12 + 1
        dia = min(d.day, calendar.monthrange(ano, mes)[1])
        return date(ano, mes, dia)
