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
        stmt = (
            select(CnaeCode)
            .where(or_(CnaeCode.descricao.ilike(termo), CnaeCode.codigo.like(f"{busca}%")))
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
