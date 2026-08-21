import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createUser, generateResetLink, listUsers, setUserStatus, updateUser } from '../api/users'
import { createTeam, deleteTeam, listTeams, updateTeam } from '../api/teams'
import '../styles/dataTable.css'
import './UsuariosPage.css'

const PERFIL_LABEL = {
  admin: 'Admin', gestor: 'Gestor', vendedor: 'Vendedor',
  prospector: 'Prospector', pesquisador: 'Pesquisador', visualizador: 'Visualizador',
}

function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}

export default function UsuariosPage() {
  const queryClient = useQueryClient()
  const [busca, setBusca] = useState('')
  const [perfil, setPerfil] = useState('')
  const [modalUser, setModalUser] = useState(undefined) // undefined = fechado, null = criar, obj = editar
  const [linkModalUser, setLinkModalUser] = useState(null) // usuário para quem estamos gerando o link de reset
  const [teamsOpen, setTeamsOpen] = useState(false)

  const usersQuery = useQuery({
    queryKey: ['users', 'list', { busca, perfil }],
    queryFn: () => listUsers({ size: 100, busca: busca || undefined, perfil: perfil || undefined }),
    retry: false,
  })
  const teamsQuery = useQuery({ queryKey: ['teams'], queryFn: listTeams, retry: false })
  const teams = teamsQuery.data ?? []

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['users'] })
  }

  const createMutation = useMutation({ mutationFn: createUser, onSuccess: () => { setModalUser(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateUser(id, data), onSuccess: () => { setModalUser(undefined); invalidate() } })
  const statusMutation = useMutation({ mutationFn: ({ id, status }) => setUserStatus(id, status), onSuccess: invalidate })
  const resetLinkMutation = useMutation({ mutationFn: generateResetLink })

  function openResetLink(u) {
    setLinkModalUser(u)
    resetLinkMutation.mutate(u.id)
  }

  function closeResetLink() {
    setLinkModalUser(null)
    resetLinkMutation.reset()
  }

  if (usersQuery.isError) {
    return (
      <>
        <header className="topbar"><div className="topbar-title"><h1>Usuários</h1></div></header>
        <div className="content">
          <p className="state-msg error">Só administradores podem gerenciar usuários.</p>
        </div>
      </>
    )
  }

  const items = usersQuery.data?.items ?? []

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Usuários</h1>
          <p>{items.length.toLocaleString('pt-BR')} usuário(s)</p>
        </div>
        <div className="page-actions">
          <button className="btn-ghost" onClick={() => setTeamsOpen(true)}>👥 Equipes</button>
          <button className="btn-primary" onClick={() => setModalUser(null)}>+ Novo usuário</button>
        </div>
      </header>

      <div className="content">
        <div className="filters-bar">
          <div className="search">
            <input type="text" placeholder="Buscar por nome ou e-mail" value={busca} onChange={(e) => setBusca(e.target.value)} />
          </div>
          <select className="filter-select" value={perfil} onChange={(e) => setPerfil(e.target.value)}>
            <option value="">Todos os perfis</option>
            {Object.entries(PERFIL_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>

        <div className="card">
          {usersQuery.isLoading && <p className="state-msg">Carregando usuários…</p>}
          {usersQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>Usuário</th><th>Cargo</th><th>Equipe</th><th>Perfil</th><th>Status</th><th>Último acesso</th><th className="actions-col"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <div className="row-title">{u.nome}</div>
                        <div className="row-sub">{u.email}</div>
                      </td>
                      <td>{u.cargo ?? '—'}</td>
                      <td>{teams.find((t) => t.id === u.team_id)?.nome ?? '—'}</td>
                      <td><span className="perfil-pill" data-perfil={u.perfil}><span className="d" />{PERFIL_LABEL[u.perfil] ?? u.perfil}</span></td>
                      <td><span className="status-pill" data-status={u.status}><span className="d" />{u.status === 'ativo' ? 'Ativo' : 'Inativo'}</span></td>
                      <td>{u.ultimo_acesso ? new Date(u.ultimo_acesso).toLocaleString('pt-BR') : '—'}</td>
                      <td className="actions-col">
                        <button className="row-action" title="Editar" onClick={() => setModalUser(u)}>✎</button>
                        <button className="row-action" title="Gerar link de redefinição de senha" onClick={() => openResetLink(u)}>🔗</button>
                        <button
                          className="row-action"
                          title={u.status === 'ativo' ? 'Desativar' : 'Ativar'}
                          onClick={() => statusMutation.mutate({ id: u.id, status: u.status === 'ativo' ? 'inativo' : 'ativo' })}
                        >
                          {u.status === 'ativo' ? '⏻' : '✓'}
                        </button>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && <tr><td colSpan={7} className="empty-cell">Nenhum usuário encontrado.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {modalUser !== undefined && (
        <UserModal
          user={modalUser}
          teams={teams}
          onClose={() => setModalUser(undefined)}
          onSubmit={(data) => {
            if (modalUser) updateMutation.mutate({ id: modalUser.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {teamsOpen && (
        <TeamsModal
          teams={teams}
          users={items}
          onClose={() => setTeamsOpen(false)}
          onChanged={() => {
            queryClient.invalidateQueries({ queryKey: ['teams'] })
            queryClient.invalidateQueries({ queryKey: ['users'] })
          }}
        />
      )}

      {linkModalUser && (
        <ResetLinkModal
          user={linkModalUser}
          result={resetLinkMutation.data}
          loading={resetLinkMutation.isPending}
          error={resetLinkMutation.error}
          onClose={closeResetLink}
        />
      )}
    </>
  )
}

function ResetLinkModal({ user, result, loading, error, onClose }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(result.link)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard indisponível (ex.: contexto não seguro) — usuário copia manualmente do campo
    }
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Link de redefinição de senha</h2>
        <p className="reset-link-sub">
          Envie este link para <strong>{user.nome}</strong> por um canal seguro (WhatsApp, etc.). Ele vale por{' '}
          {result ? `${result.expira_em_minutos} minutos` : '…'} e não é enviado automaticamente por e-mail.
        </p>

        {loading && <p className="state-msg">Gerando link…</p>}
        {error && <p className="state-msg error">Não foi possível gerar o link. Tente novamente.</p>}

        {result && (
          <div className="reset-link-box">
            <input type="text" readOnly value={result.link} onFocus={(e) => e.target.select()} />
            <button type="button" className="btn-primary" onClick={copy}>{copied ? 'Copiado!' : 'Copiar'}</button>
          </div>
        )}

        <div className="modal-actions">
          <button type="button" className="btn-ghost" onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  )
}

function UserModal({ user, teams = [], onClose, onSubmit, submitting, error }) {
  const isEdit = Boolean(user)
  const [form, setForm] = useState({
    nome: user?.nome ?? '',
    email: user?.email ?? '',
    senha: '',
    telefone: user?.telefone ?? '',
    cargo: user?.cargo ?? '',
    perfil: user?.perfil ?? 'vendedor',
    team_id: user?.team_id ?? '',
    meta_pesquisa_semanal: user?.meta_pesquisa_semanal ?? '',
    meta_pesquisa_mensal: user?.meta_pesquisa_mensal ?? '',
  })

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    const metas = {
      team_id: form.team_id || null,
      meta_pesquisa_semanal: form.meta_pesquisa_semanal !== '' ? Number(form.meta_pesquisa_semanal) : null,
      meta_pesquisa_mensal: form.meta_pesquisa_mensal !== '' ? Number(form.meta_pesquisa_mensal) : null,
    }
    if (isEdit) {
      onSubmit({
        nome: form.nome.trim(),
        telefone: form.telefone.trim() || null,
        cargo: form.cargo.trim() || null,
        perfil: form.perfil,
        ...metas,
      })
    } else {
      onSubmit({
        nome: form.nome.trim(),
        email: form.email.trim(),
        senha: form.senha,
        telefone: form.telefone.trim() || null,
        cargo: form.cargo.trim() || null,
        perfil: form.perfil,
        ...metas,
      })
    }
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{isEdit ? 'Editar usuário' : 'Novo usuário'}</h2>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="nome">Nome *</label>
            <input id="nome" required value={form.nome} onChange={set('nome')} placeholder="Nome completo" />
          </div>
          <div className="field">
            <label htmlFor="email">E-mail *</label>
            <input id="email" type="email" required value={form.email} onChange={set('email')} disabled={isEdit} placeholder="nome@gdconecta.com.br" />
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="telefone">Telefone</label>
              <input id="telefone" value={form.telefone} onChange={set('telefone')} />
            </div>
            <div className="field">
              <label htmlFor="cargo">Cargo</label>
              <input id="cargo" value={form.cargo} onChange={set('cargo')} placeholder="Ex.: Executivo de Vendas" />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="perfil">Perfil *</label>
              <select id="perfil" value={form.perfil} onChange={set('perfil')}>
                {Object.entries(PERFIL_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="team_id">Equipe</label>
              <select id="team_id" value={form.team_id} onChange={set('team_id')}>
                <option value="">Sem equipe</option>
                {teams.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
              </select>
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="meta_semanal">Meta de pesquisa semanal</label>
              <input id="meta_semanal" type="number" min="0" value={form.meta_pesquisa_semanal} onChange={set('meta_pesquisa_semanal')} placeholder="Ex.: 20" />
            </div>
            <div className="field">
              <label htmlFor="meta_mensal">Meta de pesquisa mensal</label>
              <input id="meta_mensal" type="number" min="0" value={form.meta_pesquisa_mensal} onChange={set('meta_pesquisa_mensal')} placeholder="Ex.: 80" />
            </div>
          </div>
          {!isEdit && (
            <div className="field">
              <label htmlFor="senha">Senha temporária *</label>
              <input id="senha" required minLength={8} value={form.senha} onChange={set('senha')} placeholder="Mínimo 8 caracteres" />
            </div>
          )}

          {error && (
            <p className="state-msg error">
              {error.response?.data?.error?.message ?? 'Não foi possível salvar. Confira os dados e tente de novo.'}
            </p>
          )}

          <div className="modal-actions">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function TeamsModal({ teams, users, onClose, onChanged }) {
  const [novoNome, setNovoNome] = useState('')
  const [novoGestor, setNovoGestor] = useState('')
  const [erro, setErro] = useState(null)

  // Elegíveis a gestor: admins e gestores.
  const gestores = users.filter((u) => u.perfil === 'gestor' || u.perfil === 'admin')

  const createMutation = useMutation({
    mutationFn: () => createTeam({ nome: novoNome.trim(), gestor_id: novoGestor || null }),
    onSuccess: () => { setNovoNome(''); setNovoGestor(''); setErro(null); onChanged() },
    onError: () => setErro('Não foi possível criar a equipe.'),
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updateTeam(id, data),
    onSuccess: onChanged,
  })
  const deleteMutation = useMutation({
    mutationFn: (id) => deleteTeam(id),
    onSuccess: onChanged,
  })

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Equipes</h2>
        <p className="sub">A meta de uma equipe é a soma das metas dos seus vendedores. Excluir uma equipe apenas desliga os vendedores (não remove ninguém).</p>

        <div className="teams-list">
          {teams.length === 0 && <p className="state-msg">Nenhuma equipe cadastrada ainda.</p>}
          {teams.map((t) => (
            <div className="team-item" key={t.id}>
              <input
                className="f-input" defaultValue={t.nome}
                onBlur={(e) => { if (e.target.value.trim() && e.target.value.trim() !== t.nome) updateMutation.mutate({ id: t.id, data: { nome: e.target.value.trim() } }) }}
              />
              <select
                className="f-input" value={t.gestor_id ?? ''}
                onChange={(e) => updateMutation.mutate({ id: t.id, data: { gestor_id: e.target.value || null } })}
              >
                <option value="">Sem gestor</option>
                {gestores.map((g) => <option key={g.id} value={g.id}>{g.nome}</option>)}
              </select>
              <button className="row-action" title="Excluir equipe" onClick={() => deleteMutation.mutate(t.id)}>🗑</button>
            </div>
          ))}
        </div>

        <div className="team-new">
          <input className="f-input" placeholder="Nome da nova equipe" value={novoNome} onChange={(e) => setNovoNome(e.target.value)} />
          <select className="f-input" value={novoGestor} onChange={(e) => setNovoGestor(e.target.value)}>
            <option value="">Sem gestor</option>
            {gestores.map((g) => <option key={g.id} value={g.id}>{g.nome}</option>)}
          </select>
          <button className="btn-primary" disabled={!novoNome.trim() || createMutation.isPending} onClick={() => createMutation.mutate()}>
            + Criar
          </button>
        </div>

        {erro && <p className="state-msg error">{erro}</p>}

        <div className="modal-actions">
          <button type="button" className="btn-ghost" onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  )
}
