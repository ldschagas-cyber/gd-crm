import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getMetasLigacoesProgresso, setMetasLigacoesTargets } from '../api/metasLigacoes'
import { listUsers } from '../api/users'
import { listTeams } from '../api/teams'
import '../styles/dataTable.css'
import './MetasLigacoesPage.css'

const PERFIL_LABEL = {
  admin: 'Admin', gestor: 'Gestor', vendedor: 'Vendedor',
  prospector: 'Prospector', pesquisador: 'Pesquisador', visualizador: 'Visualizador',
}
const PERFIS_VENDA = ['vendedor', 'gestor', 'prospector', 'pesquisador']

function pct(atual, meta) {
  if (!meta) return null
  return Math.round((atual / meta) * 100)
}
function statusClass(p) {
  if (p == null) return ''
  if (p >= 100) return 'ok'
  if (p >= 70) return 'atencao'
  return 'critico'
}
function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}
function mesOptions() {
  const options = []
  const now = new Date()
  for (let i = 0; i < 12; i += 1) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const label = d.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
    options.push({ value, label: label.charAt(0).toUpperCase() + label.slice(1) })
  }
  return options
}

function LigBar({ label, atual, meta }) {
  const p = pct(atual, meta)
  return (
    <div className="lig-bar">
      <span className="lig-bar-label">{label}</span>
      {meta ? (
        <>
          <div className="lig-track">
            <div className={`lig-fill ${statusClass(p)}`} style={{ width: `${Math.min(100, p)}%` }} />
          </div>
          <span className={`lig-pill ${statusClass(p)}`}>{atual}/{meta}</span>
        </>
      ) : (
        <span className="lig-nogoal">{atual} ligaç{atual === 1 ? 'ão' : 'ões'} · sem meta definida</span>
      )}
    </div>
  )
}

