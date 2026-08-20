"""Serviço de equipes de vendas."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.team import Team
from app.models.user import User
from app.repositories.team import TeamRepository
from app.repositories.user import UserRepository
from app.schemas.team import TeamCreate, TeamUpdate


class TeamService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TeamRepository(db)
        self.users = UserRepository(db)

    def list(self) -> list[Team]:
        teams, _ = self.repo.list(limit=1000, order_by=Team.nome)
        return teams

    def get(self, team_id: UUID) -> Team:
        team = self.repo.get(team_id)
        if team is None:
            raise NotFoundError("Equipe não encontrada")
        return team

    def create(self, data: TeamCreate) -> Team:
        return self.repo.add(Team(nome=data.nome, gestor_id=data.gestor_id))

    def update(self, team_id: UUID, data: TeamUpdate) -> Team:
        team = self.get(team_id)
        payload = data.model_dump(exclude_unset=True)
        for field, value in payload.items():
            setattr(team, field, value)
        return self.repo.save(team)

    def delete(self, team_id: UUID) -> None:
        team = self.get(team_id)
        # Desliga os vendedores da equipe antes de remover — a FK users.team_id é
        # nullable, então basta zerar (não apaga nem move os usuários).
        membros, _ = self.users.list(User.team_id == team_id, limit=1000)
        for membro in membros:
            membro.team_id = None
        self.db.flush()
        self.repo.delete(team)
