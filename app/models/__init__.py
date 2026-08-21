"""Importa todos os modelos para registro no metadata (Alembic autogenerate)."""
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.company import Company
from app.models.contact import Contact
from app.models.pipeline import Pipeline, PipelineStage
from app.models.deal import Deal
from app.models.task import Task
from app.models.timeline import TimelineEvent
from app.models.import_job import ImportJob
from app.models.audit import AuditLog
from app.models.user_integration import UserIntegration
from app.models.lead_prospect import LeadProspect
from app.models.form import Form, FormSubmission
from app.models.site_visit import SiteVisit
from app.models.snippet import Snippet
from app.models.call import Call
from app.models.origem_option import OrigemOption
from app.models.revenue_investment import RevenueInvestment
from app.models.activity_sla_rule import ActivitySlaMilestoneHit, ActivitySlaRule
from app.models.subscription import Assinatura, AssinaturaEvento
from app.models.onboarding import OnboardingChecklistItem
from app.models.team import Team
from app.models.sales_target import SalesTarget
from app.models.call_target import CallTarget

__all__ = [
    "Base", "Tenant", "User", "Company", "Contact", "Pipeline",
    "PipelineStage", "Deal", "Task", "TimelineEvent", "ImportJob", "AuditLog",
    "UserIntegration", "LeadProspect", "Form", "FormSubmission", "SiteVisit",
    "Snippet", "Call", "OrigemOption", "RevenueInvestment", "ActivitySlaRule", "ActivitySlaMilestoneHit",
    "Assinatura", "AssinaturaEvento", "OnboardingChecklistItem", "Team", "SalesTarget", "CallTarget",
]
