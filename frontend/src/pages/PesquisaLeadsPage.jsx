import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext.jsx'
import {
  createLeadProspect, deleteLeadProspect, enrichLeadProspect, getLeadProspectImportJob, importLeadProspects,
  listLeadProspects, promoteLeadProspect, updateLeadProspect,
} from '../api/leadProspects'
import { getIcpScoringRules, updateIcpScoringRules } from '../api/tenant'
import { listUsers } from '../api/users'
import '../styles/dataTable.css'
import './PesquisaLeadsPage.css'

const STATUS_LABEL = {
  novo: 'Novo', enriquecer: 'Enriquecer', triagem: 'Triagem', qualificado: 'Qualificado',
  promovido: 'Promovido', descartado: 'Descartado',
}
const SETORES = ['Farma', 'Alimentos', 'Autopeças', 'Etiquetas', 'Plástico', 'Máquinas e Equipamentos',
  'Química', 'Cosmético', 'Serviços', 'Tecnologia', 'Varejo', 'Outro']
const FAIXAS = ['1-50', '51-200', '201-500', '501-1.000', '1.001-5.000', '5.001-10.000', '+ de 10.001']
const UF_REGIAO = {
  AC: 'Norte', AP: 'Norte', AM: 'Norte', PA: 'Norte', RO: 'Norte', RR: 'Norte', TO: 'Norte',
  AL: 'Nordeste', BA: 'Nordeste', CE: 'Nordeste', MA: 'Nordeste', PB: 'Nordeste', PE: 'Nordeste',
  PI: 'Nordeste', RN: 'Nordeste', SE: 'Nordeste',
  DF: 'Centro-Oeste', GO: 'Centro-Oeste', MT: 'Centro-Oeste', MS: 'Centro-Oeste',
  ES: 'Sudeste', MG: 'Sudeste', RJ: 'Sudeste', SP: 'Sudeste',
  PR: 'Sul', RS: 'Sul', SC: 'Sul',
}
const UFS = Object.keys(UF_REGIAO).sort()
const REGIOES = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']

function fitClass(fit) {
  if (fit === 'Sem Perfil') return 'SemPerfil'
  if (fit === 'Não avaliado') return 'NaoAvaliado'
  return fit
}
function fitShort(fit) {
  if (fit === 'Sem Perfil') return 'SP'
  if (fit === 'Não avaliado') return '—'
  return fit
}
function money(n) {
  return `R$ ${Number(n ?? 0).toFixed(2).replace('.', ',')}`
}
function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}
function IconImport() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7">
      <path d="M10 13.5V4M6.3 7.7L10 4l3.7 3.7" />
      <path d="M4 15.5h12" />
    </svg>
  )
}

