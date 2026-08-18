"""AssinaturaService — CRUD de assinaturas com o livro-razão de MRR sempre em dia.

Toda mudança de valor_mensal ou status passa por aqui e grava um AssinaturaEvento
correspondente — é essa garantia que faz o RevenueService (app/services/revenue.py) poder
derivar os indicadores só somando a coluna delta_mrr por tipo/período, sem tocar direto em
Assinatura. Ver docs/PLANO_RECEITA_RECORRENTE.md §1 e §3.
"""
from calendar import monthrange
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import get_current_user_id
from app.core.exceptions import ConflictError, NotFoundError
from app.models.subscription import (
    Assinatura, AssinaturaEvento, AssinaturaStatus, CicloCobranca, TipoEventoAssinatura,
)
from app.repositories.company import CompanyRepository
from app.repositories.subscription import AssinaturaEventoRepository, AssinaturaRepository
from app.schemas.subscription import (
    AssinaturaCancelar, AssinaturaCreate, AssinaturaReativar, AssinaturaRenovar, AssinaturaValorUpdate,
)


# Deal.valor_previsto é o valor TOTAL da oportunidade (forecast/pipeline somam como "valor
# total" e ponderam por probabilidade — ver app/services/forecast.py), não um valor mensal.
# Para virar MRR ao ganhar o negócio, tratamos esse total como valor ANUAL de contrato e
# normalizamos dividindo por 12 — a mesma convenção que CicloCobranca.ANUAL já documenta
# ("valor_mensal já vem normalizado = valor_anual / 12"). Ponto único de ajuste caso o
# processo comercial passe a lançar valor_previsto com outra recorrência.
MESES_CONTRATO_PADRAO = 12


def _add_months(d: date, months: int) -> date:
    """Sem dependência nova (python-dateutil) só por isso — soma meses lidando com
    estouro de dia (ex.: 31/jan + 1 mês -> 28 ou 29/fev, nunca 03/mar)."""
    total = d.month - 1 + months
    ano = d.year + total // 12
    mes = total % 12 + 1
    dia = min(d.day, monthrange(ano, mes)[1])
    return date(ano, mes, dia)


class AssinaturaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AssinaturaRepository(db)
        self.eventos = AssinaturaEventoRepository(db)
        self.companies = CompanyRepository(db)

    # ---- Leitura ----------------------------------------------------------
    # `list` por último de propósito: dentro do corpo da classe, uma vez que o método
    # `list` é definido ele passa a *sombrear* o builtin `list` no namespace da classe —
    # qualquer anotação `list[...]` num método declarado DEPOIS dele quebra em Python <3.14
    # (que ainda avalia anotações eagerly) com `TypeError: 'function' object is not
    # subscriptable`. Mantém o nome `list` (mesmo padrão de DealService/CompanyService) só
    # cuidando da ordem, em vez de renomear.
    def get(self, assinatura_id: UUID) -> Assinatura:
        item = self.repo.get(assinatura_id)
        if item is None:
            raise NotFoundError("Assinatura não encontrada")
        return item

    def list_by_company(self, company_id: UUID) -> list[Assinatura]:
        return self.list(company_id=company_id)

    def list_eventos(self, assinatura_id: UUID) -> list[AssinaturaEvento]:
        self.get(assinatura_id)  # valida existência/tenant
        return self.eventos.list_by_assinatura(assinatura_id)

    def list(self, status: str | None = None, responsavel_id: UUID | None = None,
             company_id: UUID | None = None) -> list[Assinatura]:
        filters = []
        if status:
            filters.append(Assinatura.status == status)
        if responsavel_id:
            filters.append(Assinatura.responsavel_id == responsavel_id)
        if company_id:
            filters.append(Assinatura.company_id == company_id)
        items, _ = self.repo.list(*filters, limit=1000, order_by=Assinatura.created_at.desc())
        return items

    # ---- Escrita — cada método garante o evento correspondente -----------
    def create(self, data: AssinaturaCreate) -> Assinatura:
        company = self.companies.get(data.company_id)
        if company is None:
            raise NotFoundError("Empresa não encontrada")
        # Uma assinatura ativa por empresa na v1 (§0.5 do plano) — upsell/downgrade editam
        # a assinatura existente em vez de abrir uma segunda linha.
        if self.repo.get_ativa_por_empresa(data.company_id) is not None:
            raise ConflictError("Esta empresa já tem uma assinatura ativa")

        assinatura = Assinatura(
            company_id=data.company_id, deal_id=data.deal_id, nome_plano=data.nome_plano,
            valor_mensal=data.valor_mensal, ciclo_cobranca=data.ciclo_cobranca,
            status=AssinaturaStatus.ATIVA.value, data_inicio=data.data_inicio,
            responsavel_id=data.responsavel_id, ciclo_renovacao_meses=data.ciclo_renovacao_meses,
            # Customer Success (ver docs/PLANO_CUSTOMER_SUCCESS.md) — primeira renovação
            # calculada a partir do início do contrato; None se não há prazo fixo.
            data_renovacao=(
                _add_months(data.data_inicio, data.ciclo_renovacao_meses)
                if data.ciclo_renovacao_meses else None
            ),
        )
        assinatura = self.repo.add(assinatura)
        self._registrar_evento(
            assinatura, TipoEventoAssinatura.NOVA.value, valor_anterior=None,
            valor_novo=assinatura.valor_mensal, delta=assinatura.valor_mensal,
            data_evento=data.data_inicio, observacao=None,
        )
        return assinatura

    def registrar_negocio_ganho(self, deal) -> "Assinatura | None":
        """Ponte automática Negócio ganho -> Receita Recorrente. Chamado por
        DealService quando um negócio entra em GANHO (uma única vez por negócio — a
        idempotência é garantida por DealService._on_deal_closed, que só dispara na
        transição para ganho, não a cada re-save de um negócio já fechado).

        `valor_previsto` do negócio é o valor total do contrato, convertido em MRR pela
        regra de MESES_CONTRATO_PADRAO (ver constante acima). Sem assinatura ativa -> cria
        a primeira; já havendo uma (segundo negócio ganho do mesmo cliente) -> soma o MRR
        como evento de expansão, mantendo a regra de "uma assinatura ativa por empresa"
        (§0.5 do plano) em vez de abrir uma segunda linha bloqueada. Ver
        docs/PLANO_RECEITA_RECORRENTE.md."""
        if deal.valor_previsto is None:
            return None
        valor_contrato = float(deal.valor_previsto)
        if valor_contrato <= 0:
            return None
        mrr = round(valor_contrato / MESES_CONTRATO_PADRAO, 2)
        if mrr <= 0:
            return None

        ativa = self.repo.get_ativa_por_empresa(deal.company_id)
        if ativa is None:
            return self.create(AssinaturaCreate(
                company_id=deal.company_id, deal_id=deal.id, nome_plano=deal.nome[:120],
                valor_mensal=mrr, ciclo_cobranca=CicloCobranca.ANUAL.value,
                ciclo_renovacao_meses=MESES_CONTRATO_PADRAO, responsavel_id=deal.responsavel_id,
                data_inicio=deal.data_fechamento.date() if deal.data_fechamento else date.today(),
            ))
        # Cliente já tem assinatura ativa -> negócio ganho é expansão do MRR existente.
        return self.atualizar_valor(ativa.id, AssinaturaValorUpdate(
            valor_mensal=round(float(ativa.valor_mensal) + mrr, 2),
            observacao=f"Expansão automática — negócio ganho: {deal.nome}"[:255],
        ))

    def atualizar_valor(self, assinatura_id: UUID, data: AssinaturaValorUpdate) -> Assinatura:
        assinatura = self.get(assinatura_id)
        if assinatura.status != AssinaturaStatus.ATIVA.value:
            raise ConflictError("Só é possível reajustar uma assinatura ativa")
        valor_anterior = float(assinatura.valor_mensal)
        if data.valor_mensal == valor_anterior:
            raise ConflictError("Informe um valor diferente do atual")

        delta = data.valor_mensal - valor_anterior
        tipo = TipoEventoAssinatura.EXPANSAO.value if delta > 0 else TipoEventoAssinatura.CONTRACAO.value
        assinatura.valor_mensal = data.valor_mensal
        assinatura = self.repo.save(assinatura)
        self._registrar_evento(
            assinatura, tipo, valor_anterior=valor_anterior, valor_novo=data.valor_mensal, delta=delta,
            data_evento=data.data_evento or date.today(), observacao=data.observacao,
        )
        return assinatura

    def cancelar(self, assinatura_id: UUID, data: AssinaturaCancelar) -> Assinatura:
        assinatura = self.get(assinatura_id)
        if assinatura.status == AssinaturaStatus.CANCELADA.value:
            raise ConflictError("Assinatura já está cancelada")
        valor_atual = float(assinatura.valor_mensal)
        data_cancelamento = data.data_cancelamento or date.today()

        assinatura.status = AssinaturaStatus.CANCELADA.value
        assinatura.data_cancelamento = data_cancelamento
        assinatura.motivo_cancelamento = data.motivo_cancelamento
        assinatura = self.repo.save(assinatura)
        self._registrar_evento(
            assinatura, TipoEventoAssinatura.CANCELAMENTO.value, valor_anterior=valor_atual,
            valor_novo=0, delta=-valor_atual, data_evento=data_cancelamento,
            observacao=data.motivo_cancelamento,
        )
        # Customer Success (ver docs/PLANO_CUSTOMER_SUCCESS.md §4) — único caminho até a
        # fase "churn": cancelar a assinatura É o cancelamento do cliente, não uma ação
        # separada. Import tardio: evita ciclo com CompanyService.
        from app.services.company import CompanyService
        CompanyService(self.db).advance_cs_on_assinatura_cancelada(assinatura.company_id)
        return assinatura

    def renovar(self, assinatura_id: UUID, data: AssinaturaRenovar) -> Assinatura:
        """Confirma a renovação do ciclo atual — empurra `data_renovacao` pra frente em
        `ciclo_renovacao_meses`. Só se aplica a assinatura com prazo fixo (Customer
        Success, ver docs/PLANO_CUSTOMER_SUCCESS.md); sem `ciclo_renovacao_meses` não
        há "renovação" a confirmar (contrato mês a mês, já sempre "em dia")."""
        assinatura = self.get(assinatura_id)
        if assinatura.status != AssinaturaStatus.ATIVA.value:
            raise ConflictError("Só é possível renovar uma assinatura ativa")
        if not assinatura.ciclo_renovacao_meses:
            raise ConflictError("Esta assinatura não tem prazo fixo — nada para renovar")

        base = assinatura.data_renovacao or date.today()
        assinatura.data_renovacao = _add_months(base, assinatura.ciclo_renovacao_meses)

        if data.novo_valor_mensal is not None and data.novo_valor_mensal != float(assinatura.valor_mensal):
            valor_anterior = float(assinatura.valor_mensal)
            delta = data.novo_valor_mensal - valor_anterior
            tipo = TipoEventoAssinatura.EXPANSAO.value if delta > 0 else TipoEventoAssinatura.CONTRACAO.value
            assinatura.valor_mensal = data.novo_valor_mensal
            assinatura = self.repo.save(assinatura)
            self._registrar_evento(
                assinatura, tipo, valor_anterior=valor_anterior, valor_novo=data.novo_valor_mensal, delta=delta,
                data_evento=date.today(), observacao=data.observacao or "Reajuste na renovação",
            )
        else:
            assinatura = self.repo.save(assinatura)
        return assinatura

    def reativar(self, assinatura_id: UUID, data: AssinaturaReativar) -> Assinatura:
        assinatura = self.get(assinatura_id)
        if assinatura.status != AssinaturaStatus.CANCELADA.value:
            raise ConflictError("Só é possível reativar uma assinatura cancelada")
        if self.repo.get_ativa_por_empresa(assinatura.company_id) is not None:
            raise ConflictError("Esta empresa já tem uma assinatura ativa")

        valor_atual = float(assinatura.valor_mensal)
        assinatura.status = AssinaturaStatus.ATIVA.value
        assinatura.data_cancelamento = None
        assinatura.motivo_cancelamento = None
        assinatura = self.repo.save(assinatura)
        self._registrar_evento(
            assinatura, TipoEventoAssinatura.REATIVACAO.value, valor_anterior=0,
            valor_novo=valor_atual, delta=valor_atual,
            data_evento=data.data_evento or date.today(), observacao=data.observacao,
        )
        return assinatura

    # ---- interno ------------------------------------------------------------
    def _registrar_evento(self, assinatura: Assinatura, tipo: str, *, valor_anterior: float | None,
                          valor_novo: float | None, delta: float, data_evento: date,
                          observacao: str | None) -> AssinaturaEvento:
        evento = AssinaturaEvento(
            assinatura_id=assinatura.id, tipo=tipo, valor_anterior=valor_anterior,
            valor_novo=valor_novo, delta_mrr=delta, data_evento=data_evento,
            observacao=observacao, criado_por=get_current_user_id(),
        )
        return self.eventos.add(evento)
