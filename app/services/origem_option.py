"""Serviço de opções de Origem.

As opções "de fábrica" (`ORIGENS_PADRAO`) ficam sempre disponíveis mesmo sem
nenhuma linha gravada — a tabela `origem_options` só guarda as opções extras que
o próprio tenant cadastrou (via "+ Criar nova opção…" no formulário de Empresa/
Pesquisa de Leads). `list()` devolve a união das duas, sem duplicar.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.origem_option import OrigemOption
from app.repositories.origem_option import OrigemOptionRepository
from app.schemas.origem_option import OrigemOptionCreate

# União das duas listas fixas que existiam duplicadas em EmpresasPage.jsx (ORIGENS_EMPRESA)
# e PesquisaLeadsPage.jsx (ORIGENS) — vira só o conjunto default agora, editável por tenant.
ORIGENS_PADRAO = [
    "Feira", "Indicação", "Campanha", "Prospecção ativa", "LinkedIn",
    "Site institucional", "Formulário do site", "Pesquisa de Leads", "Outro",
]


class OrigemOptionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OrigemOptionRepository(db)

    def list(self) -> list[str]:
        vistas = {n.lower() for n in ORIGENS_PADRAO}
        extras = [o.nome for o in self.repo.list_all() if o.nome.lower() not in vistas]
        return ORIGENS_PADRAO + extras

    def create(self, data: OrigemOptionCreate) -> OrigemOption:
        nome = data.nome.strip()
        if not nome:
            raise ConflictError("Informe um nome para a nova origem")
        if nome.lower() in {n.lower() for n in ORIGENS_PADRAO}:
            raise ConflictError(f'"{nome}" já existe na lista de origens')
        if self.repo.get_by_nome(nome):
            raise ConflictError(f'"{nome}" já existe na lista de origens')
        return self.repo.add(OrigemOption(nome=nome))
