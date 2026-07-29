# ✅ Checklist de Deployment CRM em Produção

## Fase 1: Preparação (30 min)

- [ ] Servidor Linux com Docker + Docker Compose
- [ ] SSH access ao servidor
- [ ] Domínio + DNS apontando para o servidor
- [ ] Certificado SSL disponível (Let's Encrypt ou outro)
  
## Fase 2: Clone e Configuração (20 min)

- [ ] Clone do repositório no servidor:
  ```bash
  cd /opt/gdconecta/crm
  git clone <repo-url> .
  chmod +x atualizar_producao.sh
  ```

- [ ] Criar `.env.prod` baseado em `.env.prod.example`:
  ```bash
  cp .env.prod.example .env.prod
  nano .env.prod
  ```

- [ ] Preencher variáveis obrigatórias:
  - [ ] `POSTGRES_PASSWORD` (senha forte)
  - [ ] `SECRET_KEY` (gerar com Python)
  - [ ] `MICROSOFT_REDIRECT_URI` (seu domínio)
  
- [ ] Se usar Microsoft 365: copiar `secrets/crm_graph_private.key`

- [ ] Configurar TLS:
  ```bash
  sudo certbot certonly --standalone -d crm.gdconecta.com.br
  sudo chmod 755 /etc/letsencrypt/{live,archive}
  ```

## Fase 3: Deploy (10 min)

- [ ] Subir containers:
  ```bash
  docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
  ```

- [ ] Aguardar API pronta (verificar logs):
  ```bash
  docker compose -f docker-compose.prod.yml logs -f api
  ```

- [ ] Criar dados iniciais (seed):
  ```bash
  docker compose -f docker-compose.prod.yml exec -T api python -m app.seed
  ```

## Fase 4: Validação (5 min)

- [ ] Testar health check:
  ```bash
  curl https://crm.gdconecta.com.br/health
  ```

- [ ] Acessar login:
  ```
  https://crm.gdconecta.com.br
  admin@gdconecta.com.br / Admin@123456
  ```

- [ ] Trocar senha do admin (OBRIGATÓRIO)

- [ ] Verificar status dos containers:
  ```bash
  docker compose -f docker-compose.prod.yml ps
  ```

## Fase 5: Monitoramento (Contínuo)

- [ ] Monitorar logs periodicamente:
  ```bash
  docker compose -f docker-compose.prod.yml logs --tail=100 api
  ```

- [ ] Verificar CPU/memória:
  ```bash
  docker stats
  ```

- [ ] Agendar backups do PostgreSQL

- [ ] Testar renovação do certificado SSL

## Atualizações Futuras

- [ ] Para fazer deploy de atualizações:
  ```bash
  ./atualizar_producao.sh
  ```

- [ ] Script automaticamente:
  - Verifica mudanças locais
  - Faz git pull
  - Reconstrói containers
  - Executa migrações
  - Valida API pronta

## Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| API não inicia | `docker compose -f docker-compose.prod.yml logs api` |
| Banco cheio | `docker compose -f docker-compose.prod.yml exec db psql -U crm -d crm` |
| Redis preso | `docker compose -f docker-compose.prod.yml restart redis` |
| Cert expirado | `sudo certbot renew --force-renewal` |
| Worker parado | `docker compose -f docker-compose.prod.yml restart worker` |

---

**Tempo total estimado:** ~1 hora (primeira vez)  
**Tempo de atualização:** ~5-10 min (próximas vezes com script)
