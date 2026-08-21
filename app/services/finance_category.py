"""CategoriaService — plano de categorias financeiras (RF-CAT / PA-02).

Fase 1 usa só categorias de receita. Na primeira leitura por tenant, semeia as
categorias-padrão (idempotente: só cria se ainda não houver nenhuma de receita).
"""
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.finance_category import CategoriaFinanceira, CategoriaTipo
from app.repositories.billing import CategoriaFinanceiraRepository
from app.schemas.billing import CategoriaCreate

# PA-02 (provisório — confirmar com o usuário): categorias de receita padrão.
CATEGORIAS_RECEITA_PADRAO = [
    "Mensalidade recorrente", "Serviço pontual", "Consultoria", "Outras receitas",
]


class CategoriaService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoriaFinanceiraRepository(db)

    def list(self, tipo: str = CategoriaTipo.RECEITA.value) -> list[CategoriaFinanceira]:
        if tipo == CategoriaTipo.RECEITA.value and self.repo.count_por_tipo(tipo) == 0:
            self._seed_receita()
        return self.repo.list_por_tipo(tipo)

    def create(self, data: CategoriaCreate) -> CategoriaFinanceira:
        return self.repo.add(CategoriaFinanceira(nome=data.nome, tipo=data.tipo.value, ativo=True))

    def _seed_receita(self) -> None:
        for nome in CATEGORIAS_RECEITA_PADRAO:
            self.repo.add(CategoriaFinanceira(nome=nome, tipo=CategoriaTipo.RECEITA.value, ativo=True))
