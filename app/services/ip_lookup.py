"""Identificação de empresa por IP corporativo via IPinfo.io (item 9.8).

Sem IPINFO_API_TOKEN configurado, degrada silenciosamente (retorna None) — o
rastreio de sessões/páginas continua funcionando normalmente, só sem o nome
da empresa. Resultado é cacheado em memória por IP dentro do processo pra
não gastar uma consulta paga por página vista da mesma sessão."""
import httpx

from app.core.config import settings

_cache: dict[str, str | None] = {}


def lookup_company_by_ip(ip: str | None) -> str | None:
    if not ip or not settings.IPINFO_API_TOKEN:
        return None
    if ip in _cache:
        return _cache[ip]

    empresa = None
    try:
        resp = httpx.get(
            f"https://ipinfo.io/{ip}",
            params={"token": settings.IPINFO_API_TOKEN},
            timeout=3.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            company = data.get("company") or {}
            empresa = company.get("name")
    except httpx.HTTPError:
        empresa = None

    _cache[ip] = empresa
    return empresa