export default function MetasLigacoesPage() {
  const queryClient = useQueryClient()
  const options = useMemo(mesOptions, [])
  const [mes, setMes] = useState(options[0].value)
  const [editOpen, setEditOpen] = useState(false)

  const query = useQuery({
    queryKey: ['metas-ligacoes', mes],
    queryFn: () => getMetasLigacoesProgresso(mes),
    retry: false,
  })

  if (query.isError) {
    return (
      <>
        <header className="topbar"><div className="topbar-title"><h1>Metas de Ligações</h1></div></header>
        <div className="content"><p className="state-msg error">Só administradores e gestores podem ver este controle.</p></div>
      </>
    )
  }

  const data = query.data
  const rows = data?.rows ?? []
  const mesCorrente = data?.mes_corrente
  const mesLabel = options.find((o) => o.value === mes)?.label ?? mes
  const totalSemana = rows.reduce((a, r) => a + r.ligacoes_semana, 0)
  const totalMes = rows.reduce((a, r) => a + r.ligacoes_mes, 0)

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Metas de Ligações</h1>
          <p>Meta por mês (semanal e mensal) por vendedor — realizado = tarefas de ligação concluídas</p>
        </div>
        <div className="page-actions">
          <button className="btn-ghost" onClick={() => setEditOpen(true)}>⚙ Editar metas</button>
        </div>
      </header>

      <div className="content">
        <div className="filters-bar">
          <select className="filter-select" value={mes} onChange={(e) => setMes(e.target.value)}>
            {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <span className="lig-hint">
            {mesCorrente
              ? 'Mês corrente — mostra o progresso da semana atual e do mês.'
              : 'Mês passado — só o total do mês (a "semana atual" pertence ao mês corrente).'}
          </span>
        </div>

        {query.isLoading ? (
          <p className="state-msg">Carregando…</p>
        ) : (
          <>
            <div className="stat-strip">
              {mesCorrente && (
                <div className="stat-tile"><div className="t">Ligações na semana</div><div className="v">{totalSemana}</div></div>
              )}
              <div className="stat-tile"><div className="t">Ligações no mês</div><div className="v">{totalMes}</div></div>
              <div className="stat-tile"><div className="t">Vendedores ativos</div><div className="v">{rows.length}</div></div>
            </div>

            {rows.length === 0 ? (
              <div className="card"><p className="state-msg">Nenhuma meta definida e nenhuma ligação em {mesLabel.toLowerCase()}. Use "Editar metas" para definir as metas do mês.</p></div>
            ) : (
              <div className="card">
                <div className="card-head">
                  <div>
                    <h3>Progresso por vendedor</h3>
                    <p>{mesCorrente ? 'Semana atual e mês corrente.' : `Total de ${mesLabel.toLowerCase()}.`} Realizado atualiza conforme as tarefas de ligação são concluídas.</p>
                  </div>
                </div>
                <div className="card-body">
                  {rows.map((r) => (
                    <div className="lig-row" key={r.user_id}>
                      <div className="row-resp">
                        <span className="avatar">{initials(r.nome)}</span>
                        <span>{r.nome}</span>
                        <span className={`lig-role lig-role-${r.perfil}`}>{PERFIL_LABEL[r.perfil] ?? r.perfil}</span>
                      </div>
                      <div className="lig-bars">
                        {mesCorrente && <LigBar label="Semana" atual={r.ligacoes_semana} meta={r.meta_semanal} />}
                        <LigBar label="Mês" atual={r.ligacoes_mes} meta={r.meta_mensal} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {editOpen && (
        <EditTargetsDrawer
          mes={mes}
          mesLabel={mesLabel}
          progresso={data}
          onClose={() => setEditOpen(false)}
          onSaved={() => {
            queryClient.invalidateQueries({ queryKey: ['metas-ligacoes'] })
            setEditOpen(false)
          }}
        />
      )}
    </>
  )
}

function EditTargetsDrawer({ mes, mesLabel, progresso, onClose, onSaved }) {
  const usersQuery = useQuery({ queryKey: ['users', 'for-metas-ligacoes'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const teamsQuery = useQuery({ queryKey: ['teams'], queryFn: listTeams, retry: false })

  // Metas atuais do mês, extraídas do progresso já carregado.
  const currentTargets = useMemo(() => {
    const map = {}
    for (const r of progresso?.rows ?? []) map[r.user_id] = { semanal: r.meta_semanal, mensal: r.meta_mensal }
    return map
  }, [progresso])

  const [form, setForm] = useState({})
  const teamName = useMemo(() => {
    const m = {}
    for (const t of teamsQuery.data ?? []) m[t.id] = t.nome
    return m
  }, [teamsQuery.data])

  const vendedores = (usersQuery.data?.items ?? []).filter((u) => PERFIS_VENDA.includes(u.perfil) || u.team_id)

  function valueFor(userId, campo) {
    if (form[userId]?.[campo] !== undefined) return form[userId][campo]
    const cur = currentTargets[userId]
    const raw = campo === 'semanal' ? cur?.semanal : cur?.mensal
    return raw != null ? String(raw) : ''
  }
  function set(userId, campo) {
    return (e) => setForm((f) => ({ ...f, [userId]: { ...f[userId], [campo]: e.target.value } }))
  }

  const saveMutation = useMutation({
    mutationFn: (items) => setMetasLigacoesTargets(mes, items),
    onSuccess: onSaved,
  })

  function handleSave() {
    const items = vendedores.map((u) => ({
      user_id: u.id,
      meta_semanal: valueFor(u.id, 'semanal') !== '' ? Number(valueFor(u.id, 'semanal')) : null,
      meta_mensal: valueFor(u.id, 'mensal') !== '' ? Number(valueFor(u.id, 'mensal')) : null,
    }))
    saveMutation.mutate(items)
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>Editar metas de ligações</h2>
            <p>Meta de {mesLabel.toLowerCase()} por vendedor — ligações por semana e por mês.</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          {usersQuery.isLoading ? (
            <p className="state-msg">Carregando membros…</p>
          ) : usersQuery.isError ? (
            <p className="state-msg error">Não foi possível carregar a lista de membros.</p>
          ) : vendedores.length === 0 ? (
            <p className="state-msg">Nenhum membro elegível. Cadastre vendedores/prospectores ou associe pessoas a uma equipe.</p>
          ) : (
            <div className="lig-edit-list">
              <div className="lig-edit-row lig-edit-head">
                <span>Vendedor</span><span>Meta semanal</span><span>Meta mensal</span>
              </div>
              {vendedores.map((u) => (
                <div className="lig-edit-row" key={u.id}>
                  <div className="lig-edit-name">
                    <span className="avatar">{initials(u.nome)}</span>
                    <div>
                      <div>{u.nome}</div>
                      <small className="lig-edit-team">{PERFIL_LABEL[u.perfil] ?? u.perfil} · {u.team_id ? teamName[u.team_id] ?? '—' : 'Sem equipe'}</small>
                    </div>
                  </div>
                  <input className="f-input" type="number" min="0" placeholder="—"
                         value={valueFor(u.id, 'semanal')} onChange={set(u.id, 'semanal')} />
                  <input className="f-input" type="number" min="0" placeholder="—"
                         value={valueFor(u.id, 'mensal')} onChange={set(u.id, 'mensal')} />
                </div>
              ))}
            </div>
          )}
          {saveMutation.isError && <p className="state-msg error">Não foi possível salvar as metas. Tente novamente.</p>}
        </div>
        <div className="drawer-foot">
          <button className="btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn-primary" disabled={saveMutation.isPending} onClick={handleSave}>
            {saveMutation.isPending ? 'Salvando…' : 'Salvar metas'}
          </button>
        </div>
      </div>
    </div>
  )
}
