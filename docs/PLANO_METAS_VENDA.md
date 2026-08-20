# Plano — Metas de Venda e Metas de Ligações

Duas melhorias de acompanhamento de meta por pessoa, distintas das **Metas do Funil**
(que são do tenant inteiro, por percentual de fase — ver `PLANO_METAS_FUNIL.md`).

## 1. Meta de Venda (quantidade e valor) por equipe e vendedor

### Modelo de dados
- **`teams`** (`app/models/team.py`) — equipe de vendas: `nome`, `gestor_id` (FK
  users, opcional). Hierarquia **gestor → equipe → vendedores**; um tenant tem
  várias equipes.
- **`users.team_id`** — liga o vendedor à equipe (nullable; `None` = sem equipe).
- **`sales_targets`** (`app/models/sales_target.py`) — meta por vendedor por mês:
  `user_id`, `mes` (`AAAA-MM`), `meta_qtd`, `meta_valor`. Único por
  `(tenant, user, mes)`. **A meta muda mês a mês** — por isso é tabela, não coluna.

### Regras
- **Meta da equipe = soma** das metas dos vendedores da equipe naquele mês. Não é
  armazenada.
- **Realizado é lido ao vivo**, no mesmo espírito das Metas do Funil: negócios com
  `status=ganho` e `data_fechamento` dentro do mês, agrupados por `responsavel_id`
  (quantidade e soma de `valor_previsto`). Nada de escrita manual do realizado.
- **Status** de cada indicador (qtd/valor) contra a meta: `ok` ≥ 100%, `atencao`
  ≥ 70%, `critico` abaixo. Sem meta definida → sem status.

### Camadas
- Serviço `app/services/metas_venda.py` (`MetasVendaService.resumo(mes)` /
  `set_targets(mes, items)`), espelhando `funil_metas.py`.
- API `app/api/v1/metas_venda.py` (`GET /metas-venda/resumo`, `PUT
  /metas-venda/targets`) — restrito a admin/gestor.
- Equipes: `app/services/team.py` + `app/api/v1/teams.py` (CRUD; criação/edição
  restrita a admin, listagem liberada pra popular seletores).
- Frontend: `MetasVendaPage.jsx` (dashboard + drawer de edição das metas do mês) e
  gerenciamento de equipes + seleção de equipe no cadastro de usuário
  (`UsuariosPage.jsx`).

## 2. Meta de Ligações (semana e mês) por vendedor

- Meta **fixa** por semana/mês, colunas em `users`
  (`meta_ligacoes_semanal/mensal`), no mesmo molde de `meta_pesquisa_*`.
- **Realizado = tarefas `tipo=ligacao` concluídas** por vendedor (mesma fonte que o
  dashboard do vendedor já usa) — não usa `Call` do Twilio nem `TimelineEvent`,
  evitando dependência de Twilio e contagem dupla. Progresso sempre relativo a
  "agora" (semana e mês correntes).
- Serviço `app/services/metas_ligacoes.py`, API `app/api/v1/metas_ligacoes.py`
  (`GET /metas-ligacoes/progresso`, admin/gestor), tela `MetasLigacoesPage.jsx`. A
  meta é definida no cadastro de usuário.

## Notas de implementação
- Tabelas novas (`teams`, `sales_targets`) não têm política RLS no Postgres (só as
  10 iniciais têm) — isolamento pela aplicação via `TenantMixin` + `BaseRepository`.
- Migração `d9e1f3a5c7b2` — rodar `alembic heads` antes do deploy (PRs paralelos
  podem divergir).
