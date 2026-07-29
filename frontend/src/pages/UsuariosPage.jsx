import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createUser, listUsers, setUserStatus, updateUser } from '../api/users'
import '../styles/dataTable.css'
import './UsuariosPage.css'

const PERFIL_LABEL = { admin: 'Admin', gestor: 'Gestor', vendedor: 'Vendedor', visualizador: 'Visualizador' }

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

  const usersQuery = useQuery({
    queryKey: ['users', 'list', { busca, perfil }],
    queryFn: () => listUsers({ size: 100, busca: busca || undefined, perfil: perfil || undefined }),
    retry: false,
  })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['users'] })
  }

  const createMutation = useMutation({ mutationFn: createUser, onSuccess: () => { setModalUser(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateUser(id, data), onSuccess: () => { setModalUser(undefined); invalidate() } })
  const statusMutation = useMutation({ mutationFn: ({ id, status }) => setUserStatus(id, status), onSuccess: invalidate })

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
        <button className="btn-primary" onClick={() => setModalUser(null)}>+ Novo usuário</button>
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
                    <th>Usuário</th><th>Cargo</th><th>Perfil</th><th>Status</th><th>Último acesso</th><th className="actions-col"></th>
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
                      <td><span className="perfil-pill" data-perfil={u.perfil}><span className="d" />{PERFIL_LABEL[u.perfil] ?? u.perfil}</span></td>
                      <td><span className="status-pill" data-status={u.status}><span className="d" />{u.status === 'ativo' ? 'Ativo' : 'Inativo'}</span></td>
                      <td>{u.ultimo_acesso ? new Date(u.ultimo_acesso).toLocaleString('pt-BR') : '—'}</td>
                      <td className="actions-col">
                        <button className="row-action" title="Editar" onClick={() => setModalUser(u)}>✎</button>
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
                  {items.length === 0 && <tr><td colSpan={6} className="empty-cell">Nenhum usuário encontrado.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {modalUser !== undefined && (
        <UserModal
          user={modalUser}
          onClose={() => setModalUser(undefined)}
          onSubmit={(data) => {
            if (modalUser) updateMutation.mutate({ id: modalUser.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}
    </>
  )
}

function UserModal({ user, onClose, onSubmit, submitting, error }) {
  const isEdit = Boolean(user)
  const [form, setForm] = useState({
    nome: user?.nome ?? '',
    email: user?.email ?? '',
    senha: '',
    telefone: user?.telefone ?? '',
    cargo: user?.cargo ?? '',
    perfil: user?.perfil ?? 'vendedor',
  })

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (isEdit) {
      onSubmit({
        nome: form.nome.trim(),
        telefone: form.telefone.trim() || null,
        cargo: form.cargo.trim() || null,
        perfil: form.perfil,
      })
    } else {
      onSubmit({
        nome: form.nome.trim(),
        email: form.email.trim(),
        senha: form.senha,
        telefone: form.telefone.trim() || null,
        cargo: form.cargo.trim() || null,
        perfil: form.perfil,
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
          <div className="field">
            <label htmlFor="perfil">Perfil *</label>
            <select id="perfil" value={form.perfil} onChange={set('perfil')}>
              {Object.entries(PERFIL_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
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
