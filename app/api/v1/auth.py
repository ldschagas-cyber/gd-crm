"""Rotas de autenticação."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest, LoginRequest, MeResponse,
    RefreshRequest, ResetPasswordRequest, TokenResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return AuthService(db).login(data)


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    return AuthService(db).refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: User = Depends(get_current_user)):
    # Tokens são stateless; o cliente descarta o refresh. (Blacklist é Fase 2.)
    return None


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    AuthService(db).generate_reset_token(data.email)
    return {"message": "Se o e-mail existir, enviaremos instruções de redefinição."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    AuthService(db).reset_password(data)
    return None


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return user
