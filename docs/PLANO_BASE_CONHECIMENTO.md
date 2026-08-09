# Plano — Base de Conhecimento (Playbooks)

Status: **proposta, não implementada**. Protótipo funcional em
[`docs/prototypes/base_conhecimento_prototype.html`](prototypes/base_conhecimento_prototype.html).

## 0. Problema e decisões travadas

Hoje o conhecimento comercial (como abordar, o que responder a uma objeção, qual case citar)
mora na cabeça de quem já vende há mais tempo. Isso trava a empresa quando alguém sai de
férias, muda de time ou desliga — e torna o onboarding de vendedor novo lento e dependente de
"sombra" com o time sênior.

1. **É conteúdo, não automação** — não é um novo tipo de e-mail/sequência disparado
   automaticamente. É material de consulta que o vendedor lê antes/durante uma conversa.
   Por isso não entra no grupo "Automação" do menu (Sequências, Workflows, Modelos de
   e-mail, Snippets) nem reaproveita a tabela de `EmailTemplate` — tem ciclo de vida e dono
   diferente (curadoria de gestão comercial, não disparo).
2. **Curadoria centralizada, leitura livre** — qualquer perfil lê; só `admin`/`gestor`
   publicam e editam (mesmo padrão de `Pipelines` — `require_roles(ADMIN, GESTOR)` em
   [`app/api/v1/pipelines.py:17`](../app/api/v1/pipelines.py)). Vendedor pode **sugerir**
   conteúdo (rascunho) e **avaliar** o que já existe ("isso ajudou?"), mas não publica sem
   revisão — sem isso a base vira depósito de texto não confiável.
3. **Vive dentro do fluxo de trabalho, não só numa página isolada** — a causa mais comum de
   base de conhecimento morta é ela ficar num canto que ninguém abre. Por isso a Fase 2 injeta
   o conteúdo relevante (por setor) direto no Dossiê Comercial da empresa
   ([`CompanyDossierPage.jsx`](../frontend/src/pages/CompanyDossierPage.jsx)), onde o vendedor
   já está olhando antes de ligar — ele não precisa lembrar que a base existe.
4. **Combate ao conteúdo esquecido** — todo artigo tem um selo "sem revisão há N dias"
   calculado a partir de `atualizado_em`; não é auditoria pesada, é só visibilidade de que
   aquele script pode estar desatualizado. Sem isso, em 1 ano a base acumula scripts obsoletos
   e ninguém percebe.

## 1. Modelo de dados

Tabela nova, aditiva — não mexe em nada existente.

### `PlaybookArticle` (`app/models/playbook.py`, novo arquivo)

```python
class PlaybookCategoria(str, enum.Enum):
    PROCESSO = "processo"       # Processo comercial — etapas, SLAs, "o que fazer em cada fase"
    SCRIPT = "script"           # Scripts de abordagem (ligação, e-mail, WhatsApp)
    OBJECAO = "objecao"         # Objeção + como responder
    CASE = "case"                # Case de cliente real — problema, solução, resultado
    METODOLOGIA = "metodologia" # Framework de venda (qualificação, descoberta, etc.)


class PlaybookStatus(str, enum.Enum):
    RASCUNHO = "rascunho"   # sugerido por qualquer perfil, ainda não publicado
    PUBLICADO = "publicado" # visível pra todo mundo
    ARQUIVADO = "arquivado" # fora de uso, mas mantido pro histórico


class PlaybookArticle(Base, TenantMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "playbook_articles"

    id: Mapped[uuid.UUID] = uuid_pk()
    categoria: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=PlaybookStatus.RASCUNHO.value, index=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    resumo: Mapped[str | None] = mapped_column(String(240))  # subtítulo, aparece no card
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)  # texto com markdown leve (**negrito**, listas com "- ")

    # Contextualização — mesma taxonomia de setor já usada no ICP (LeadProspect/Company.setor).
    # None = artigo geral, vale pra qualquer setor.
    setor: Mapped[str | None] = mapped_column(String(80), index=True)

    # Tags livres separadas por vírgula (mesmo espírito simples do atalho de Snippet) — filtro
    # complementar ao setor/categoria, ex.: "frete,rodoviário,farma".
    tags: Mapped[str | None] = mapped_column(String(255))

    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # ordenação manual dentro da categoria

    util_positivo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    util_negativo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visualizacoes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
```

- `status` separa "rascunho sugerido" de "publicado" sem precisar de uma segunda tabela de
  aprovação — mesmo princípio de `DealStatus`/`CompanyStatus`: um campo simples de string.
- `PlaybookVote` **não** vira tabela própria nesta fase — `util_positivo`/`util_negativo` são
  contadores agregados (sem rastrear quem votou); é o suficiente pra sinalizar "isso está
  ajudando" sem o custo de mais uma tabela + endpoint de auditoria de voto individual.
- Sem coluna dedicada de "próxima revisão": o alerta de staleness é só `updated_at` (herdado de
  `TimestampMixin`) comparado com hoje — mais simples que pedir pro autor lembrar de preencher
  uma data.

### Migração Alembic
Revisão nova em `alembic/versions/`, criando a tabela `playbook_articles` com os índices em
`tenant_id`, `categoria`, `status`, `setor` (mesmo padrão das tabelas existentes — ver
`alembic/versions/` para o modelo de migração usado em `snippets`/`companies`).

## 2. Backend

Domínio novo, seguindo o padrão de `Snippet` (repository + service + schema + router próprios,
ver [`app/services/snippet.py`](../app/services/snippet.py) e
[`app/api/v1/snippets.py`](../app/api/v1/snippets.py) como referência direta de estrutura):

