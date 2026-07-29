"""DTOs dos dashboards."""
from pydantic import BaseModel


class CommercialDashboard(BaseModel):
    total_leads: int
    empresas_qualificadas: int
    negocios_ativos: int
    receita_prevista: float
    receita_ganha: float
    taxa_conversao: float
    ticket_medio: float


class SellerDashboard(BaseModel):
    tarefas_pendentes: int
    tarefas_concluidas: int
    ligacoes_realizadas: int
    emails_enviados: int
    negocios_abertos: int
    receita_prevista: float
