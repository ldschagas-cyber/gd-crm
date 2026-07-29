# CRM GD Conecta — Backend (MVP)

API do CRM GD Conecta em **FastAPI + SQLAlchemy + PostgreSQL + Celery/Redis**, com
arquitetura limpa (router → service → repository → model), DTOs Pydantic,
isolamento multi-tenant (filtro automático + RLS) e autenticação JWT.

## Stack
Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL · JWT · Celery · Redis

## Arquitetura (camadas)
- **api/** — routers HTTP (validação, autenticação, autorização). Sem regra de negócio.
- **schemas/** — DTOs Pydantic (Create/Update/Read + paginação).
- **services/** — regras de negócio, transações, timeline, auditoria.
- **repositories/** — acesso a dados; `BaseRepository` injeta o tenant automaticamente.
- **models/** — mapeamento ORM + mixins (tenant, timestamps, soft delete).
- **core/** — config, database, security (JWT), contexto de tenant, deps, Celery.
- **workers/** — tarefas Celery (importação assíncrona).

## Como rodar (Docker)
```bash
cp .env.example .env          # ajuste SECRET_KEY
docker compose up --build     # sobe db, redis, api, worker e nginx
docker compose exec api python -m app.seed   # cria tenant + admin inicial
```
- API/Swagger: http://localhost:8000/docs
- Via Nginx: http://localhost/api/v1/...

## Como rodar (local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# subir Postgres e Redis (ex.: docker compose up db redis)
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
celery -A app.core.celery_app.celery_app worker -Q default --loglevel=info
```

## Login inicial
`admin@gdconecta.com.br` / `Admin@123456` (troque após o primeiro acesso).

## Migrações
```bash
alembic revision --autogenerate -m "descricao"   # gera nova migração a partir dos models
alembic upgrade head
```

## Endpoints (MVP)
Auth, Tenant, Usuários, Empresas (+Timeline), Contatos, Pipelines (+Board),
Negócios, Tarefas, Dashboards (comercial e vendedor). Documentação completa em `/docs`.

## Multi-tenant
O `tenant_id` é derivado **exclusivamente do JWT**. O `BaseRepository` filtra toda
query pelo tenant atual e o PostgreSQL reforça via **Row-Level Security**.