- `app/repositories/playbook.py`, `app/services/playbook.py`, `app/schemas/playbook.py`,
  `app/api/v1/playbooks.py`.

### Endpoints

| Rota | Quem pode | Descrição |
|---|---|---|
| `GET /playbooks?categoria=&setor=&status=&busca=` | Todos | Lista com filtro; vendedor só vê `status=publicado` por padrão (gestor/admin veem rascunhos também) |
| `GET /playbooks/{id}` | Todos (se publicado) | Detalhe; incrementa `visualizacoes` |
| `POST /playbooks` | Todos | Cria — se `perfil` for vendedor/visualizador, força `status=rascunho`; admin/gestor pode criar já `publicado` |
| `PATCH /playbooks/{id}` | Dono do rascunho ou admin/gestor | Edita conteúdo |
| `PATCH /playbooks/{id}/status` | admin/gestor (`require_roles`, igual `pipelines.py`) | Publica / arquiva / devolve pra rascunho |
| `DELETE /playbooks/{id}` | admin/gestor | Soft delete |
| `POST /playbooks/{id}/feedback` | Todos | `{ util: true \| false }` — incrementa contador, sem gravar quem votou |
| `GET /playbooks/resumo` | Todos | Contagem por categoria, total, "sem revisão há +90 dias" — alimenta o stat-strip |
| `GET /playbooks/sugeridos?setor=X` | Todos | Atalho usado pelo Dossiê Comercial (Fase 2): top N publicados daquele setor + gerais, por categoria |

## 3. Frontend

### Página principal — `PlaybooksPage.jsx`
Reaproveita quase 100% de CSS já existente (`dataTable.css`, padrões de `drawer`/`scrim`,
`SnippetsPage.jsx` como esqueleto de CRUD):

- Menu novo: grupo **"Capacitação"** em
  [`AppShell.jsx`](../frontend/src/layouts/AppShell.jsx) — não cabe em "Automação" (que é sobre
  disparo automático) nem em "Inteligência Comercial" (que é sobre prospecção); é uma categoria
  própria, com espaço pra crescer (ex.: treinamentos, no-shows de onboarding) depois. Item único
  por enquanto: "Base de Conhecimento".
- Topo: abas de categoria (Todos, Processo Comercial, Scripts, Objeções, Cases, Metodologia) +
  busca + filtro de setor + stat-strip (total, por categoria, "N sem revisão").
- Grid de cards (não tabela — conteúdo de leitura, cartão com título/resumo/setor/selo de
  categoria/👍 combina mais que linha de tabela). Clique abre o artigo num drawer largo com o
  conteúdo renderizado (markdown leve, função própria de 20 linhas — sem nova dependência,
  mesmo espírito do resto do frontend, que não usa nenhuma lib de rich text hoje).
- Botão "+ Novo artigo" visível pra todos; se quem cria não é admin/gestor, o rascunho some da
  visão geral e aparece só em "Meus rascunhos" até alguém publicar — dá caminho pro vendedor
  contribuir sem virar bagunça.
- admin/gestor veem fila "Rascunhos pendentes" (badge no topo) pra revisar sugestões do time.

### Integração contextual — Fase 2, `CompanyDossierPage.jsx`
Novo bloco "📘 Playbook sugerido" logo após a seção "Perfil de encaixe (ICP)"
([`CompanyDossierPage.jsx:184`](../frontend/src/pages/CompanyDossierPage.jsx)), usando
`company.setor` pra puxar `GET /playbooks/sugeridos?setor=...`: até 2 scripts de abordagem +
até 2 objeções comuns do setor + 1 case, cada um como card compacto que abre o mesmo drawer de
leitura. É o que faz a base ser usada de verdade — aparece exatamente onde o vendedor já está
antes de ligar, em vez de depender de ele lembrar de ir num menu separado.

## 4. Fora de escopo desta primeira fase

- Sem editor rich-text/WYSIWYG — markdown leve em textarea (negrito, listas), como o resto do
  CRM já faz com campo de texto livre (`problemas_encontrados`, `hipoteses` em Company).
- Sem versionamento/histórico de edições (quem mudou o quê, diff) — só `updated_by`/`updated_at`
  simples. Se virar necessidade real, é extensão futura análoga a `TimelineEvent`.
- Sem tabela de voto individual (`PlaybookVote`) — só contador agregado.
- Sem geração de conteúdo por IA nesta fase — é curadoria humana. (Poderia entrar depois como
  "sugerir rascunho de objeção a partir de negócios perdidos com esse `motivo_perda`", mas isso
  é uma Fase 3 separada, não bloqueia o MVP.)
- Sem permissão granular por setor/time (ex.: só o time Farma edita playbook de Farma) — todo
  admin/gestor do tenant pode editar qualquer artigo.

## 5. Sequenciamento sugerido

1. Migração (`playbook_articles`) + modelo + repository/service/schema/router (CRUD básico,
   sem feedback/resumo ainda).
2. `PlaybooksPage.jsx` (grid + drawer de leitura/edição) + item de menu "Capacitação".
3. Fluxo de rascunho→publicado (perfis, fila de revisão) + feedback útil/não útil.
4. `GET /playbooks/resumo` (stat-strip, selo de staleness).
5. Fase 2: `GET /playbooks/sugeridos` + bloco no Dossiê Comercial.
6. QA: nenhuma tela existente muda de comportamento (é 100% aditivo — novo domínio, novo menu).
