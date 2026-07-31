"""Configurações da aplicação carregadas de variáveis de ambiente."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Aplicação
    APP_NAME: str = "CRM GD Conecta"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Banco de dados
    DATABASE_URL: str = "postgresql+psycopg://crm:crm@localhost:5432/crm"

    # Segurança / JWT
    SECRET_KEY: str = "troque-esta-chave-em-producao"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:5174"]

    # Para onde redirecionar o navegador após o callback OAuth (Microsoft 365).
    FRONTEND_URL: str = "http://localhost:5174"

    # Integração Microsoft 365/Graph (Preferências pessoais) — vazio até o
    # cliente registrar o app no Azure AD (ver docs/ESPECIFICACAO_TECNICA_V1.md §9.2).
    # Autenticação por certificado (não client secret): a política do tenant
    # gdconecta.onmicrosoft.com bloqueia criação de client secrets.
    MICROSOFT_CLIENT_ID: str | None = None
    MICROSOFT_TENANT_ID: str | None = None
    MICROSOFT_REDIRECT_URI: str | None = None
    MICROSOFT_CERT_PATH: str = "secrets/crm_graph_private.key"
    MICROSOFT_CERT_THUMBPRINT: str | None = None

    # Chave Fernet pra criptografar access_token/refresh_token em repouso em
    # UserIntegration antes de gravar no banco. Gerar com:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    TOKEN_ENCRYPTION_KEY: str | None = None

    # Enriquecimento de Pesquisa de Leads via IA (Anthropic) — vazio até configurar
    # a chave (ver conversa: mesma conta usada no GD Diagnóstico, chave própria recomendada).
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-5"

    # Identificação de empresa por IP corporativo no Rastreio do site (item 9.8) —
    # vazio até o usuário criar conta no IPinfo.io (plano com add-on "IP to Company").
    IPINFO_API_TOKEN: str | None = None

    # Uploads locais (ex.: foto de perfil) — servidos via StaticFiles em /uploads.
    UPLOAD_DIR: str = "uploads"
    MAX_AVATAR_MB: int = 5

    # Buscar Empresas: API pública hospedada do projeto minha-receita (dados
    # abertos de CNPJ da Receita Federal). Sem chave/autenticação, sem SLA
    # documentado — serviço best-effort mantido por 1 pessoa.
    MINHA_RECEITA_BASE_URL: str = "https://minhareceita.org"
    MINHA_RECEITA_TIMEOUT_SECONDS: float = 8.0

    # Inteligência Comercial (Pesquisa de Leads): consulta o Benchmark Setorial
    # do GD Diagnóstico via endpoint interno /internal, serviço-a-serviço — não
    # é JWT de usuário. DIAGNOSTICO_INTERNAL_API_KEY precisa ser o MESMO valor
    # configurado como INTERNAL_API_KEY no .env do Diagnóstico. Em produção, os
    # dois containers estão no mesmo Docker network e a URL aponta direto pro
    # nome do serviço (ex.: http://gd_frete_backend:8000), sem passar pelo nginx.
    DIAGNOSTICO_INTERNAL_URL: str | None = None
    DIAGNOSTICO_INTERNAL_API_KEY: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
