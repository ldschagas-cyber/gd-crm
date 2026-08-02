"""Rotas de Chamadas (Twilio Voice) — autenticadas, consumidas pelo softphone do frontend."""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.exceptions import ConflictError
from app.models.user import User
from app.schemas.call import AccessTokenRead, CallConfigRead
from app.services.twilio_voice import is_configured, mint_access_token

router = APIRouter(prefix="/calls", tags=["Chamadas"])


@router.get("/config", response_model=CallConfigRead)
def get_call_config(user: User = Depends(get_current_user)):
    return CallConfigRead(conectado=is_configured())


@router.get("/token", response_model=AccessTokenRead)
def get_access_token(user: User = Depends(get_current_user)):
    if not is_configured():
        raise ConflictError("Chamadas (Twilio Voice) ainda não configuradas nesta instância do CRM.")
    return AccessTokenRead(token=mint_access_token(user))
