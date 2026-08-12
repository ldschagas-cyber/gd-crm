"""Agregador de rotas da API v1."""
from fastapi import APIRouter

from app.api.v1 import (
    auth, calls, cnae_codes, companies, contacts, dashboards, deals, email_templates, embed, forecast, forms,
    funil_metas, import_jobs, lead_prospects, me, message_templates, origem_options, pipelines, public,
    public_companies, revenue_investments, sequences, site_visits, snippets, tasks, tenant, users, workflows,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(calls.router)
api_router.include_router(tenant.router)
api_router.include_router(users.router)
api_router.include_router(companies.router)
api_router.include_router(contacts.router)
api_router.include_router(pipelines.router)
api_router.include_router(deals.router)
api_router.include_router(tasks.router)
api_router.include_router(import_jobs.router)
api_router.include_router(dashboards.router)
api_router.include_router(lead_prospects.router)
api_router.include_router(funil_metas.router)
api_router.include_router(forecast.router)
api_router.include_router(revenue_investments.router)
api_router.include_router(cnae_codes.router)
api_router.include_router(public_companies.router)
api_router.include_router(forms.router)
api_router.include_router(site_visits.router)
api_router.include_router(snippets.router)
api_router.include_router(email_templates.router)
api_router.include_router(message_templates.router)
api_router.include_router(origem_options.router)
api_router.include_router(sequences.router)
api_router.include_router(workflows.router)
api_router.include_router(embed.router)
api_router.include_router(public.router)