export default function PesquisaLeadsPage() {
  const { user } = useAuth()
  const isAdmin = user?.perfil === 'admin'
  const queryClient = useQueryClient()
  const [busca, setBusca] = useState('')
  const [status, setStatus] = useState('')
  const [icpFit, setIcpFit] = useState('')
  const [pesquisadoPor, setPesquisadoPor] = useState('')
  const [onlyBonus, setOnlyBonus] = useState(false)
  const [drawerLead, setDrawerLead] = useState(undefined) // undefined = fechado, null = novo, obj = editar
  const [criteriaOpen, setCriteriaOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [promotingLead, setPromotingLead] = useState(null)
  const [enrichingLead, setEnrichingLead] = useState(null)
  const [selected, setSelected] = useState({})
  const [bulkOwnerOpen, setBulkOwnerOpen] = useState(false)
  const [bulkOwnerId, setBulkOwnerId] = useState('')

  const usersQuery = useQuery({ queryKey: ['users', 'for-lead-prospects'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const users = usersQuery.data?.items ?? []
  const usersById = Object.fromEntries(users.map((u) => [u.id, u.nome]))

  // volume esperado é baixo (pesquisa manual) — busca tudo e filtra/pagina client-side
  const leadsQuery = useQuery({ queryKey: ['lead-prospects', 'all'], queryFn: () => listLeadProspects({ size: 200 }) })
  const allLeads = leadsQuery.data?.items ?? []

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['lead-prospects'] })
  }

  const createMutation = useMutation({ mutationFn: createLeadProspect, onSuccess: () => { setDrawerLead(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateLeadProspect(id, data), onSuccess: () => { setDrawerLead(undefined); invalidate() } })
  const promoteMutation = useMutation({ mutationFn: promoteLeadProspect, onSuccess: () => { setPromotingLead(null); invalidate() } })
  const enrichMutation = useMutation({ mutationFn: enrichLeadProspect })
  const applyEnrichMutation = useMutation({
    mutationFn: ({ id, data }) => updateLeadProspect(id, data),
    onSuccess: () => { setEnrichingLead(null); enrichMutation.reset(); invalidate() },
  })
  const bulkOwnerMutation = useMutation({
    mutationFn: () => Promise.all(selectedIds.map((id) => updateLeadProspect(id, { pesquisado_por: bulkOwnerId }))),
    onSuccess: () => { setBulkOwnerOpen(false); setBulkOwnerId(''); setSelected({}); invalidate() },
  })

  function handleEnrich(lead) {
    setEnrichingLead(lead)
    enrichMutation.mutate(lead.id)
  }

  function toggleSelect(id) {
    setSelected((s) => ({ ...s, [id]: !s[id] }))
  }

  function toggleSelectAll() {
    const allSelected = filtered.length > 0 && filtered.every((l) => selected[l.id])
    const next = {}
    if (!allSelected) filtered.forEach((l) => { next[l.id] = true })
    setSelected(next)
  }

  async function handleBulkDelete() {
    if (!confirm(`Excluir ${selectedIds.length} pesquisa(s) selecionada(s)?`)) return
    await Promise.all(selectedIds.map((id) => deleteLeadProspect(id)))
    setSelected({})
    invalidate()
  }

  const filtered = useMemo(() => {
    const q = busca.trim().toLowerCase()
    return allLeads.filter((l) => {
      if (status && l.status !== status) return false
      if (icpFit && l.icp_fit !== icpFit) return false
      if (pesquisadoPor && l.pesquisado_por !== pesquisadoPor) return false
      if (onlyBonus && !l.recebe_bonus) return false
      if (q) {
        const hay = `${l.empresa} ${l.setor ?? ''} ${l.segmento ?? ''}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [allLeads, busca, status, icpFit, pesquisadoPor, onlyBonus])

  const selectedIds = Object.keys(selected).filter((id) => selected[id])

  const stats = useMemo(() => {
    const counts = { A: 0, B: 0, C: 0, semPerfil: 0 }
    let bonusCount = 0; let bonusValorTotal = 0; let bonusPending = 0; let prontos = 0; let promovidos = 0
    allLeads.forEach((l) => {
      if (l.icp_fit === 'A') counts.A += 1
      else if (l.icp_fit === 'B') counts.B += 1
      else if (l.icp_fit === 'C') counts.C += 1
      else counts.semPerfil += 1
      if (l.recebe_bonus) { bonusCount += 1; bonusValorTotal += l.bonus_valor }
      else if (l.gamificacao > 70 && l.status !== 'promovido') bonusPending += 1
      if (l.status === 'qualificado') prontos += 1
      if (l.status === 'promovido') promovidos += 1
    })
    return { total: allLeads.length, ...counts, bonusCount, bonusValorTotal, bonusPending, prontos, promovidos }
  }, [allLeads])

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Pesquisa de Leads</h1>
          <p>
            <span className="mono">{stats.total}</span> empresas pesquisadas este mês · <span className="mono">{stats.bonusCount}</span> com
            bônus válido ({money(stats.bonusValorTotal)}) · <span className="mono">{stats.bonusPending}</span> pendentes de promoção
          </p>
        </div>
        <div className="page-actions">
          <button className="btn-ghost" onClick={() => setImportOpen(true)}><IconImport /> Importar</button>
          <button className="btn-ghost" onClick={() => setCriteriaOpen(true)}>Critérios de pontuação</button>
          <button className="btn-primary" onClick={() => setDrawerLead(null)}>+ Nova pesquisa</button>
        </div>
      </header>

      <div className="content">
        <div className="stat-strip">
          <div className="stat-tile"><div className="t">Total</div><div className="v">{stats.total}</div></div>
          <div className="stat-tile fit-A"><div className="t">ICP A</div><div className="v">{stats.A}</div></div>
          <div className="stat-tile fit-B"><div className="t">ICP B</div><div className="v">{stats.B}</div></div>
          <div className="stat-tile fit-C"><div className="t">ICP C</div><div className="v">{stats.C}</div></div>
          <div className="stat-tile"><div className="t">Sem perfil / não avaliado</div><div className="v">{stats.semPerfil}</div></div>
          <div className="stat-tile"><div className="t">Qualificadas</div><div className="v">{stats.prontos}</div></div>
          <div className="stat-tile bonus"><div className="t">Promovidas</div><div className="v">{stats.promovidos}</div></div>
        </div>

        <div className="filters-bar">
          <div className="search">
            <input type="text" placeholder="Buscar por empresa ou setor" value={busca} onChange={(e) => setBusca(e.target.value)} />
          </div>
          <select className="filter-select" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todos os status</option>
            {Object.entries(STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <select className="filter-select" value={icpFit} onChange={(e) => setIcpFit(e.target.value)}>
            <option value="">Todo ICP Fit</option>
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
            <option value="Sem Perfil">Sem Perfil</option>
            <option value="Não avaliado">Não avaliado</option>
          </select>
          <select className="filter-select" value={pesquisadoPor} onChange={(e) => setPesquisadoPor(e.target.value)}>
            <option value="">Todos os pesquisadores</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
          <label className="chip-toggle">
            <input type="checkbox" checked={onlyBonus} onChange={(e) => setOnlyBonus(e.target.checked)} />
            Somente com bônus válido
          </label>
        </div>

        <div className="card">
          {selectedIds.length > 0 && (
            <div className="bulk-bar show">
              <span><b>{selectedIds.length}</b> selecionada(s)</span>
              <div className="link-btn">
                <a onClick={() => setBulkOwnerOpen(true)}>Alterar proprietário</a>
                <a onClick={handleBulkDelete}>Excluir</a>
              </div>
            </div>
          )}

          {leadsQuery.isLoading && <p className="state-msg">Carregando pesquisas…</p>}
          {leadsQuery.isError && <p className="state-msg error">Não foi possível carregar as pesquisas agora.</p>}
          {leadsQuery.data && filtered.length === 0 && <p className="state-msg">Nenhuma pesquisa encontrada.</p>}

          {filtered.length > 0 && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th className="checkbox-col">
                      <input
                        type="checkbox"
                        checked={filtered.length > 0 && filtered.every((l) => selected[l.id])}
                        onChange={toggleSelectAll}
                      />
                    </th>
                    <th>Empresa</th>
                    <th>Status</th>
                    <th>ICP Fit</th>
                    <th>Faixa / Região</th>
                    <th>Gamificação</th>
                    <th>Pesquisador</th>
                    <th style={{ textAlign: 'right' }}>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((lead) => (
                    <LeadRow
                      key={lead.id}
                      lead={lead}
                      pesquisadorNome={usersById[lead.pesquisado_por]}
                      selected={!!selected[lead.id]}
                      onToggleSelect={() => toggleSelect(lead.id)}
                      onEdit={() => setDrawerLead(lead)}
                      onPromote={() => setPromotingLead(lead)}
                      onEnrich={() => handleEnrich(lead)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {drawerLead !== undefined && (
        <LeadDrawer
          lead={drawerLead}
          users={users}
          onClose={() => setDrawerLead(undefined)}
          onSubmit={(data) => {
            if (drawerLead) updateMutation.mutate({ id: drawerLead.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {criteriaOpen && <CriteriaDrawer isAdmin={isAdmin} onClose={() => setCriteriaOpen(false)} onSaved={invalidate} />}

      {importOpen && <ImportDrawer onClose={() => setImportOpen(false)} onDone={invalidate} />}

      {bulkOwnerOpen && (
        <div className="scrim show" onClick={() => setBulkOwnerOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Alterar proprietário</h3>
            <p className="sub">Definir o pesquisador de <strong>{selectedIds.length}</strong> pesquisa(s) selecionada(s).</p>
            <div className="f-group">
              <select className="f-select" value={bulkOwnerId} onChange={(e) => setBulkOwnerId(e.target.value)}>
                <option value="" disabled>Selecione o novo pesquisador</option>
                {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
              </select>
            </div>
            <div className="row">
              <button className="btn-ghost" onClick={() => setBulkOwnerOpen(false)}>Cancelar</button>
              <button
                className="btn-primary"
                disabled={!bulkOwnerId || bulkOwnerMutation.isPending}
                onClick={() => bulkOwnerMutation.mutate()}
              >
                {bulkOwnerMutation.isPending ? 'Salvando…' : 'Aplicar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {promotingLead && (
        <div className="scrim show" onClick={() => setPromotingLead(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Promover para Empresa</h3>
            <p className="sub">
              <strong>{promotingLead.empresa}</strong> entrará no cadastro oficial de Empresas como <strong>lead</strong>, com os dados desta
              pesquisa. O registro de pesquisa continua aqui, marcado como &quot;Promovido&quot; — é só a partir de agora que o bônus de quem
              pesquisou se torna válido.
            </p>
            <div className="row">
              <button className="btn-ghost" onClick={() => setPromotingLead(null)}>Cancelar</button>
              <button className="btn-primary" disabled={promoteMutation.isPending} onClick={() => promoteMutation.mutate(promotingLead.id)}>
                Promover
              </button>
            </div>
          </div>
        </div>
      )}

      {enrichingLead && (
        <EnrichModal
          lead={enrichingLead}
          result={enrichMutation.data}
          isPending={enrichMutation.isPending}
          error={enrichMutation.error}
          applying={applyEnrichMutation.isPending}
          onRetry={() => enrichMutation.mutate(enrichingLead.id)}
          onClose={() => { setEnrichingLead(null); enrichMutation.reset() }}
          onApply={(suggestion) => {
            const data = Object.fromEntries(Object.entries(suggestion).filter(([k, v]) => k !== 'observacoes' && v != null))
            data.status = 'enriquecer'
            applyEnrichMutation.mutate({ id: enrichingLead.id, data })
          }}
        />
      )}
    </>
  )
}

const ENRICH_FIELD_LABELS = {
  setor: 'Setor', segmento: 'Segmento', uf: 'UF', faixa_funcionarios: 'Faixa de funcionários',
  faturamento: 'Faturamento estimado', site: 'Site', telefone: 'Telefone', linkedin: 'LinkedIn',
  contato_sugerido: 'Contato sugerido', dor_sugerida: 'Dor sugerida',
}

function EnrichModal({ lead, result, isPending, error, applying, onRetry, onClose, onApply }) {
  const fields = result ? Object.entries(ENRICH_FIELD_LABELS).filter(([k]) => result[k] != null && result[k] !== '') : []

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>Enriquecer com IA</h2>
            <p>{lead.empresa} — sugestões pesquisadas na web, revise antes de aplicar</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          {isPending && <p className="state-msg">Pesquisando a empresa na web… isso pode levar de 5 a 15 segundos.</p>}

          {error && (
            <>
              <p className="state-msg error">
                {error.response?.data?.error?.message ?? 'Não foi possível enriquecer esta pesquisa agora.'}
              </p>
              <button className="btn-ghost" onClick={onRetry}>Tentar de novo</button>
            </>
          )}

          {result && (
            <>
              {fields.length === 0 && <p className="state-msg">A IA não encontrou nenhum dado novo para esta empresa.</p>}
              {fields.map(([key, label]) => (
                <div className="f-group" key={key} style={{ marginBottom: 0 }}>
                  <label className="f-label">{label}</label>
                  <div className="row-title" style={{ fontWeight: 500 }}>
                    {key === 'faturamento' ? money(result[key]) : result[key]}
                  </div>
                </div>
              ))}
              {result.observacoes && <div className="rule-note">{result.observacoes}</div>}
            </>
          )}
        </div>
        <div className="drawer-foot">
          <button className="btn-ghost" onClick={onClose}>Descartar</button>
          {result && (
            <button className="btn-primary" disabled={applying || fields.length === 0} onClick={() => onApply(result)}>
              {applying ? 'Aplicando…' : 'Aplicar sugestões'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function LeadRow({ lead, pesquisadorNome, selected, onToggleSelect, onEdit, onPromote, onEnrich }) {
  const bonusPillClass = lead.recebe_bonus ? 'yes' : (lead.gamificacao > 70 && lead.status !== 'descartado' ? 'pending' : 'no')
  const bonusPillText = lead.recebe_bonus ? `Bônus ${money(lead.bonus_valor)}` : (bonusPillClass === 'pending' ? 'Bônus pendente' : 'Sem bônus')
  const canPromote = !lead.promoted_company_id && lead.status !== 'descartado'
  const canEnrich = !lead.promoted_company_id && lead.status !== 'descartado'

  return (
    <tr className={selected ? 'row-selected' : ''}>
      <td className="checkbox-col">
        <input type="checkbox" checked={selected} onChange={onToggleSelect} />
      </td>
      <td>
        <div className="row-title lead-empresa-name">{lead.empresa}</div>
        {lead.segmento && <div className="row-sub">{lead.segmento}</div>}
      </td>
      <td>
        <span className="status-pill" data-status={lead.status}><span className="d" />{STATUS_LABEL[lead.status] ?? lead.status}</span>
      </td>
      <td>
        <div className="fit-cell">
          <span className={`fit-badge ${fitClass(lead.icp_fit)}`}>{fitShort(lead.icp_fit)}</span>
          <span className="fit-score">{lead.score_icp}pt</span>
        </div>
      </td>
      <td>
        <div className="row-sub" style={{ marginTop: 0 }}>{lead.faixa_funcionarios || '—'}</div>
        <div className="row-sub">{lead.uf ? `${lead.uf} · ${lead.regiao || UF_REGIAO[lead.uf]}` : (lead.regiao || '—')}</div>
      </td>
      <td>
        <div className="gam-cell">
          <div className="gam-bar-track"><div className="gam-bar-fill" style={{ width: `${lead.gamificacao}%` }} /></div>
          <div className="gam-num">{lead.gamificacao}pt</div>
          <span className={`bonus-pill ${bonusPillClass}`}>{bonusPillText}</span>
        </div>
      </td>
      <td>
        <div className="row-resp">
          <span className="avatar">{initials(pesquisadorNome)}</span>
          {pesquisadorNome ?? '—'}
        </div>
      </td>
      <td>
        <div className="row-actions" style={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
          {canEnrich && <button className="icon-btn" title="Enriquecer com IA" onClick={onEnrich}>✨</button>}
          {canPromote && <button className="icon-btn" title="Promover para Empresa" onClick={onPromote}>↑</button>}
          <button className="icon-btn" title="Editar" onClick={onEdit}>✎</button>
        </div>
      </td>
    </tr>
  )
}

function LeadDrawer({ lead, users, onClose, onSubmit, submitting, error }) {
  const [form, setForm] = useState({
    empresa: lead?.empresa ?? '',
    setor: lead?.setor ?? '',
    segmento: lead?.segmento ?? '',
    uf: lead?.uf ?? '',
    regiao: lead?.regiao ?? '',
    faixa_funcionarios: lead?.faixa_funcionarios ?? '',
    faturamento: lead?.faturamento ?? '',
    telefone: lead?.telefone ?? '',
    site: lead?.site ?? '',
    linkedin: lead?.linkedin ?? '',
    contato_sugerido: lead?.contato_sugerido ?? '',
    dor_sugerida: lead?.dor_sugerida ?? '',
    status: lead?.status ?? 'novo',
    pesquisado_por: lead?.pesquisado_por ?? '',
  })

  const preview = useMemo(() => computePreview(form), [form])

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!form.empresa.trim() || !form.pesquisado_por) return
    onSubmit({
      empresa: form.empresa.trim(),
      setor: form.setor || null,
      segmento: form.segmento || null,
      uf: form.uf || null,
      regiao: form.regiao || null,
      faixa_funcionarios: form.faixa_funcionarios || null,
      faturamento: form.faturamento ? Number(form.faturamento) : null,
      telefone: form.telefone || null,
      site: form.site || null,
      linkedin: form.linkedin || null,
      contato_sugerido: form.contato_sugerido || null,
      dor_sugerida: form.dor_sugerida || null,
      status: form.status,
      pesquisado_por: form.pesquisado_por,
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>{lead ? 'Editar pesquisa' : 'Nova pesquisa'}</h2>
            <p>Preencha os dados coletados na pesquisa</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-group">
              <label className="f-label">Empresa <span className="req">*</span></label>
              <input className="f-input" value={form.empresa} onChange={set('empresa')} placeholder="Razão social ou nome comercial" required />
            </div>

            <p className="f-hint" style={{ marginTop: -6, marginBottom: 10 }}>
              Campos em <b style={{ color: 'var(--azul)' }}>azul</b> definem o Score ICP.
            </p>

            <div className="f-row">
              <div className="f-group">
                <label className="f-label icp-field">Setor</label>
                <select className="f-select" value={form.setor} onChange={set('setor')}>
                  <option value="">Selecione…</option>
                  {SETORES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="f-group">
                <label className="f-label">Segmento <span className="opt">subcategoria</span></label>
                <input className="f-input" value={form.segmento} onChange={set('segmento')} placeholder="Ex.: Genéricos, Embalagens flexíveis…" />
              </div>
            </div>

            <div className="f-row">
              <div className="f-group">
                <label className="f-label icp-field">UF</label>
                <select className="f-select" value={form.uf} onChange={set('uf')}>
                  <option value="">Selecione…</option>
                  {UFS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
                </select>
              </div>
              <div className="f-group">
                <label className="f-label icp-field">Região</label>
                <select className="f-select" value={form.regiao} onChange={set('regiao')}>
                  <option value="">{form.uf ? UF_REGIAO[form.uf] : 'Selecione…'}</option>
                  {REGIOES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            </div>

            <div className="f-row">
              <div className="f-group">
                <label className="f-label icp-field">Faixa de funcionários</label>
                <select className="f-select" value={form.faixa_funcionarios} onChange={set('faixa_funcionarios')}>
                  <option value="">Selecione…</option>
                  {FAIXAS.map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div className="f-group">
                <label className="f-label">Faturamento estimado</label>
                <input className="f-input" type="number" step="0.01" value={form.faturamento} onChange={set('faturamento')} placeholder="Ex.: 20000000" />
              </div>
            </div>

            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Telefone</label>
                <input className="f-input" value={form.telefone} onChange={set('telefone')} placeholder="(00) 0000-0000" />
              </div>
              <div className="f-group">
                <label className="f-label">Site</label>
                <input className="f-input" value={form.site} onChange={set('site')} placeholder="empresa.com.br" />
              </div>
            </div>

            <div className="f-group">
              <label className="f-label">LinkedIn</label>
              <input className="f-input" value={form.linkedin} onChange={set('linkedin')} placeholder="linkedin.com/company/…" />
            </div>

            <div className="f-group">
              <label className="f-label">Contato sugerido</label>
              <input className="f-input" value={form.contato_sugerido} onChange={set('contato_sugerido')} placeholder="Ex.: Ana Paula — Gerente de Compras" />
            </div>

            <div className="f-group">
              <label className="f-label">Dor sugerida</label>
              <textarea className="f-textarea" value={form.dor_sugerida} onChange={set('dor_sugerida')} placeholder="Hipótese de dor levantada na pesquisa" />
            </div>

            <div className="live-preview">
              <div className="lp-title">Cálculo automático</div>
              <div className="lp-row"><span>Score ICP</span><b>{preview.score}</b></div>
              <div className="lp-row"><span>ICP Fit</span><b>{preview.fit}</b></div>
              <div className="lp-row"><span>Gamificação</span><b>{preview.gam}</b></div>
              <div className="lp-row"><span>Bônus</span><b>{preview.bonus ? 'Sim' : 'Não'}</b></div>
            </div>

            <div className="divider-label">Fluxo</div>

            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Status</label>
                <select className="f-select" value={form.status} onChange={set('status')}>
                  {Object.entries(STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
                <span className="f-hint">Bônus só é válido quando o status vira &quot;Promovido&quot;.</span>
              </div>
              <div className="f-group">
                <label className="f-label">Pesquisado por <span className="req">*</span></label>
                <select className="f-select" value={form.pesquisado_por} onChange={set('pesquisado_por')} required>
                  <option value="" disabled>Selecione</option>
                  {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
                </select>
              </div>
            </div>

            {error && <p className="state-msg error">Não foi possível salvar. Confira os dados e tente de novo.</p>}
          </div>
          <div className="drawer-foot">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar pesquisa'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Preview client-side simplificado: usa os pesos default (mesmos do backend) só para dar
// um feedback imediato ao digitar. O valor real, salvo, é sempre recalculado no servidor
// a partir dos critérios vigentes do tenant — que podem ter sido customizados.
const PREVIEW_RULES = {
  setor: { Farma: 40, Alimentos: 40, Autopeças: 40, Etiquetas: 40, Plástico: 30, 'Máquinas e Equipamentos': 30, Química: 30, Cosmético: 30 },
  setorFallback: 10,
  regiao: { Sudeste: 30, Sul: 30, Nordeste: 30, Norte: 0, 'Centro-Oeste': 0 },
  faixa: { '1-50': 0, '51-200': 30, '201-500': 30, '501-1.000': 30, '1.001-5.000': 40, '5.001-10.000': 50, '+ de 10.001': 0 },
  corteA: 80, corteB: 70, corteC: 40,
}
function computePreview(form) {
  const setorPts = form.setor ? (PREVIEW_RULES.setor[form.setor] ?? PREVIEW_RULES.setorFallback) : 0
  const regiao = form.regiao || (form.uf ? UF_REGIAO[form.uf] : null)
  const regiaoPts = regiao ? (PREVIEW_RULES.regiao[regiao] ?? 0) : 0
  const faixaPts = form.faixa_funcionarios ? (PREVIEW_RULES.faixa[form.faixa_funcionarios] ?? 0) : 0
  const score = Math.min(100, setorPts + regiaoPts + faixaPts)
  let fit
  if (score === 0 && !form.setor && !form.uf && !form.regiao && !form.faixa_funcionarios) fit = 'Não avaliado'
  else if (score >= PREVIEW_RULES.corteA) fit = 'A'
  else if (score >= PREVIEW_RULES.corteB) fit = 'B'
  else if (score >= PREVIEW_RULES.corteC) fit = 'C'
  else fit = 'Sem Perfil'
  let gam = 0
  if (!['C', 'Sem Perfil', 'Não avaliado'].includes(fit) && form.status !== 'descartado') {
    if (form.telefone) gam += 40
    if (form.setor) gam += 20
    if (form.uf || form.regiao) gam += 20
    if (form.faixa_funcionarios) gam += 10
    if (form.site) gam += 10
  }
  const bonus = form.status === 'promovido' && gam > 70
  return { score, fit, gam, bonus }
}

function ImportDrawer({ onClose, onDone }) {
  const [file, setFile] = useState(null)
  const [job, setJob] = useState(null)
  const [error, setError] = useState(null)

  const uploadMutation = useMutation({
    mutationFn: importLeadProspects,
    onSuccess: (data) => setJob(data),
    onError: () => setError('Não foi possível enviar o arquivo.'),
  })

  const pollQuery = useQuery({
    queryKey: ['lead-prospect-import-job', job?.id],
    queryFn: () => getLeadProspectImportJob(job.id),
    enabled: Boolean(job) && job.status !== 'concluido' && job.status !== 'erro',
    refetchInterval: 1200,
  })

  useEffect(() => {
    if (!pollQuery.data) return
    setJob(pollQuery.data)
    if (pollQuery.data.status === 'concluido') onDone()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollQuery.data])

  function handleFileChange(e) {
    const f = e.target.files?.[0]
    setFile(f ?? null)
    setJob(null)
    setError(null)
  }

  function handleConfirm() {
    if (file) uploadMutation.mutate(file)
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>Importar pesquisas</h2>
            <p>Envie um .csv ou .xlsx — processado em segundo plano pelo worker</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          <div className="import-cols">
            Colunas esperadas: <code>empresa*</code> <code>setor</code> <code>segmento</code> <code>uf</code>{' '}
            <code>regiao</code> <code>faixa_funcionarios</code> <code>faturamento</code> <code>telefone</code>{' '}
            <code>site</code> <code>linkedin</code> <code>contato_sugerido</code> <code>dor_sugerida</code>{' '}
            <code>status</code> <code>pesquisado_por</code>
            <br />
            <span className="f-hint">
              Os nomes das colunas precisam vir exatamente assim (minúsculo, sem acento, sem espaço) — cabeçalhos
              como &quot;Faixa de Funcionários&quot; ou &quot;Região&quot; com acento não são reconhecidos.
              <code>uf</code> é a sigla do estado (ex.: SP); <code>regiao</code> é a macrorregião (ex.: Sudeste) — informe
              ao menos um dos dois. <code>pesquisado_por</code> aceita o e-mail de um usuário do CRM — se a coluna
              faltar ou vier vazia, a pesquisa fica atribuída a quem está importando.
            </span>
          </div>

          <label className="drop-zone">
            <div className="dz-title">{file ? file.name : 'Clique para escolher um arquivo'}</div>
            <div className="dz-sub">.csv ou .xlsx</div>
            <input type="file" accept=".csv,.xlsx" onChange={handleFileChange} />
          </label>

          {error && <p className="state-msg error">{error}</p>}

          {job && (
            <div className="import-summary">
              <div className="summary-tile"><div className="v">{job.status}</div><div className="t">Status</div></div>
              <div className="summary-tile"><div className="v">{job.total_linhas ?? '—'}</div><div className="t">Linhas</div></div>
              <div className="summary-tile ok"><div className="v">{job.importadas ?? '—'}</div><div className="t">Importadas</div></div>
              <div className="summary-tile erro"><div className="v">{job.erros?.length ?? 0}</div><div className="t">Com erro</div></div>
            </div>
          )}
          {job?.erros?.length > 0 && (
            <div className="import-results">
              {job.erros.map((e, i) => (
                <div className="import-row" key={i}>
                  <span className="ln">L{e.linha ?? '?'}</span>
                  <span className="motivo">{e.motivo}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="drawer-foot">
          <button className="btn-ghost" onClick={onClose}>Fechar</button>
          <button
            className="btn-primary"
            disabled={!file || uploadMutation.isPending || (job && job.status !== 'concluido' && job.status !== 'erro')}
            onClick={handleConfirm}
          >
            {uploadMutation.isPending ? 'Enviando…' : 'Enviar'}
          </button>
        </div>
      </div>
    </div>
  )
}

function CriteriaDrawer({ isAdmin, onClose, onSaved }) {
  const rulesQuery = useQuery({ queryKey: ['tenant', 'icp-scoring-rules'], queryFn: getIcpScoringRules })
  const [rules, setRules] = useState(null)
  const saveMutation = useMutation({
    mutationFn: updateIcpScoringRules,
    onSuccess: () => { onSaved(); onClose() },
  })

  const current = rules ?? rulesQuery.data

  function setNum(section, key, value) {
    setRules((r) => {
      const base = r ?? rulesQuery.data
      if (section) return { ...base, [section]: { ...base[section], [key]: Number(value) } }
      return { ...base, [key]: Number(value) }
    })
  }

  function handleSave() {
    if (current) saveMutation.mutate(current)
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>Critérios de pontuação</h2>
            <p>Pesos do Score ICP, do corte de ICP Fit e do valor do bônus</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          {rulesQuery.isLoading && <p className="state-msg">Carregando critérios…</p>}
          {current && (
            <fieldset disabled={!isAdmin} style={{ border: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div className="rule-note">
                {isAdmin
                  ? 'Esses critérios ficam salvos por tenant — cada cliente da CRM pode ter pesos diferentes de setor, região e porte. Alterar aqui recalcula todas as pesquisas na hora.'
                  : 'Somente administradores podem alterar os critérios de pontuação. Os valores abaixo são somente leitura.'}
              </div>

              <div className="rule-section-title">Setor (pontos)</div>
              <div className="rule-table">
                {Object.entries(current.setor).map(([k, v]) => (
                  <div className="rule-row" key={k}>
                    <span>{k}</span>
                    <input type="number" value={v} onChange={(e) => setNum('setor', k, e.target.value)} />
                  </div>
                ))}
              </div>
              <span className="f-hint">Setores fora desta lista pontuam {current.setor_fallback} por padrão (ajustável abaixo).</span>
              <div className="rule-row">
                <span>Fallback (setor fora da lista)</span>
                <input type="number" value={current.setor_fallback} onChange={(e) => setNum(null, 'setor_fallback', e.target.value)} />
              </div>

              <div className="rule-section-title">Região (pontos)</div>
              <div className="rule-table">
                {Object.entries(current.regiao).map(([k, v]) => (
                  <div className="rule-row" key={k}>
                    <span>{k}</span>
                    <input type="number" value={v} onChange={(e) => setNum('regiao', k, e.target.value)} />
                  </div>
                ))}
              </div>

              <div className="rule-section-title">Porte / faixa de funcionários (pontos)</div>
              <div className="rule-table">
                {Object.entries(current.faixa_funcionarios).map(([k, v]) => (
                  <div className="rule-row" key={k}>
                    <span>{k}</span>
                    <input type="number" value={v} onChange={(e) => setNum('faixa_funcionarios', k, e.target.value)} />
                  </div>
                ))}
              </div>

              <div className="rule-section-title">Corte de ICP Fit</div>
              <div className="rule-table">
                <div className="rule-row"><span>A a partir de</span><input type="number" min="0" max="100" value={current.corte_a} onChange={(e) => setNum(null, 'corte_a', e.target.value)} /></div>
                <div className="rule-row"><span>B a partir de</span><input type="number" min="0" max="100" value={current.corte_b} onChange={(e) => setNum(null, 'corte_b', e.target.value)} /></div>
                <div className="rule-row"><span>C a partir de</span><input type="number" min="0" max="100" value={current.corte_c} onChange={(e) => setNum(null, 'corte_c', e.target.value)} /></div>
              </div>

              <div className="rule-section-title">Bônus</div>
              <div className="rule-table">
                <div className="rule-row"><span>Valor por lead qualificado (R$)</span><input type="number" min="0" step="0.5" value={current.bonus_valor} onChange={(e) => setNum(null, 'bonus_valor', e.target.value)} /></div>
              </div>

              {saveMutation.isError && <p className="state-msg error">Não foi possível salvar os critérios.</p>}
            </fieldset>
          )}
        </div>
        <div className="drawer-foot">
          <button className="btn-ghost" onClick={onClose}>Fechar sem salvar</button>
          {isAdmin && (
            <button className="btn-primary" disabled={!current || saveMutation.isPending} onClick={handleSave}>
              {saveMutation.isPending ? 'Salvando…' : 'Salvar critérios'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
