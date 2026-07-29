"""Seed inicial: cria um tenant e um usuário administrador.

Uso:
    python -m app.seed

Como o MVP não possui cadastro público de tenant, este script faz o bootstrap
do primeiro tenant e do admin, que então cria os demais usuários via API.
"""
import uuid

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole, UserStatus

ADMIN_EMAIL = "admin@gdconecta.com.br"
ADMIN_SENHA = "Admin@123456"


def run() -> None:
    db = SessionLocal()
    try:
        existente = db.query(Tenant).filter(Tenant.cnpj == "00000000000000").first()
        if existente:
            print("Seed já aplicado. Tenant:", existente.id)
            return
        tenant = Tenant(
            id=uuid.uuid4(), razao_social="GD Conecta", nome_fantasia="GD Conecta",
            cnpj="00000000000000", plano="pro", status="ativo",
        )
        db.add(tenant)
        db.flush()
        admin = User(
            id=uuid.uuid4(), tenant_id=tenant.id, nome="Administrador",
            email=ADMIN_EMAIL, senha_hash=hash_password(ADMIN_SENHA),
            perfil=UserRole.ADMIN.value, status=UserStatus.ATIVO.value,
        )
        db.add(admin)
        db.commit()
        print("Tenant criado:", tenant.id)
        print("Admin:", ADMIN_EMAIL, "/ senha:", ADMIN_SENHA)
    finally:
        db.close()


if __name__ == "__main__":
    run()
