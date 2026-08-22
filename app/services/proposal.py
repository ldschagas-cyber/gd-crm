"""PropostaService — orçamento com captura de desconto (RF-PROP).

Sem governança nesta fase: o desconto é calculado e registrado (RN-F09), mas não há
fila de alçada/aprovação nem bloqueio de piso. O aceite gera um Contrato em rascunho,
herdando itens e preços (RF-PROP-07/RF-CONTR-06).
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import get_current_tenant, get_current_user_id
from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.core.money import dec, desconto_pct, money
from app.models.proposal import Proposta, PropostaItem, PropostaStatus
from app.repositories.product import ProdutoRepository
from app.repositories.proposal import PropostaRepository
from app.schemas.common import PageParams
from app.schemas.proposal import PropostaCreate, PropostaItemCreate, PropostaUpdate

# Transições de status permitidas (RF-PROP-06). Rascunho até estados terminais.
_TRANSICOES = {
    PropostaStatus.RASCUNHO.value: {PropostaStatus.ENVIADA.value, PropostaStatus.RECUSADA.value},
    PropostaStatus.ENVIADA.value: {
        PropostaStatus.EM_NEGOCIACAO.value, PropostaStatus.ACEITA.value,
        PropostaStatus.RECUSADA.value, PropostaStatus.EXPIRADA.value,
    },
    PropostaStatus.EM_NEGOCIACAO.value: {
        PropostaStatus.ACEITA.value, PropostaStatus.RECUSADA.value, PropostaStatus.EXPIRADA.value,
    },
    PropostaStatus.ACEITA.value: set(),
    PropostaStatus.RECUSADA.value: set(),
    PropostaStatus.EXPIRADA.value: set(),
}


class PropostaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PropostaRepository(db)
        self.produtos = ProdutoRepository(db)

    def list(self, params: PageParams, status: str | None = None,
             company_id: UUID | None = None) -> tuple[list[Proposta], int]:
        filters = []
        if status:
            filters.append(Proposta.status == status)
        if company_id:
            filters.append(Proposta.company_id == company_id)
        return self.repo.list(*filters, offset=params.offset, limit=params.size,
                              order_by=Proposta.created_at.desc())

    def get(self, proposta_id: UUID) -> Proposta:
        proposta = self.repo.get(proposta_id)
        if proposta is None:
            raise NotFoundError("Proposta não encontrada")
        return proposta

    def create(self, data: PropostaCreate) -> Proposta:
        proposta = Proposta(
            numero=self.repo.proximo_numero(date.today().year),
            company_id=data.company_id, deal_id=data.deal_id, vendedor_id=data.vendedor_id,
            versao=1, status=PropostaStatus.RASCUNHO.value, validade=data.validade,
            observacao=data.observacao, created_by=get_current_user_id(),
        )
        self._aplicar_itens(proposta, data.itens)
        return self.repo.add(proposta)

    def update(self, proposta_id: UUID, data: PropostaUpdate) -> Proposta:
        proposta = self.get(proposta_id)
        if proposta.status != PropostaStatus.RASCUNHO.value:
            raise ConflictError("Só é possível editar uma proposta em rascunho")
        if data.vendedor_id is not None:
            proposta.vendedor_id = data.vendedor_id
        if data.validade is not None:
            proposta.validade = data.validade
        if data.observacao is not None:
            proposta.observacao = data.observacao
        if data.itens is not None:
            proposta.itens.clear()
            self._aplicar_itens(proposta, data.itens)
        return self.repo.save(proposta)

    def mudar_status(self, proposta_id: UUID, novo: str) -> Proposta:
        proposta = self.get(proposta_id)
        if novo == proposta.status:
            return proposta
        if novo not in _TRANSICOES.get(proposta.status, set()):
            raise ConflictError(f"Transição inválida: {proposta.status} -> {novo}")
        proposta.status = novo
        proposta = self.repo.save(proposta)
        if novo == PropostaStatus.ACEITA.value:
            self._gerar_contrato(proposta)
        return proposta

    # ---- interno ----------------------------------------------------------
    def _aplicar_itens(self, proposta: Proposta, itens: list[PropostaItemCreate]) -> None:
        tabela_total = dec(0)
        proposto_total = dec(0)
        for it in itens:
            produto = self.produtos.get(it.produto_id)
            if produto is None:
                raise NotFoundError("Produto do item não encontrado")
            if not produto.ativo:
                raise AppException(f'Produto "{produto.nome}" está inativo (RF-PROD-02)')
            preco_tabela = dec(produto.preco_tabela)          # snapshot (RN-F13)
            preco_proposto = dec(it.preco_proposto)
            qtd = it.quantidade
            proposta.itens.append(PropostaItem(
                tenant_id=get_current_tenant(),  # filho via cascade não passa pelo repo.add
                produto_id=produto.id, descricao=it.descricao or produto.nome,
                preco_tabela=money(preco_tabela), preco_proposto=money(preco_proposto),
                desconto_pct=desconto_pct(preco_tabela, preco_proposto), quantidade=qtd,
            ))
            tabela_total += preco_tabela * qtd
            proposto_total += preco_proposto * qtd
        proposta.valor_tabela_total = money(tabela_total)
        proposta.valor_proposto_total = money(proposto_total)
        proposta.desconto_pct_total = desconto_pct(tabela_total, proposto_total)

    def _gerar_contrato(self, proposta: Proposta) -> None:
        # Import tardio: evita ciclo Proposta<->Contrato service.
        from app.services.contract import ContratoService
        if proposta.contrato_id is not None:
            return
        contrato = ContratoService(self.db).criar_de_proposta(proposta)
        proposta.contrato_id = contrato.id
        self.repo.save(proposta)
