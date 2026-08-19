"""Prepara a base para o início da operação: zera atividade de teste sem tocar no
inventário que se quer manter (empresas + leads).

Faz DUAS limpezas, ambas IRREVERSÍVEIS (essas tabelas não têm soft-delete):

  1) Contatos realizados de AGOSTO/2026 — apaga os TimelineEvent de tipo `ligacao` e
     `email` no período. É isso que o indicador "Contatos realizados" conta (empresas
     distintas com ligação/e-mail no mês). NÃO mexe na tabela `contacts` (pessoas de
     contato) — só nos eventos de atividade da timeline.
  2) Receita recorrente — apaga `assinatura_eventos` (livro-razão de MRR) e `assinaturas`.
     Zera Novo MRR / Expansão / Contração / Churn / NRR.

O que NÃO é tocado (só conferido e impresso): `companies` e `lead_prospects`. As 10
empresas e os 75 leads permanecem intactos.

DRY-RUN por padrão — só imprime o estado atual e o que seria apagado. Para aplicar:
    ... python scripts/preparar_lancamento.py --apply

RECOMENDADO fazer backup antes do --apply:
    docker compose -f docker-compose.prod.yml exec -T db pg_dump -U crm gd_crm | gzip > backup_pre_lancamento.sql.gz

Como rodar (dentro do container `api`, que já tem a DATABASE_URL):
    # preview:
    docker compose -f docker-compose.prod.yml exec api python scripts/preparar_lancamento.py
    # aplicar:
    docker compose -f docker-compose.prod.yml exec api python scripts/preparar_lancamento.py --apply

O usuário `crm` é superusuário e ignora RLS — abrange TODOS os tenants. O dry-run imprime
as contagens por tenant justamente pra você conferir o escopo antes de apagar.
"""
import os
import sys

from sqlalchemy import text

# Permite rodar como `python scripts/x.py` dentro do container: sem isto, só `scripts/`
# entra no sys.path e `import app` falha. Adiciona a raiz do projeto (pai de scripts/).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine  # noqa: E402

# Janela do mês a limpar (contatos). AAAA-MM-DD, meia-noite UTC, fim exclusivo.
INICIO_MES = "2026-08-01"
FIM_MES = "2026-09-01"
TIPOS_CONTATO = ("ligacao", "email")


def _scalar(conn, sql, **params):
    return conn.execute(text(sql), params).scalar() or 0


def _estado_atual(conn) -> None:
    print("=== ESTADO ATUAL (nada apagado ainda) ===\n")

    print("-- Inventário que será MANTIDO --")
    print("  companies (não deletadas), por status:")
    for r in conn.execute(text(
        "SELECT tenant_id, status, COUNT(*) n FROM companies WHERE deleted_at IS NULL "
        "GROUP BY tenant_id, status ORDER BY tenant_id, status"
    )):
        print(f"    tenant {r.tenant_id} | {r.status:<12} {r.n}")
    total_emp = _scalar(conn, "SELECT COUNT(*) FROM companies WHERE deleted_at IS NULL")
    total_leads = _scalar(conn, "SELECT COUNT(*) FROM lead_prospects")
    print(f"  TOTAL empresas ativas: {total_emp} | leads em pesquisa: {total_leads}\n")

    print(f"-- (1) Contatos realizados em {INICIO_MES[:7]} (serão APAGADOS) --")
    for r in conn.execute(text(
        "SELECT tenant_id, tipo, COUNT(*) n, COUNT(DISTINCT company_id) empresas "
        "FROM timeline_events WHERE tipo = ANY(:tipos) "
        "AND created_at >= :ini AND created_at < :fim GROUP BY tenant_id, tipo ORDER BY tenant_id, tipo"
    ), {"tipos": list(TIPOS_CONTATO), "ini": INICIO_MES, "fim": FIM_MES}):
        print(f"    tenant {r.tenant_id} | {r.tipo:<8} {r.n} evento(s), {r.empresas} empresa(s)")
    n_contatos = _scalar(conn,
        "SELECT COUNT(*) FROM timeline_events WHERE tipo = ANY(:tipos) AND created_at >= :ini AND created_at < :fim",
        tipos=list(TIPOS_CONTATO), ini=INICIO_MES, fim=FIM_MES)
    print(f"  TOTAL eventos a apagar: {n_contatos}\n")

    print("-- (2) Receita recorrente (será APAGADA) --")
    for r in conn.execute(text(
        "SELECT tenant_id, status, COUNT(*) n, COALESCE(SUM(valor_mensal),0) mrr "
        "FROM assinaturas GROUP BY tenant_id, status ORDER BY tenant_id, status"
    )):
        print(f"    tenant {r.tenant_id} | {r.status:<10} {r.n} assinatura(s), MRR R$ {r.mrr}")
    n_assin = _scalar(conn, "SELECT COUNT(*) FROM assinaturas")
    n_ev = _scalar(conn, "SELECT COUNT(*) FROM assinatura_eventos")
    print(f"  TOTAL: {n_assin} assinatura(s) + {n_ev} evento(s) de MRR a apagar\n")


def _aplicar(conn) -> None:
    del_ev = conn.execute(text("DELETE FROM assinatura_eventos")).rowcount
    del_as = conn.execute(text("DELETE FROM assinaturas")).rowcount
    del_ct = conn.execute(text(
        "DELETE FROM timeline_events WHERE tipo = ANY(:tipos) AND created_at >= :ini AND created_at < :fim"
    ), {"tipos": list(TIPOS_CONTATO), "ini": INICIO_MES, "fim": FIM_MES}).rowcount
    print(f"  [OK] contatos ({INICIO_MES[:7]}): {del_ct} evento(s) apagado(s)")
    print(f"  [OK] receita recorrente: {del_as} assinatura(s) + {del_ev} evento(s) apagado(s)")


def main() -> None:
    aplicar = "--apply" in sys.argv[1:]

    with engine.connect() as conn:
        _estado_atual(conn)

    if not aplicar:
        print("(DRY-RUN — nada foi apagado. Faça backup e rode com --apply para aplicar.)")
        return

    print("Aplicando (--apply)...")
    with engine.begin() as conn:  # transação única: ou tudo, ou nada
        _aplicar(conn)
    print("\n[CONCLUÍDO] Base pronta para o início da operação.")


if __name__ == "__main__":
    main()
