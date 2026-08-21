import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getMetasVendaResumo, setMetasVendaTargets } from '../api/metasVenda'
import { listUsers } from '../api/users'
import { listTeams } from '../api/teams'
import '../styles/dataTable.css'
import './MetasVendaPage.css'

function money(v) {
  return Number(v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}
function fmt(n) { return Number(n ?? 0).toLocaleString('pt-BR') }
const PERFIL_LABEL = {
  admin: 'Admin', gestor: 'Gestor', vendedor: 'Vendedor',
  prospector: 'Prospector', pesquisador: 'Pesquisador', visualizador: 'Visualizador',
}
function pct(real, meta) {
  if (!meta) return null
  return Math.round((real / meta) * 100)
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

// Célula "realizado / meta" com pill de atingimento. status vem do backend (ok/atencao/critico).
function MetaCell({ real, meta, status, valor }) {
  const p = pct(real, meta)
  const realTxt = valor ? money(real) : fmt(real)
  const metaTxt = valor ? money(meta) : fmt(meta)
  if (!meta) {
    return <div className="mv-cell"><span className="mv-real">{realTxt}</span><span className="mv-nogoal">sem meta</span></div>
  }
  return (
    <div className="mv-cell">
      <span className="mv-real">{realTxt} <span className="mv-of">/ {metaTxt}</span></span>
      <span className={`mv-pill mv-${status}`}>{p}%</span>
    </div>
  )
}

export default function MetasVendaPage() {
  const queryClient = useQueryClient()
  const options = useMemo(mesOptions, [])
  const [mes, setMes] = useState(options[0].value)
  const [editOpen, setEditOpen] = useState(false)

  const resumoQuery = useQuery({
    queryKey: ['metas-venda', 'resumo', mes],
    queryFn: () => getMetasVendaResumo(mes),
    retry: false,
  })

  if (resumoQuery.isError) {
    return (
      <>
        <header className="topbar"><div className="topbar-title"><h1>Metas de Vendas</h1></div></header>
        <div className="content"><p className="state-msg error">Só administradores e gestores podem ver este controle.</p></div>
      </>
    )
  }

  const data = resumoQuery.data
  const equipes = data?.equipes ?? []
  const mesLabel = (options.find((o) => o.value === mes)?.label ?? mes)
  const atingQtd = pct(data?.total_realizado_qtd, data?.total_meta_qtd)
  const atingValor = pct(data?.total_realizado_valor, data?.total_meta_valor)

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Metas de Vendas</h1>
          <p>Quantidade e valor por vendedor e equipe — meta definida por mês, realizado ao vivo dos negócios ganhos</p>
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
          <span className="mv-hint">Realizado = negócios com status "ganho" e data de fechamento em {mesLabel.toLowerCase()}.</span>
        </div>

        {resumoQuery.isLoading ? (
          <p className="state-msg">Carregando…</p>
        ) : (
          <>
            <div className="stat-strip">
              <div className="stat-tile">
                <div className="t">Vendas realizadas</div>
                <div className="v">{fmt(data.total_realizado_qtd)} <small>/ {fmt(data.total_meta_qtd)}</small></div>
                {atingQtd != null && <div className="mv-sub">{atingQtd}% da meta</div>}
              </div>
              <div className="stat-tile">
                <div className="t">Valor realizado</div>
                <div className="v">{money(data.total_realizado_valor)}</div>
                <div className="mv-sub">meta {money(data.total_meta_valor)}{atingValor != null ? ` · ${atingValor}%` : ''}</div>
              </div>
              <div className="stat-tile">
                <div className="t">Equipes</div>
                <div className="v">{equipes.filter((e) => e.team_id).length}</div>
              </div>
              <div className="stat-tile">
                <div className="t">Membros com meta</div>
                <div className="v">{equipes.reduce((a, e) => a + e.vendedores.filter((v) => v.meta_qtd != null || v.meta_valor != null).length, 0)}</div>
              </div>
            </div>

            {equipes.length === 0 ? (
              <div className="card"><p className="state-msg">Nenhuma meta ou venda neste mês. Use "Editar metas" para definir as metas do período.</p></div>
            ) : (
              equipes.map((equipe) => (
                <div className="card mv-team-card" key={equipe.team_id ?? 'sem-equipe'}>
                  <div className="card-head mv-team-head">
                    <div>
                      <h3>{equipe.nome}</h3>
                      <p>{equipe.gestor_nome ? `Gestor: ${equipe.gestor_nome}` : 'Sem gestor definido'} · {equipe.vendedores.length} membro{equipe.vendedores.length === 1 ? '' : 's'}</p>
                    </div>
                    <div className="mv-team-totals">
                      <div className="mv-total">
                        <span className="mv-total-label">Qtd</span>
                        <span className="mv-total-val">{fmt(equipe.realizado_qtd)}<small> / {fmt(equipe.meta_qtd)}</small></span>
                      </div>
                      <div className="mv-total">
                        <span className="mv-total-label">Valor</span>
                        <span className="mv-total-val">{money(equipe.realizado_valor)}<small> / {money(equipe.meta_valor)}</small></span>
                      </div>
                    </div>
                  </div>
                  <div className="table-scroll">
                    <table className="data mv-table">
                      <thead>
                        <tr>
                          <th>Membro</th>
                          <th>Quantidade</th>
                          <th>Valor</th>
                        </tr>
                      </thead>
                      <tbody>
                        {equipe.vendedores.map((v) => (
                          <tr key={v.user_id}>
                            <td>
                              <div className="row-resp">
                                <span className="avatar">{initials(v.nome)}</span>
                                <span className="row-resp-name">{v.nome}</span>
                                <span className={`mv-role mv-role-${v.perfil}`}>{PERFIL_LABEL[v.perfil] ?? v.perfil}</span>
                              </div>
                            </td>
                            <td><MetaCell real={v.realizado_qtd} meta={v.meta_qtd} status={v.status_qtd} /></td>
                            <td><MetaCell real={v.realizado_valor} meta={v.meta_valor} status={v.status_valor} valor /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))
            )}
          </>
        )}
      </div>

      {editOpen && (
        <EditTargetsDrawer
          mes={mes}
          mesLabel={mesLabel}
          resumo={data}
          onClose={() => setEditOpen(false)}
          onSaved={() => {
            queryClient.invalidateQueries({ queryKey: ['metas-venda'] })
            setEditOpen(false)
          }}
        />
      )}
    </>
  )
}

function EditTargetsDrawer({ mes, mesLabel, resumo, onClose, onSaved }) {
  const usersQuery = useQuery({ queryKey: ['users', 'for-metas-venda'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const teamsQuery = useQuery({ queryKey: ['teams'], queryFn: listTeams, retry: false })

  // Metas atuais do mês, extraídas do resumo já carregado (user_id -> {qtd, valor}).
  const currentTargets = useMemo(() => {
    const map = {}
    for (const e of resumo?.equipes ?? []) {
      for (const v of e.vendedores) map[v.user_id] = { qtd: v.meta_qtd, valor: v.meta_valor }
    }
    return map
  }, [resumo])

  const [form, setForm] = useState({})
  const teamName = useMemo(() => {
    const m = {}
    for (const t of teamsQuery.data ?? []) m[t.id] = t.nome
    return m
  }, [teamsQuery.data])

  // Carregam meta de venda: quem tem perfil de venda (vendedor/gestor/prospector/
  // pesquisador) ou já pertence a uma equipe — assim todo membro de equipe aparece,
  // qualquer que seja o perfil.
  const PERFIS_VENDA = ['vendedor', 'gestor', 'prospector', 'pesquisador']
  const vendedores = (usersQuery.data?.items ?? []).filter((u) => PERFIS_VENDA.includes(u.perfil) || u.team_id)

  function valueFor(userId, campo) {
    if (form[userId]?.[campo] !== undefined) return form[userId][campo]
    const cur = currentTargets[userId]
    const raw = campo === 'qtd' ? cur?.qtd : cur?.valor
    return raw != null ? String(raw) : ''
  }
  function set(userId, campo) {
    return (e) => setForm((f) => ({ ...f, [userId]: { ...f[userId], [campo]: e.target.value } }))
  }

  const saveMutation = useMutation({
    mutationFn: (items) => setMetasVendaTargets(mes, items),
    onSuccess: onSaved,
  })

  function handleSave() {
    const items = vendedores.map((u) => ({
      user_id: u.id,
      meta_qtd: valueFor(u.id, 'qtd') !== '' ? Number(valueFor(u.id, 'qtd')) : null,
      meta_valor: valueFor(u.id, 'valor') !== '' ? Number(valueFor(u.id, 'valor')) : null,
    }))
    saveMutation.mutate(items)
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>Editar metas de venda</h2>
            <p>Meta de {mesLabel.toLowerCase()} por vendedor — quantidade e valor. A meta da equipe é a soma dos vendedores.</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          {usersQuery.isLoading ? (
            <p className="state-msg">Carregando membros…</p>
          ) : usersQuery.isError ? (
            <p className="state-msg error">Não foi possível carregar a lista de membros.</p>
          ) : vendedores.length === 0 ? (
            <p className="state-msg">Nenhum membro elegível a meta de venda. Cadastre vendedores/prospectores ou associe pessoas a uma equipe.</p>
          ) : (
            <div className="mv-edit-list">
              <div className="mv-edit-row mv-edit-head">
                <span>Vendedor</span><span>Meta qtd</span><span>Meta valor (R$)</span>
              </div>
              {vendedores.map((u) => (
                <div className="mv-edit-row" key={u.id}>
                  <div className="mv-edit-name">
                    <span className="avatar">{initials(u.nome)}</span>
                    <div>
                      <div>{u.nome}</div>
                      <small className="mv-edit-team">{PERFIL_LABEL[u.perfil] ?? u.perfil} · {u.team_id ? teamName[u.team_id] ?? '—' : 'Sem equipe'}</small>
                    </div>
                  </div>
                  <input className="f-input" type="number" min="0" placeholder="—"
                         value={valueFor(u.id, 'qtd')} onChange={set(u.id, 'qtd')} />
                  <input className="f-input" type="number" min="0" step="1000" placeholder="—"
                         value={valueFor(u.id, 'valor')} onChange={set(u.id, 'valor')} />
                </div>
              ))}
            </div>
          )}
          {saveMutation.isError && (
            <p className="state-msg error">Não foi possível salvar as metas. Tente novamente.</p>
          )}
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
