"""Rotas de Preferências pessoais — auto-atendimento do próprio usuário logado."""
from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import MeResponse
from app.schemas.me import IntegrationAuthorizeUrl, IntegrationRead, MeUpdate, PasswordChange, UpcomingMeetingRead
from app.services.me import MeService

router = APIRouter(prefix="/me", tags=["Preferências pessoais"])


@router.put("", response_model=MeResponse)
def update_me(data: MeUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MeService(db).update_profile(user, data)


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(data: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    MeService(db).change_password(user, data)
    return None


@router.post("/avatar", response_model=MeResponse)
def upload_avatar(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MeService(db).set_avatar(user, file)


@router.delete("/avatar", response_model=MeResponse)
def delete_avatar(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MeService(db).remove_avatar(user)


@router.get("/upcoming-meetings", response_model=list[UpcomingMeetingRead])
def upcoming_meetings(days: int = 7, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MeService(db).upcoming_meetings(user, days=days)


def _integration_read(tipo: str, row) -> IntegrationRead:
    if row is None:
        return IntegrationRead(tipo=tipo, provider="microsoft365", conectado=False, conectado_em=None, ativo=False)
    return IntegrationRead(
        tipo=row.tipo, provider=row.provider, conectado=True,
        conectado_em=row.conectado_em, ativo=row.ativo,
    )


@router.get("/integrations/callback", include_in_schema=False)
async def integration_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Recebido direto do navegador após o consentimento na Microsoft — sem JWT de sessão.

    Precisa ser `async def` pelo mesmo motivo de `get_current_user`: a mutação
    do contexto de tenant/usuário (feita dentro de `complete_integration`, a
    partir do `state`) só fica visível pras chamadas síncronas seguintes
    (repositório) se tudo rodar na mesma task do event loop.

    Precisa vir ANTES de `/integrations/{tipo}` no arquivo: como os dois são
    GET com um único segmento depois de `/integrations/`, o FastAPI casa por
    ordem de registro — se `{tipo}` viesse primeiro, ele "engoliria" o
    `callback` literal como se fosse um valor de `tipo`.
    """
    tipo = MeService(db).complete_integration(state, code)
    return RedirectResponse(f"{settings.FRONTEND_URL}/preferencias?tab={tipo}")


@router.get("/integrations/{tipo}", response_model=IntegrationRead)
def get_integration(tipo: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _integration_read(tipo, MeService(db).get_integration(user, tipo))


@router.post("/integrations/{tipo}", response_model=IntegrationAuthorizeUrl)
def connect_integration(tipo: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return IntegrationAuthorizeUrl(auth_url=MeService(db).get_authorize_url(user, tipo))


@router.delete("/integrations/{tipo}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_integration(tipo: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    MeService(db).disconnect_integration(user, tipo)
    return None
