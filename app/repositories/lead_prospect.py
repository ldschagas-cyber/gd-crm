"""Repositório de pesquisas de leads."""
from sqlalchemy import or_

from app.models.lead_prospect import LeadProspect
from app.repositories.base import BaseRepository


class LeadProspectRepository(BaseRepository[LeadProspect]):
    model = LeadProspect

    def search_filter(self, termo: str):
        like = f"%{termo}%"
        return or_(LeadProspect.empresa.ilike(like), LeadProspect.setor.ilike(like),
                   LeadProspect.segmento.ilike(like))
