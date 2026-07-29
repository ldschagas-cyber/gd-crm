"""Repositório de contatos."""
from sqlalchemy import or_, select

from app.models.contact import Contact
from app.repositories.base import BaseRepository


class ContactRepository(BaseRepository[Contact]):
    model = Contact

    def search_filter(self, termo: str):
        like = f"%{termo}%"
        return or_(Contact.nome.ilike(like), Contact.email.ilike(like), Contact.cargo.ilike(like))

    def distinct_values(self, column) -> list[str]:
        """Valores distintos já usados numa coluna de texto livre (ex.: cargo)."""
        stmt = (
            select(column)
            .where(Contact.tenant_id == self._tenant_id(), column.isnot(None), column != "")
            .distinct()
            .order_by(column)
        )
        return list(self.db.execute(stmt).scalars().all())
