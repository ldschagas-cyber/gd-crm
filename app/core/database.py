"""Configuração do engine e da sessão do SQLAlchemy."""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.context import get_current_tenant

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@event.listens_for(SessionLocal, "after_begin")
def _set_rls_tenant(session, transaction, connection):
    """Defende em profundidade: propaga o tenant atual para a sessão do Postgres
    (consumido por políticas RLS, quando habilitadas no banco)."""
    tenant_id = get_current_tenant()
    if tenant_id is not None:
        connection.exec_driver_sql(
            "SELECT set_config('app.current_tenant', %s, true)", (str(tenant_id),)
        )


def get_db() -> Generator[Session, None, None]:
    """Dependência FastAPI: fornece uma sessão por requisição."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
