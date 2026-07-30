"""Seed da tabela de referência CNAE (app/data/cnae_hierarquia.csv, fonte IBGE/Concla).

Uso:
    python -m app.seed_cnae

Idempotente (upsert por código) — pode rodar de novo se o CSV for atualizado.
"""
import csv
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal
from app.models.cnae_code import CnaeCode

CSV_PATH = Path(__file__).parent / "data" / "cnae_hierarquia.csv"


def run() -> None:
    db = SessionLocal()
    try:
        with CSV_PATH.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            print("CSV vazio, nada a fazer:", CSV_PATH)
            return

        stmt = insert(CnaeCode).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["codigo"],
            set_={
                "descricao": stmt.excluded.descricao,
                "secao": stmt.excluded.secao,
                "divisao": stmt.excluded.divisao,
                "grupo": stmt.excluded.grupo,
                "classe": stmt.excluded.classe,
            },
        )
        db.execute(stmt)
        db.commit()
        print(f"{len(rows)} códigos CNAE aplicados (upsert).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
