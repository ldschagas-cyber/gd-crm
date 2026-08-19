"""Mescla empresas duplicadas em `companies` (Problema descoberto via Metas do Funil:
Adium com 4 cópias, Connectoway com 3). A duplicação vinha de LeadProspectService.promote()
criar Company nova sem deduplicar — já corrigido; este script limpa o passado.

Duas fontes de grupos a mesclar:

1) AUTOMÁTICO — agrupa por (tenant_id, dedupe_key), o mesmo `dedupe_key` de app/core/text.py
   que a cascata de dedupe do app usa. Ele é CONSERVADOR: normaliza acento/pontuação e
   remove só naturezas jurídicas (ltda/me/epp/eireli/sa). Logo, casa nomes normalizados
   IDÊNTICOS (ex.: "Adium" ×4, "ZARAPLAST" vs "Zaraplast"), mas NÃO casa variações de razão
   social — "Connectoway" e "Connectoway Solucoes Inteligentes em Tecnologia S.A" têm chaves
   diferentes e ficam em grupos separados (casar por "primeira palavra" geraria falso
   positivo na base inteira, então não fazemos isso automaticamente).

2) MANUAL — a lista MANUAL_MERGES abaixo, para os casos cross-nome que o item 1 não pega.
   Cada entrada fixa o id canônico e os ids a mesclar nele. Ids listados aqui são removidos
   do passe automático (a decisão manual vence).

Para cada grupo (automático ou manual):
  - canônico automático = o registro mais "rico" (mais linhas-filhas somadas nas 12 tabelas
    com FK para companies.id); empate -> o mais antigo. No manual, o canônico é o que você fixou.
  - repointa as 12 tabelas-filhas para o canônico.
  - soft-delete dos duplicados (deleted_at = now()) — reversível, consistente com o
    SoftDeleteMixin do model. NÃO faz hard delete.

DRY-RUN por padrão: só imprime o plano, não grava nada. Para aplicar de verdade:
    ... python scripts/merge_duplicate_companies.py --apply

Como rodar em produção (dentro do container `api`, que já tem a DATABASE_URL):
    # preview (não grava nada):
    docker compose -f docker-compose.prod.yml exec api python scripts/merge_duplicate_companies.py
    # aplicar:
    docker compose -f docker-compose.prod.yml exec api python scripts/merge_duplicate_companies.py --apply

O usuário `crm` do Postgres é superusuário e ignora RLS, então abrange todos os tenants de
uma vez. O agrupamento automático é sempre por tenant_id — nunca funde tenants diferentes;
o manual valida que todos os ids do grupo são do mesmo tenant antes de mesclar.
"""
import os
import sys
from collections import defaultdict
from uuid import UUID

from sqlalchemy import text

# Permite rodar como `python scripts/x.py` dentro do container: sem isto, só `scripts/`
# entra no sys.path e `import app` falha. Adiciona a raiz do projeto (pai de scripts/).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine  # noqa: E402
from app.core.text import dedupe_key  # noqa: E402

# (tabela, coluna FK) — as 12 referências a companies.id levantadas via information_schema.
# Manter em sincronia se novas tabelas passarem a referenciar companies.id.
FK_TABLES = [
    ("contacts", "company_id"),
    ("lead_prospects", "promoted_company_id"),
    ("site_visits", "company_id"),
    ("deals", "company_id"),
    ("form_submissions", "company_id"),
    ("timeline_events", "company_id"),
    ("tasks", "company_id"),
    ("calls", "company_id"),
    ("sequence_enrollments", "company_id"),
    ("activity_sla_milestone_hits", "company_id"),
    ("assinaturas", "company_id"),
    ("onboarding_checklist_items", "company_id"),
]

# Mesclagens manuais para casos cross-nome que o dedupe_key (conservador) não agrupa.
# Formato: (id_canonico, [id_duplicado, ...]). Todos precisam existir, estar ativos e ser
# do mesmo tenant. Revise SEMPRE no dry-run antes de aplicar.
#
# Connectoway: o registro rico (nome completo, mais antigo, 10 cs_checkin + 8 pipeline) é o
# canônico; os dois "Connectoway" curtos entram nele.
MANUAL_MERGES: list[tuple[str, list[str]]] = [
    (
        "65a27e12-7c44-4d01-a860-4fb9388bb920",
        ["864c2ea9-f67f-40fa-b027-2822f87178ae", "fa3d393f-6936-46a3-8764-c282a3951fcd"],
    ),
]


def _load_child_counts(conn) -> dict:
    """{(tabela, coluna): {company_id: qtd}} — quantas linhas cada empresa tem em cada
    tabela-filha. Uma varredura agregada por tabela, barato mesmo com a base inteira."""
    counts: dict = {}
    for tabela, coluna in FK_TABLES:
        rows = conn.execute(
            text(f"SELECT {coluna} AS cid, COUNT(*) AS n FROM {tabela} "
                 f"WHERE {coluna} IS NOT NULL GROUP BY {coluna}")
        ).fetchall()
        counts[(tabela, coluna)] = {r.cid: r.n for r in rows}
    return counts


def _total_filhos(company_id, child_counts) -> int:
    return sum(tbl.get(company_id, 0) for tbl in child_counts.values())


