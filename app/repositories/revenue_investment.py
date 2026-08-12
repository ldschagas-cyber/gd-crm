"""Repositório de lançamentos de investimento comercial."""
from app.models.revenue_investment import RevenueInvestment
from app.repositories.base import BaseRepository


class RevenueInvestmentRepository(BaseRepository[RevenueInvestment]):
    model = RevenueInvestment
