"""DTOs de Chamadas (Twilio Voice)."""
from pydantic import BaseModel


class CallConfigRead(BaseModel):
    conectado: bool


class AccessTokenRead(BaseModel):
    token: str
