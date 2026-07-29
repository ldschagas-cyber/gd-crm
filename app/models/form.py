"""Form / FormSubmission — formulários públicos embutidos no site institucional (item 9.8)."""
import enum
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class FormStatus(str, enum.Enum):
    ATIVO = "ativo"
    PAUSADO = "pausado"
    RASCUNHO = "rascunho"


class PostSubmitAction(str, enum.Enum):
    CRIAR_LEAD = "criar_lead"
    SO_REGISTRAR = "so_registrar"


# Biblioteca fixa de campos opcionais que o builder permite arrastar pro formulário
# (nome/e-mail são fixos em todo formulário, não entram nessa lista).
FORM_FIELD_LIBRARY = {
    "empresa": "Empresa", "cnpj": "CNPJ", "site": "Site", "cidade": "Cidade", "uf": "UF",
    "segmento": "Segmento", "porte": "Porte",
    "telefone": "Telefone", "whatsapp": "WhatsApp", "linkedin": "LinkedIn", "cargo": "Cargo",
    "nascimento": "Data de nascimento",
    "origem": "Origem do lead", "ja_utiliza_tms": "Já utiliza TMS?", "mensagem": "Mensagem",
}

# Campos cujo widget de valor não é o <input type="text"> padrão — usado pelo embed
# público (app/api/v1/embed.py) pra escolher o tipo de campo renderizado no site.
FORM_FIELD_TYPES = {
    "mensagem": "textarea",
    "ja_utiliza_tms": "boolean",
}


class Form(Base, TenantMixin, TimestampMixin):
    __tablename__ = "forms"

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    pagina: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=FormStatus.RASCUNHO.value, index=True)
    campos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Campos ad hoc criados pelo usuário no builder (chave "custom_..." -> rótulo),
    # complementando FORM_FIELD_LIBRARY. Sempre texto livre — sem tipo próprio.
    campos_personalizados: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    post_submit_action: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PostSubmitAction.CRIAR_LEAD.value
    )


class FormSubmission(Base, TenantMixin, TimestampMixin):
    __tablename__ = "form_submissions"

    id: Mapped[uuid.UUID] = uuid_pk()
    form_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("forms.id"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    valores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ip: Mapped[str | None] = mapped_column(String(45))
    company_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("companies.id"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("contacts.id"))
    duplicado: Mapped[bool] = mapped_column(nullable=False, default=False)