def _grupos(conn):
    """Retorna (grupos, child_counts). Cada grupo = (rotulo, membros[canônico primeiro]).
    Combina os grupos manuais (MANUAL_MERGES) e os automáticos (por dedupe_key), com os ids
    manuais removidos do passe automático."""
    companies = conn.execute(text(
        "SELECT id, tenant_id, razao_social, cnpj, created_at FROM companies "
        "WHERE deleted_at IS NULL"
    )).fetchall()
    child_counts = _load_child_counts(conn)
    por_id = {c.id: c for c in companies}

    grupos = []
    ids_manuais: set = set()

    # --- grupos manuais primeiro ---
    for canon_str, dup_strs in MANUAL_MERGES:
        canon_id = UUID(canon_str)
        dup_ids = [UUID(s) for s in dup_strs]
        membros_ids = [canon_id, *dup_ids]
        faltando = [i for i in membros_ids if i not in por_id]
        if faltando:
            print(f"[AVISO] mesclagem manual ignorada — id(s) inexistente(s)/já deletado(s): "
                  f"{', '.join(str(i) for i in faltando)}")
            continue
        tenants = {por_id[i].tenant_id for i in membros_ids}
        if len(tenants) > 1:
            print(f"[AVISO] mesclagem manual ignorada — ids de tenants diferentes: {canon_str}")
            continue
        ids_manuais.update(membros_ids)
        membros = [por_id[canon_id]] + [por_id[i] for i in dup_ids]  # canônico fixo, na ordem dada
        grupos.append((f"manual:{por_id[canon_id].razao_social}", membros))

    # --- grupos automáticos por dedupe_key ---
    por_chave: dict = defaultdict(list)
    for c in companies:
        if c.id in ids_manuais:
            continue  # já tratado manualmente
        key = dedupe_key(c.razao_social)
        if not key:  # nome vazio/inutilizável — nunca agrupa
            continue
        por_chave[(c.tenant_id, key)].append(c)

    for (tenant_id, key), membros in por_chave.items():
        if len(membros) < 2:
            continue
        # canônico = mais filhos; empate -> mais antigo; desempate final -> id (determinístico)
        membros.sort(key=lambda c: (-_total_filhos(c.id, child_counts), c.created_at, str(c.id)))
        grupos.append((f"auto:{key}", membros))

    # grupos com mais duplicatas primeiro, só pra leitura
    grupos.sort(key=lambda g: -len(g[1]))
    return grupos, child_counts


def _imprimir_plano(grupos, child_counts) -> tuple[int, int]:
    total_dups = 0
    total_linhas = 0
    for rotulo, membros in grupos:
        canonico, *dups = membros
        total_dups += len(dups)
        print(f"\n=== {rotulo} — {len(membros)} registros (tenant {canonico.tenant_id}) ===")
        print(f"  CANÔNICO  {canonico.id}  {canonico.razao_social!r}  "
              f"criado={canonico.created_at:%Y-%m-%d}  filhos={_total_filhos(canonico.id, child_counts)}")
        for d in dups:
            print(f"  mescla ->  {d.id}  {d.razao_social!r}  "
                  f"criado={d.created_at:%Y-%m-%d}  filhos={_total_filhos(d.id, child_counts)}")
        dup_ids = [d.id for d in dups]
        for (tabela, coluna), tbl in child_counts.items():
            movidas = sum(tbl.get(did, 0) for did in dup_ids)
            if movidas:
                total_linhas += movidas
                print(f"      {tabela}.{coluna}: {movidas} linha(s) repointada(s)")
    return total_dups, total_linhas


def _aplicar(conn, grupos) -> None:
    """Repointa filhas e soft-delete dos duplicados — tudo na transação do caller."""
    for rotulo, membros in grupos:
        canonico, *dups = membros
        dup_ids = [d.id for d in dups]
        for tabela, coluna in FK_TABLES:
            conn.execute(
                text(f"UPDATE {tabela} SET {coluna} = :canon WHERE {coluna} = ANY(:dups)"),
                {"canon": canonico.id, "dups": dup_ids},
            )
        conn.execute(
            text("UPDATE companies SET deleted_at = now() WHERE id = ANY(:dups)"),
            {"dups": dup_ids},
        )
        print(f"  [OK] {rotulo}: {len(dups)} duplicado(s) mesclado(s) em {canonico.id}")


def main() -> None:
    aplicar = "--apply" in sys.argv[1:]

    # Leitura numa conexão só-leitura; os Rows vêm materializados por fetchall(), então
    # continuam válidos depois que a conexão fecha.
    with engine.connect() as conn:
        grupos, child_counts = _grupos(conn)

    if not grupos:
        print("Nenhuma empresa duplicada encontrada. Nada a fazer.")
        return

    total_dups, total_linhas = _imprimir_plano(grupos, child_counts)
    print(f"\n{'='*60}")
    print(f"RESUMO: {len(grupos)} grupo(s) | {total_dups} duplicado(s) a mesclar | "
          f"{total_linhas} linha(s)-filha(s) a repointar.")

    if not aplicar:
        print("\n(DRY-RUN — nada foi gravado. Rode com --apply para aplicar.)")
        return

    print("\nAplicando (--apply)...")
    with engine.begin() as conn:  # transação única: ou tudo, ou nada
        _aplicar(conn, grupos)
    print("\n[CONCLUÍDO] Mesclagem aplicada com sucesso.")


if __name__ == "__main__":
    main()
