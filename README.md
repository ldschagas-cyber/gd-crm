# Argos — Backend (MVP)

API do Argos, o CRM da GD Conecta, em **FastAPI + SQLAlchemy + PostgreSQL + Celery/Redis**, com
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

## Integrações externas (envio automático em Sequências)
- **E-mail** — Microsoft 365/Graph, OAuth **por usuário** (cada vendedor conecta a
  própria caixa em Preferências → E-mail/Calendário). Ver `app/models/user_integration.py`,
  `app/services/graph_client.py`, `app/api/v1/me.py`.
- **WhatsApp** — Twilio (WhatsApp Business Platform como BSP), config **global do
  servidor** (`TWILIO_WHATSAPP_FROM` + as credenciais Twilio de Chamadas), não por
  usuário nem por tenant no banco — a empresa tem um único número, igual ao Twilio
  Voice já usado em Chamadas. Ver `app/services/twilio_whatsapp.py`. Toda mensagem
  iniciada pela empresa (o caso de Sequência fria) só pode usar um *Content
  Template* pré-aprovado pela Meta — por isso o envio automático só é tentado
  quando o `MessageTemplate` correspondente tem `whatsapp_content_sid` preenchido
  (SID do template no Twilio Content Template Builder); sem isso, ou sem
  `TWILIO_WHATSAPP_FROM` configurado, a etapa cai no mesmo fallback de sempre:
  `Task` manual com o texto já mesclado, pronto pro vendedor copiar.
- **LinkedIn** (conexão/mensagem) — **deliberadamente não automatizado**. Não
  existe API oficial do LinkedIn que cubra prospecção fria (Marketing/Sales
  Navigator APIs têm acesso restrito e não servem esse caso de uso); automatizar
  via scraping ou APIs não oficiais viola os Termos de Uso e arrisca banir a
  conta usada, inclusive pessoal. Essas etapas continuam só gerando `Task` com o
  texto pronto pra copiar — não é um "a fazer", é a decisão final.

Em todos os casos, `app/services/sequence_dispatch.py:advance_due_steps` é quem
decide entre enviar de verdade ou cair pro fallback de `Task` — nunca falha o
enrollment inteiro por causa de um provedor fora do ar ou não configurado.
