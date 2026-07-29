# Deployment do CRM GD Conecta em Produção

## 📋 Pré-requisitos

- [ ] Servidor Linux com Docker e Docker Compose instalados
- [ ] Acesso SSH ao servidor
- [ ] Domínio configurado (ex: `crm.gdconecta.com.br`)
- [ ] Certificado SSL (Let's Encrypt ou outro)
- [ ] Senha segura para PostgreSQL
- [ ] Credenciais Microsoft 365 (se usar integração de E-mail/Calendário)

## 🚀 Deployment Inicial

### 1. Preparar o servidor

```bash
cd /opt/gdconecta/crm  # ou seu diretório preferido
git clone <repo-url> .
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.prod.example .env.prod
nano .env.prod
```

**Modificar obrigatoriamente:**

- `POSTGRES_PASSWORD` — senha forte (ex: 32 caracteres aleatórios)
- `DATABASE_URL` — ajustar senha para corresponder
- `SECRET_KEY` — gerar com:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(48))"
  ```
- `MICROSOFT_REDIRECT_URI` — seu domínio (ex: `https://crm.gdconecta.com.br/api/v1/me/integrations/callback`)

**Se usar Microsoft 365:**
- `MICROSOFT_CLIENT_ID` e `MICROSOFT_TENANT_ID`
- Copiar chave privada para `secrets/crm_graph_private.key`

### 3. Configurar Nginx (TLS com Let's Encrypt)

Se o Let's Encrypt já está em uso no servidor:

```bash
# Se é o primeiro deploy, criar certificado
sudo certbot certonly --standalone -d crm.gdconecta.com.br

# Permissões (docker precisa ler o cert)
sudo chmod 755 /etc/letsencrypt/{live,archive}
```

Se usa um certificado diferente, editar `nginx.conf` com o caminho correto.

### 4. Criar banco de dados inicial (seed)

Na primeira vez, você pode gerar um usuário admin automático via seed:

```bash
# Dentro do container (após subir)
docker compose -f docker-compose.prod.yml exec -T api python -m app.seed
```

Isso criará:
- Tenant padrão: `GD Conecta`
- Admin: `admin@gdconecta.com.br` / `Admin@123456` (troque imediatamente!)

### 5. Subir os containers

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Verificar status:
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api
```

### 6. Validar deployment

```bash
# Health check
curl https://crm.gdconecta.com.br/health

# Swagger (protegido — login necessário)
curl https://crm.gdconecta.com.br/docs
```

## 🔄 Atualizações em Produção

**Via script automático (recomendado):**

```bash
chmod +x atualizar_producao.sh
./atualizar_producao.sh
```

O script:
1. Verifica se há mudanças locais não commitadas
2. Faz `git pull`
3. Reconstrói os containers
4. Executa migrações Alembic
5. Aguarda a API ficar pronta

**Manualmente (se o script não funcionar):**

```bash
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml logs -f api
```

## 🔐 Segurança

- [ ] Trocar senha do admin na primeira vez
- [ ] Verificar que `DEBUG=false` no `.env.prod`
- [ ] Certificado SSL válido e renovação automática (Let's Encrypt)
- [ ] Banco de dados NÃO exposto externamente (porta 5432 não mapeada)
- [ ] Redis NÃO exposto externamente
- [ ] Backups automáticos do PostgreSQL agendados
- [ ] Logs centralizados (opcional, mas recomendado)

## 📊 Monitoramento

### Logs

```bash
# Última hora de logs da API
docker compose -f docker-compose.prod.yml logs --tail=1000 api

# Seguir logs em tempo real
docker compose -f docker-compose.prod.yml logs -f api

# Logs do worker Celery
docker compose -f docker-compose.prod.yml logs -f worker

# Logs do Beat (scheduler)
docker compose -f docker-compose.prod.yml logs -f beat
```

### Status dos containers

```bash
docker compose -f docker-compose.prod.yml ps
docker stats
```

### Banco de dados

```bash
# Acessar psql (dentro do container)
docker compose -f docker-compose.prod.yml exec db psql -U crm -d crm

# Verificar tamanho do banco
SELECT pg_size_pretty(pg_database_size('crm'));
```

## 🔧 Troubleshooting

### API não inicia (erro de migração)

```bash
docker compose -f docker-compose.prod.yml logs -f api

# Rollback manual (se necessário)
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1
```

### Celery Worker preso

```bash
docker compose -f docker-compose.prod.yml restart worker
```

### Redis cheio

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli FLUSHALL
```

### Banco de dados cheio

```bash
# Verificar tamanho das tabelas
docker compose -f docker-compose.prod.yml exec db psql -U crm -d crm \
  -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) \
      FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') \
      ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

## 📝 Variáveis de Ambiente (Referência Completa)

Veja `docs/ESPECIFICACAO_TECNICA_V1.md` para detalhes sobre cada endpoint e integração.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `APP_NAME` | Nome da app | `CRM GD Conecta` |
| `DEBUG` | Modo debug (NUNCA true em prod) | `false` |
| `ENVIRONMENT` | Ambiente | `production` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://crm:senha@db:5432/crm` |
| `SECRET_KEY` | Chave JWT (64 chars min) | `(gerada automaticamente)` |
| `REDIS_URL` | Redis para cache/sessions | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Redis para tarefas async | `redis://redis:6379/1` |
| `MICROSOFT_CLIENT_ID` | Azure AD App ID | (seu valor) |
| `MICROSOFT_TENANT_ID` | Azure AD Tenant ID | (seu valor) |
| `MICROSOFT_REDIRECT_URI` | Callback OAuth2 | `https://seu-dominio.com.br/api/v1/me/integrations/callback` |

## ⚠️ Notas Importantes

1. **Working tree**: O script `atualizar_producao.sh` verifica se há mudanças locais. Não edite arquivos no servidor manualmente — sempre commite e faça push para o Git.

2. **Multi-tenant**: O CRM usa isolamento multi-tenant via RLS do PostgreSQL. Cada tenant tem seus dados isolados.

3. **Celery**: O worker e o beat são necessários para tarefas assíncronas (importação, agendamento). Se não subir, funcionalidades automáticas ficarão paradas.

4. **Certificado SSL**: O Nginx espera certificados em `/etc/letsencrypt/live/seu-dominio.com.br/`. Ajustar se usar outro provedor.

5. **Backups**: Agend

ar backups automáticos do PostgreSQL (ex: `pg_dump` diário):
   ```bash
   docker compose -f docker-compose.prod.yml exec db pg_dump -U crm crm > backup-$(date +%Y%m%d).sql
   ```
