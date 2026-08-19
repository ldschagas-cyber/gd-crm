"""Preview READ-ONLY da normalização de nomes de empresa em produção.

NÃO grava nada — só lista, para cada tabela, o que a migração
`normalize_existing_company_names` mudaria (antes -> depois) e a contagem total.

Regras (idênticas às da migração):
  - lead_prospects.empresa      -> normaliza TODAS as linhas.
  - companies.razao_social      -> normaliza SÓ as linhas 100% em CAIXA ALTA
                                   (preserva grafia própria: iFood, GD Conecta, ...).

Como rodar em produção (dentro do container `api`, que já tem a DATABASE_URL):
    docker compose -f docker-compose.prod.yml exec api python scripts/preview_normalize_company_names.py

O usuário `crm` do Postgres é superusuário e ignora RLS, então a leitura
abrange todos os tenants de uma vez — sem loop por tenant.
"""
from sqlalchemy import text

from app.core.database import engine
from app.core.text import normalize_company_name


def _is_all_caps(s: str) -> bool:
    """True se `s` tem ao menos uma letra e está inteiro em maiúsculas
    (ex.: "ACME LTDA" -> True; "iFood" -> False; "123" -> False)."""
    return any(c.isalpha() for c in s) and s == s.upper()


def _collect(conn, tabela: str, coluna: str, so_caixa_alta: bool):
    rows = conn.execute(
        text(f"SELECT {coluna} FROM {tabela} WHERE {coluna} IS NOT NULL AND {coluna} <> ''")
    ).fetchall()
    mudancas = []
    for (valor,) in rows:
        if so_caixa_alta and not _is_all_caps(valor):
            continue
        novo = normalize_company_name(valor)
        if novo and novo != valor:
            mudancas.append((valor, novo))
    return len(rows), mudancas


def _imprimir(titulo: str, total: int, mudancas):
    print(f"\n=== {titulo} ===")
    print(f"linhas analisadas: {total} | linhas que mudariam: {len(mudancas)}")
    for antes, depois in mudancas:
        print(f"  {antes!r}  ->  {depois!r}")


def main() -> None:
    with engine.connect() as conn:
        total_leads, mud_leads = _collect(conn, "lead_prospects", "empresa", so_caixa_alta=False)
        total_emp, mud_emp = _collect(conn, "companies", "razao_social", so_caixa_alta=True)

    _imprimir("pesquisa_leads (empresa) — normaliza tudo", total_leads, mud_leads)
    _imprimir("empresas (razao_social) — só CAIXA ALTA", total_emp, mud_emp)
    print(f"\nTOTAL a alterar: {len(mud_leads)} lead(s) + {len(mud_emp)} empresa(s). (preview — nada foi gravado)")


if __name__ == "__main__":
    main()
