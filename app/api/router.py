"""Agregador de rotas da API v1."""
from fastapi import APIRouter

from app.api.v1 import (
    auth, cadences, companies, contacts, dashboards, deals, email_templates, embed, forms, import_jobs,
    lead_prospects, me, pipelines, public, sequences, site_visits, snippets, tasks, tenant, users, workflows,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(me.router)
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
api_router.include_router(forms.router)
api_router.include_router(site_visits.router)
api_router.include_router(snippets.router)
api_router.include_router(email_templates.router)
api_router.include_router(sequences.router)
api_router.include_router(cadences.router)
api_router.include_router(workflows.router)
api_router.include_router(embed.router)
api_router.include_router(public.router)
