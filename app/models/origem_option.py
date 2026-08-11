"""OrigemOption — opções extras cadastráveis para o campo "Origem" de Empresa/Pesquisa de Leads.

Antes, a lista de opções do seletor era hardcoded no frontend (duplicada e divergente
entre EmpresasPage e PesquisaLeadsPage — ORIGENS_EMPRESA x ORIGENS). O valor salvo no
registro continua sendo texto livre (Company.origem / LeadProspect.origem, ambos
String(80) sem FK — não vale migrar dado existente pra uma FK rígida), mas agora o
tenant pode cadastrar uma opção nova direto no formulário ("+ Criar nova opção…") em
vez de ficar preso à lista de fábrica. Ver app/services/origem_option.py.
"""
import uuid

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class OrigemOption(Base, TenantMixin, TimestampMixin):
    __tablename__ = "origem_options"
    __table_args__ = (UniqueConstraint("tenant_id", "nome", name="uq_origem_option_tenant_nome"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
