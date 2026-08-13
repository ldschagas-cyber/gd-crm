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

    def get_by_domain(self, domain: str) -> Company | None:
        """Primeira empresa (tenant atual, não deletada) cujo site ou e-mail contém o
        domínio informado. Usa ILIKE porque não há coluna de domínio materializada — ok
        pro volume esperado; se a base crescer muito, vale materializar domínio numa
        coluna indexada (ver app/services/company_dedupe.py)."""
        like = f"%{domain}%"
        return self.db.execute(
            self._base_query().where(
                Company.deleted_at.is_(None),
                or_(Company.site.ilike(like), Company.email.ilike(like)),
            )
        ).scalars().first()

    def find_by_uf_not_deleted(self, uf: str | None) -> list[Company]:
        """Candidatas pra comparação de nome normalizado (dedupe_key) — feita em Python,
        sem equivalente direto em SQL sem uma coluna gerada. Filtra por UF quando
        informado, sempre exclui soft-deleted."""
        stmt = self._base_query().where(Company.deleted_at.is_(None))
        if uf:
            stmt = stmt.where(Company.uf == uf)
        return list(self.db.execute(stmt).scalars().all())

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
