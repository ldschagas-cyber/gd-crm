"""Resolução de referências adiadas entre schemas."""
from app.schemas.deal import DealRead
from app.schemas.pipeline import BoardColumn, BoardResponse

BoardColumn.model_rebuild()
BoardResponse.model_rebuild()
