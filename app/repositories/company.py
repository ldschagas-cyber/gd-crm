"""Repositório de empresas."""
from sqlalchemy import or_, select

from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    model = Company

    def get_by_cnpj(self, cnpj: str) -> Company | None:
        return self.db.execute(
            self._base_query().where(Company.cnpj == cnpj)
        ).scalar_one_or_none()

    def get_by_name(self, razao_social: str) -> Company | None:
        return self.db.execute(
            self._base_query().where(Company.razao_social.ilike(razao_social))
        ).scalars().first()

    def search_filter(self, termo: str):
        like = f"%{termo}%"
        return or_(Company.razao_social.ilike(like), Company.nome_fantasia.ilike(like))

    def distinct_values(self, column) -> list[str]:
        """Valores distintos já usados numa coluna de texto livre (ex.: segmento, porte)."""
        stmt = (
            select(column)
            .where(
                Company.tenant_id == self._tenant_id(),
                Company.deleted_at.is_(None),
                column.isnot(None),
                column != "",
            )
            .distinct()
            .order_by(column)
        )
        return list(self.db.execute(stmt).scalars().all())
