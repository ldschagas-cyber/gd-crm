#!/usr/bin/env bash
# ============================================================
# Argos — Atualizar produção
# ============================================================
# Uso (no servidor, dentro da pasta do projeto):
#   ./atualizar_producao.sh
#
# Faz: git pull -> rebuild dos containers -> espera a API
# responder (migrações do Alembic já rodam sozinhas, dentro do
# comando do container -- ver docker-compose.prod.yml). Não pede
# confirmação no meio -- se algo falhar, o script para e mostra
# o log relevante.
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"

echo
echo "========================================"
echo " Argos — Atualizando"
echo "========================================"
echo

# ---------------------------------------------------------------
# 1) Docker disponível?
# ---------------------------------------------------------------
if ! docker info >/dev/null 2>&1; then
  echo "[ERRO] Docker não está rodando ou o usuário atual não tem permissão."
  echo "       Rode 'sudo systemctl status docker' pra checar."
  exit 1
fi
echo "[OK]  Docker respondendo."

# ---------------------------------------------------------------
# 2) Working tree limpo? (evita 'git pull' pisar em mudança manual
#    esquecida no servidor, ex.: .env.prod editado direto por engano)
# ---------------------------------------------------------------
if [ -n "$(git status --porcelain)" ]; then
  echo
  echo "[ERRO] Há mudanças não commitadas no servidor:"
  git status --short
  echo
  echo "       Resolva isso antes de atualizar (commit, stash ou descarte"
  echo "       manualmente) -- o script não decide isso por você."
  exit 1
fi
echo "[OK]  Working tree limpo."

# ---------------------------------------------------------------
# 3) git pull
# ---------------------------------------------------------------
echo
echo "Buscando código novo (git pull)..."
git pull
echo "[OK]  Código atualizado."

# ---------------------------------------------------------------
# 4) Rebuild + subir containers
#    (o backend já roda 'alembic upgrade head' sozinho antes do
#    uvicorn -- ver 'command:' em docker-compose.prod.yml)
# ---------------------------------------------------------------
echo
echo "Reconstruindo e subindo containers (pode demorar alguns minutos)..."
if ! $COMPOSE up -d --build; then
  echo
  echo "[ERRO] Falha ao subir os containers. Últimos logs:"
  echo "----------------------------------------------------------------------"
  $COMPOSE logs --tail=60
  echo "----------------------------------------------------------------------"
  exit 1
fi
echo "[OK]  Containers no ar."

# ---------------------------------------------------------------
# 5) Esperar a API responder (migrações + boot da API)
# ---------------------------------------------------------------
echo
echo "Aguardando a API ficar pronta (migrações + boot)..."
pronto=0
for i in $(seq 1 60); do
  if $COMPOSE exec -T api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" >/dev/null 2>&1; then
    pronto=1
    break
  fi
  printf "."
  sleep 3
done
echo

if [ "$pronto" -ne 1 ]; then
  echo
  echo "[AVISO] A API demorou mais que o esperado (3min). Verifique com:"
  echo "        $COMPOSE logs -f api"
  echo "        Se for erro de migração, o log vai mostrar o traceback do Alembic."
  exit 1
fi

echo "[OK]  API pronta."
echo
echo "========================================"
echo " Atualização concluída."
echo " Logs:   $COMPOSE logs -f api"
echo " Status: docker stats"
echo "========================================"
echo
