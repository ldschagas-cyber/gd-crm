"""Repositório de tarefas."""
from app.models.task import Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    def search_filter(self, termo: str):
        return Task.titulo.ilike(f"%{termo}%")
