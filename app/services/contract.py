"""ContratoService — criação a partir do aceite e ativação com reconciliação de MRR.

Ponte PA-01 (decisão de 2026-08-21): NÃO substitui o gatilho existente Negócio ganho ->
Assinatura; RECONCILIA. Ao ativar o contrato, ajusta a assinatura do cliente do valor
ESTIMADO (AssinaturaService.mrr_do_negocio — o mesmo cálculo que
AssinaturaService.registrar_negocio_ganho usou pra lançar a assinatura) para o valor
REAL do contrato, via AssinaturaService (sempre com evento — nunca UPDATE direto, para
o razão de MRR do RevenueService continuar batendo). Ver
[[financeiro-ponte-contrato-assinatura-reconciliacao]].
"""
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import get_current_tenant
from app.core.exceptions import ConflictError, NotFoundError
from app.core.money import dec, money
from app.models.contract import Contrato, ContratoItem, ContratoStatus
from app.models.product import ProdutoTipo
from app.repositories.contract import ContratoRepository
from app.repositories.deal import DealRepository
from app.repositories.product import ProdutoRepository
from app.schemas.contract import ContratoAtivar


class ContratoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ContratoRepository(db)
        self.produtos = ProdutoRepository(db)
        self.deals = DealRepository(db)

    def get(self, contrato_id: UUID) -> Contrato:
        contrato = self.repo.get(contrato_id)
        if contrato is None:
            raise NotFoundError("Contrato não encontrado")
        return contrato

    def list(self, status: str | None = None) -> list[Contrato]:
        filters = []
        if status:
            filters.append(Contrato.status == status)
        items, _ = self.repo.list(*filters, limit=1000, order_by=Contrato.created_at.desc())
        return items

    def criar_de_proposta(self, proposta) -> Contrato:
        """Cria o contrato em rascunho herdando itens/preços da proposta aceita
        (RF-CONTR-06). valor_mensal = soma dos itens de produto RECORRENTE."""
        valor_mensal = dec(0)
        contrato = Contrato(
            numero=self.repo.proximo_numero(date.today().year),
            proposta_id=proposta.id, company_id=proposta.company_id,
            vendedor_id=proposta.vendedor_id, status=ContratoStatus.RASCUNHO.value,
            data_inicio=date.today(), valor_mensal=dec(0),
        )
        for item in proposta.itens:
            produto = self.produtos.get(item.produto_id)
            preco = dec(item.preco_proposto)
            contrato.itens.append(ContratoItem(
                tenant_id=get_current_tenant(),  # filho via cascade não passa pelo repo.add
                produto_id=item.produto_id, descricao=item.descricao,
                preco=money(preco), quantidade=item.quantidade,
            ))
            if produto and produto.tipo == ProdutoTipo.RECORRENTE.value:
                valor_mensal += preco * item.quantidade
        contrato.valor_mensal = money(valor_mensal)
        return self.repo.add(contrato)

    def ativar(self, contrato_id: UUID, data: ContratoAtivar | None = None) -> Contrato:
        contrato = self.get(contrato_id)
        if contrato.status == ContratoStatus.ATIVO.value:
            raise ConflictError("Contrato já está ativo")
        if data is not None:
            if data.data_inicio is not None:
                contrato.data_inicio = data.data_inicio
            if data.vigencia_meses is not None:
                contrato.vigencia_meses = data.vigencia_meses
            if data.reajuste_indice is not None:
                contrato.reajuste_indice = data.reajuste_indice
            if data.reajuste_mes is not None:
                contrato.reajuste_mes = data.reajuste_mes
        contrato.status = ContratoStatus.ATIVO.value
        contrato = self.repo.save(contrato)
        self._reconciliar_assinatura(contrato)
        return contrato

    # ---- ponte PA-01 (reconciliação) -------------------------------------
    def _reconciliar_assinatura(self, contrato: Contrato) -> None:
        from app.services.subscription import AssinaturaService
        from app.schemas.subscription import AssinaturaCreate, AssinaturaValorUpdate
        from app.models.subscription import CicloCobranca

        svc = AssinaturaService(self.db)
        valor_real = dec(contrato.valor_mensal)
        if valor_real <= 0:
            return  # contrato sem componente recorrente: nada a lançar no MRR

        ativa = svc.repo.get_ativa_por_empresa(contrato.company_id)
        if ativa is None:
            # Negócio-ganho não criou (ou foi cancelada): a ponte cria a assinatura real.
            assinatura = svc.create(AssinaturaCreate(
                company_id=contrato.company_id,
                deal_id=contrato.proposta_id and self._deal_id_da_proposta(contrato),
                nome_plano=f"Contrato {contrato.numero}"[:120],
                valor_mensal=float(money(valor_real)),
                ciclo_cobranca=CicloCobranca.MENSAL.value,
                ciclo_renovacao_meses=contrato.vigencia_meses,
                responsavel_id=contrato.vendedor_id,
                data_inicio=contrato.data_inicio,
            ))
            contrato.assinatura_id = assinatura.id
            self.repo.save(contrato)
            return

        # Assinatura ativa existe: reconcilia do estimado para o real (delta = real - estimado).
        estimado = self._mrr_estimado_do_negocio(contrato)
        novo_valor = money(dec(ativa.valor_mensal) - estimado + valor_real)
        if novo_valor != money(ativa.valor_mensal):
            svc.atualizar_valor(ativa.id, AssinaturaValorUpdate(
                valor_mensal=float(novo_valor),
                observacao=f"Reconciliação — contrato {contrato.numero}"[:255],
            ))
        contrato.assinatura_id = ativa.id
        self.repo.save(contrato)

    def _deal_id_da_proposta(self, contrato: Contrato):
        if contrato.proposta_id is None:
            return None
        from app.repositories.proposal import PropostaRepository
        proposta = PropostaRepository(self.db).get(contrato.proposta_id)
        return proposta.deal_id if proposta else None

    def _mrr_estimado_do_negocio(self, contrato: Contrato) -> Decimal:
        """Contribuição estimada que o negócio-ganho lançou na assinatura
        (AssinaturaService.mrr_do_negocio) — o que a reconciliação precisa subtrair."""
        deal_id = self._deal_id_da_proposta(contrato)
        if deal_id is None:
            return dec(0)
        deal = self.deals.get(deal_id)
        if deal is None:
            return dec(0)
        from app.services.subscription import AssinaturaService
        return money(dec(AssinaturaService(self.db).mrr_do_negocio(deal)))
