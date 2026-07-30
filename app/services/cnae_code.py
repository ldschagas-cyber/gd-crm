"""Consulta à tabela de referência CNAE (dado global, sem tenant — ver app/models/cnae_code.py)."""
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.cnae_code import CnaeCode

NIVEIS = {"subclasse": "codigo", "classe": "classe", "grupo": "grupo", "divisao": "divisao"}


class CnaeCodeService:
    def __init__(self, db: Session):
        self.db = db

    def search(self, busca: str, limit: int = 20) -> list[CnaeCode]:
        termo = f"%{busca}%"
        # CNAE costuma ser digitado/colado no formato oficial com máscara
        # (ex.: "29.49-2/99"); a coluna codigo guarda só dígitos ("2949299").
        so_digitos = "".join(c for c in busca if c.isdigit())
        condicoes = [CnaeCode.descricao.ilike(termo), CnaeCode.codigo.like(f"{busca}%")]
        if so_digitos and so_digitos != busca:
            condicoes.append(CnaeCode.codigo.like(f"{so_digitos}%"))
        stmt = (
            select(CnaeCode)
            .where(or_(*condicoes))
            .order_by(CnaeCode.descricao)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def similares(self, codigo: str, nivel: str) -> list[CnaeCode]:
        alvo = self.db.get(CnaeCode, codigo)
        if alvo is None:
            raise NotFoundError("Código CNAE não encontrado")
        coluna_nome = NIVEIS.get(nivel, "classe")
        valor = getattr(alvo, coluna_nome)
        coluna = getattr(CnaeCode, coluna_nome)
        stmt = select(CnaeCode).where(coluna == valor).order_by(CnaeCode.descricao)
        return list(self.db.execute(stmt).scalars().all())
