"""Corrige assinaturas cujo MRR foi lançado pela regra antiga de
AssinaturaService.registrar_negocio_ganho (valor_previsto do negócio tratado como
contrato ANUAL e dividido por 12 — ver histórico de discrepância MRR na tela de
Clientes/Receita Recorrente: negócio "[GF] Connectoway" de R$ 4.940 gerando R$ 412 de
MRR). A regra nova (AssinaturaService.mrr_do_negocio) soma linhas de produto
RECORRENTE do negócio quando existem; sem nenhuma, usa valor_previsto DIRETO (sem
dividir por 12).

Este script varre as assinaturas ATIVAS ligadas a um negócio (deal_id preenchido),
recalcula o MRR pela regra nova e, se diferente do valor gravado, corrige via
AssinaturaService.atualizar_valor (sempre com evento no livro-razão — nunca UPDATE
direto, ver docstring de AssinaturaService). NÃO mexe em assinatura sem deal_id (criada
manualmente) nem em assinatura já reconciliada por um Contrato ativo depois do negócio
ganho (nesses casos o valor atual já é o contrato real, não o estimado antigo — recalcular
pela regra do negócio destruiria a reconciliação).

DRY-RUN por padrão: só imprime o plano. Para aplicar de verdade:
    python scripts/corrigir_mrr_negocio_ganho.py --apply

Como rodar em produção (dentro do container `api`):
    docker compose -f docker-compose.prod.yml exec api python scripts/corrigir_mrr_negocio_ganho.py
    docker compose -f docker-compose.prod.yml exec api python scripts/corrigir_mrr_negocio_ganho.py --apply
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.core.context import set_current_tenant, set_current_user  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.money import dec, money  # noqa: E402
from app.models.contract import Contrato, ContratoStatus  # noqa: E402
from app.models.deal import Deal  # noqa: E402
from app.models.subscription import Assinatura, AssinaturaStatus  # noqa: E402
from app.schemas.subscription import AssinaturaValorUpdate  # noqa: E402
from app.services.subscription import AssinaturaService  # noqa: E402


def main(apply: bool) -> None:
    # Sessão "superusuário": sem tenant fixado no contexto, RLS não filtra (o usuário
    # `crm` do Postgres é superusuário, mesmo padrão de scripts/merge_duplicate_companies.py)
    # — a query abaixo já varre todos os tenants de propósito.
    db = SessionLocal()
    try:
        assinaturas = db.execute(
            select(Assinatura).where(
                Assinatura.status == AssinaturaStatus.ATIVA.value,
                Assinatura.deal_id.isnot(None),
            )
        ).scalars().all()

        pendentes = []
        for assinatura in assinaturas:
            deal = db.get(Deal, assinatura.deal_id)
            if deal is None:
                continue
            # Assinatura já reconciliada por um Contrato ativo: o valor atual é o
            # contrato REAL (ver ContratoService._reconciliar_assinatura), não o estimado
            # do negócio — recalcular pela regra do negócio destruiria a reconciliação.
            tem_contrato_ativo = db.execute(
                select(Contrato.id).where(
                    Contrato.assinatura_id == assinatura.id,
                    Contrato.status == ContratoStatus.ATIVO.value,
                )
            ).first()
            if tem_contrato_ativo:
                continue

            # tenant do contexto precisa estar setado pro AssinaturaService.mrr_do_negocio
            # ler deal.itens via RLS (não usado aqui, é leitura pura em Python) — sem
            # impacto porque já lemos `deal` com sessão sem RLS acima.
            novo_mrr = money(dec(AssinaturaService(db).mrr_do_negocio(deal)))
            atual = money(dec(assinatura.valor_mensal))
            if novo_mrr != atual and novo_mrr > 0:
                pendentes.append((assinatura, deal, atual, novo_mrr))

        if not pendentes:
            print("Nenhuma assinatura para corrigir.")
            return

        print(f"{len(pendentes)} assinatura(s) com MRR desatualizado:")
        for assinatura, deal, atual, novo in pendentes:
            print(f"  - {deal.nome!r} (assinatura {assinatura.id}): "
                  f"R$ {atual} -> R$ {novo}")

        if not apply:
            print("\nDRY-RUN — nada foi gravado. Rode com --apply para corrigir de verdade.")
            return

        for assinatura, deal, _atual, novo in pendentes:
            set_current_tenant(assinatura.tenant_id)
            set_current_user(None)  # correção automatizada, sem usuário humano associado
            AssinaturaService(db).atualizar_valor(assinatura.id, AssinaturaValorUpdate(
                valor_mensal=float(novo),
                observacao="Correção — MRR recalculado sem a regra antiga de dividir "
                            "valor_previsto por 12 (ver scripts/corrigir_mrr_negocio_ganho.py)",
            ))
        db.commit()
        print(f"\n{len(pendentes)} assinatura(s) corrigida(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
