"""Repositório de tarefas."""
from sqlalchemy import or_

from app.models.task import Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    def search_filter(self, termo: str):
        return or_(Task.titulo.ilike(f"%{termo}%"), Task.descricao.ilike(f"%{termo}%"))
