"""Repositório de equipes de vendas."""
from app.models.team import Team
from app.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    model = Team
