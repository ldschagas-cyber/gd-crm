#!/usr/bin/env bash
# ============================================================
# Setup helper para deployment do CRM em produção
# ============================================================
# Gera SECRET_KEY, senha de BD, e cria .env.prod com template
# Uso:
#   bash setup_prod.sh
# ============================================================

set -euo pipefail

echo
echo "========================================"
echo " GD CRM — Setup Produção"
echo "========================================"
echo

# Gerar SECRET_KEY
echo "Gerando SECRET_KEY (chave aleatória de 64 caracteres)..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
echo "✓ SECRET_KEY gerada"
echo

# Gerar senha do PostgreSQL
echo "Gerando senha PostgreSQL (32 caracteres)..."
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
echo "✓ POSTGRES_PASSWORD gerada"
echo

# Avisar sobre arquivo
if [ -f ".env.prod" ]; then
  echo "[AVISO] Arquivo .env.prod já existe. Será preservado."
  echo "        Se quiser resetar, delete-o primeiro: rm .env.prod"
  echo
else
  echo "Criando .env.prod baseado em .env.prod.example..."
  cp .env.prod.example .env.prod

  # Substituir valores (usar | para não conflitar com /)
  sed -i "s|MUDE-ISSO-PARA-UMA-SENHA-SEGURA|${POSTGRES_PASSWORD}|g" .env.prod
  sed -i "s|GERE-UMA-CHAVE-ALEATORIA-DE-64-CARACTERES-COM-O-COMANDO-ACIMA|${SECRET_KEY}|g" .env.prod

  echo "✓ .env.prod criado"
  echo
fi

# Mostrar valores gerados
echo "========================================"
echo " Valores Gerados"
echo "========================================"
echo
echo "SECRET_KEY:"
echo "  $SECRET_KEY"
echo
echo "POSTGRES_PASSWORD:"
echo "  $POSTGRES_PASSWORD"
echo
echo "========================================"
echo " Próximas Etapas"
echo "========================================"
echo
echo "1. Editar .env.prod para revisar/ajustar:"
echo "   nano .env.prod"
echo
echo "2. Configurar domínio (em MICROSOFT_REDIRECT_URI)"
echo
echo "3. Se usar certificado Let's Encrypt:"
echo "   sudo certbot certonly --standalone -d seu-dominio.com.br"
echo
echo "4. Se usar Microsoft 365, copiar chave privada:"
echo "   mkdir -p secrets"
echo "   cp /path/to/crm_graph_private.key secrets/"
echo
echo "5. Subir containers:"
echo "   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build"
echo
echo "6. Criar dados iniciais (seed):"
echo "   docker compose -f docker-compose.prod.yml exec -T api python -m app.seed"
echo
echo "========================================"
echo
