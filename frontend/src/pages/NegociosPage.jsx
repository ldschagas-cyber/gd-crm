import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  closeDeal, createDeal, deleteDeal, listDeals, moveDealStage, updateDeal,
} from '../api/deals'
import { getBoard, listPipelines } from '../api/pipelines'
import { listCompanies } from '../api/companies'
import { listContacts } from '../api/contacts'
import { listUsers } from '../api/users'
import { buildStageTintMap } from '../utils/stageColor'
import StageLabel from '../components/StageLabel.jsx'
import EnrollModal from '../components/EnrollModal.jsx'
import BulkTaskModal from '../components/BulkTaskModal.jsx'
import '../styles/dataTable.css'
import './NegociosPage.css'

const PAGE_SIZE = 20

function formatCurrency(v) {
  return v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}
// "Negócio parado": sem interação há mais tempo do que o SLA configurado na etapa
// (Pipeline > SLA por etapa). Etapas sem SLA definido nunca disparam o aviso.
function isStalled(deal, stage) {
  if (deal.status !== 'aberto' || !stage?.sla_horas) return false
  const horas = (Date.now() - new Date(deal.ultima_interacao).getTime()) / 3_600_000
  return horas > stage.sla_horas
}
function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}
function IconChevron() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M5 8l5 5 5-5" />
    </svg>
  )
}

export default function NegociosPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const [view, setView] = useState('kanban')
  const [busca, setBusca] = useState('')
  const [status, setStatus] = useState('')
  const [stageId, setStageId] = useState('')
  const [responsavelId, setResponsavelId] = useState('')
  const [page, setPage] = useState(1)
  const [showNewDeal, setShowNewDeal] = useState(false)
  const [presetCompany, setPresetCompany] = useState(null) // { id, nome } — vindo da Central de Leads ("Converter em negócio")
  const [editingDeal, setEditingDeal] = useState(null)
  const [losingDeal, setLosingDeal] = useState(null)
  const [selectedPipelineId, setSelectedPipelineId] = useState(null)
  const [showPipelineMenu, setShowPipelineMenu] = useState(false)

  const pipelinesQuery = useQuery({ queryKey: ['pipelines'], queryFn: () => listPipelines({ size: 100 }) })
  const pipelines = pipelinesQuery.data?.items ?? []
  const pipeline = pipelines.find((p) => p.id === selectedPipelineId)
    ?? pipelines.find((p) => p.is_default) ?? pipelines[0]
  const pipelineId = pipeline?.id

  function switchPipeline(id) {
    setSelectedPipelineId(id)
    setStageId('')
    setPage(1)
    setShowPipelineMenu(false)
  }

  const companiesQuery = useQuery({ queryKey: ['companies', 'for-select'], queryFn: () => listCompanies({ size: 100 }) })
  const companies = companiesQuery.data?.items ?? []
  const companiesById = Object.fromEntries(companies.map((c) => [c.id, c.razao_social]))

  const usersQuery = useQuery({ queryKey: ['users', 'for-assign'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const users = usersQuery.data?.items ?? []
  const usersById = Object.fromEntries(users.map((u) => [u.id, u.nome]))

  // Vindo da Central de Leads (botão "Converter em negócio" no drawer, só aparece
  // quando o lead está em SQL) — abre o drawer de novo negócio já com a empresa
  // selecionada. Limpa o state da navegação pra não reabrir num back/refresh.
  useEffect(() => {
    if (location.state?.presetCompanyId) {
      setPresetCompany({ id: location.state.presetCompanyId, nome: location.state.presetCompanyNome })
      setShowNewDeal(true)
      navigate(location.pathname, { replace: true, state: null })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state])

  // A empresa pode não estar nas primeiras 100 (ordem alfabética) que o select carrega —
  // garante que ela apareça como opção mesmo assim.
  const companiesForSelect = presetCompany && !companies.some((c) => c.id === presetCompany.id)
    ? [...companies, { id: presetCompany.id, razao_social: presetCompany.nome }]
    : companies

  const boardQuery = useQuery({
    queryKey: ['deals', 'board', pipelineId],
    queryFn: () => getBoard(pipelineId),
    enabled: view === 'kanban' && Boolean(pipelineId),
  })
  const dealFilters = {
    busca: busca || undefined, status: status || undefined,
    stageId: stageId || undefined, responsavelId: responsavelId || undefined,
  }

  const listQuery = useQuery({
    queryKey: ['deals', 'list', pipelineId, { page, ...dealFilters }],
    queryFn: () => listDeals({ pipelineId, page, size: PAGE_SIZE, ...dealFilters }),
    enabled: view === 'list' && Boolean(pipelineId),
    placeholderData: keepPreviousData,
  })

  function invalidateDeals() {
    queryClient.invalidateQueries({ queryKey: ['deals'] })
  }

  const createMutation = useMutation({ mutationFn: createDeal, onSuccess: () => { setShowNewDeal(false); invalidateDeals() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateDeal(id, data), onSuccess: () => { setEditingDeal(null); invalidateDeals() } })
  const moveMutation = useMutation({ mutationFn: ({ id, stageId }) => moveDealStage(id, stageId), onSuccess: invalidateDeals })
  const closeMutation = useMutation({ mutationFn: ({ id, data }) => closeDeal(id, data), onSuccess: () => { setLosingDeal(null); invalidateDeals() } })
  // Compromisso (Previsão Comercial) — toggle isolado, não passa pelo modal de edição:
  // o vendedor confirma/desconfirma o fechamento do mês direto no card ou na lista.
  const commitMutation = useMutation({ mutationFn: ({ id, commit }) => updateDeal(id, { commit }), onSuccess: invalidateDeals })
  function toggleCommit(deal) {
    commitMutation.mutate({ id: deal.id, commit: !deal.commit })
  }

  const ganhoStageId = pipeline?.stages.find((s) => s.tipo === 'ganho')?.id

  function markWon(deal) {
    if (ganhoStageId) moveMutation.mutate({ id: deal.id, stageId: ganhoStageId })
  }

  if (pipelinesQuery.isLoading) return <div className="content"><p className="state-msg">Carregando…</p></div>
  if (!pipeline) {
    return (
      <div className="content">
        <p className="state-msg">Nenhum pipeline configurado ainda. <Link to="/pipeline">Configure um pipeline</Link> antes de criar negócios.</p>
      </div>
    )
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Negócios</h1>
          <div className="pipeline-switcher-wrap">
            <button className="pipeline-switcher-btn" onClick={() => setShowPipelineMenu((v) => !v)}>
              Pipeline: <strong>{pipeline.nome}</strong>
              <IconChevron />
            </button>
            {showPipelineMenu && (
              <>
                <div className="menu-scrim" onClick={() => setShowPipelineMenu(false)} />
                <div className="pipeline-switcher-menu">
                  {pipelines.map((p) => (
                    <button
                      key={p.id}
                      className={`pipeline-switcher-item${p.id === pipelineId ? ' active' : ''}`}
                      onClick={() => switchPipeline(p.id)}
                    >
                      {p.nome}
                      {p.is_default && <span className="badge-default">Padrão</span>}
                    </button>
                  ))}
                  <div className="pipeline-switcher-divider" />
                  <Link to="/pipeline" className="pipeline-switcher-item" onClick={() => setShowPipelineMenu(false)}>
                    Configurar pipelines
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
        <button className="btn-primary" onClick={() => setShowNewDeal(true)}>+ Novo negócio</button>
      </header>

      <div className="content">
        <div className="filters-bar">
          <div className="search">
            <input type="text" placeholder="Buscar negócio" value={busca} onChange={(e) => { setBusca(e.target.value); setPage(1) }} />
          </div>
          <select className="filter-select" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
            <option value="">Todos os status</option>
            <option value="aberto">Aberto</option>
            <option value="ganho">Ganho</option>
            <option value="perdido">Perdido</option>
          </select>
          <select className="filter-select" value={stageId} onChange={(e) => { setStageId(e.target.value); setPage(1) }}>
            <option value="">Todas as etapas</option>
            {pipeline.stages.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
          </select>
          <select className="filter-select" value={responsavelId} onChange={(e) => { setResponsavelId(e.target.value); setPage(1) }}>
            <option value="">Todos os responsáveis</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
          <div className="segmented">
            <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')}>Lista</button>
            <button className={view === 'kanban' ? 'active' : ''} onClick={() => setView('kanban')}>Kanban</button>
          </div>
        </div>

        {view === 'kanban' && (
          <DealsBoard
            query={boardQuery}
            filters={{ status, stageId, responsavelId, busca }}
            companiesById={companiesById}
            usersById={usersById}
            colorMode={pipeline.cor_exibicao}
            stageTintById={buildStageTintMap(pipeline.stages)}
            onDropStage={(id, sId) => moveMutation.mutate({ id, stageId: sId })}
            onOpen={(d) => navigate(`/negocios/${d.id}`)}
            onEdit={setEditingDeal}
            onWon={markWon}
            onLost={setLosingDeal}
            onToggleCommit={toggleCommit}
          />
        )}

        {view === 'list' && (
          <DealsList
            query={listQuery}
            page={page}
            setPage={setPage}
            companiesById={companiesById}
            usersById={usersById}
            stages={pipeline.stages}
            colorMode={pipeline.cor_exibicao}
            stageTintById={buildStageTintMap(pipeline.stages)}
            onOpen={(d) => navigate(`/negocios/${d.id}`)}
            onEdit={setEditingDeal}
            onWon={markWon}
            onLost={setLosingDeal}
            onToggleCommit={toggleCommit}
          />
        )}
      </div>

      {showNewDeal && (
        <DealDrawer
          pipeline={pipeline}
          companies={companiesForSelect}
          presetCompanyId={presetCompany?.id}
          users={users}
          onClose={() => { setShowNewDeal(false); setPresetCompany(null) }}
          submitting={createMutation.isPending}
          error={createMutation.error}
          onSubmit={(data) => createMutation.mutate({ ...data, pipeline_id: pipeline.id })}
        />
      )}

      {editingDeal && (
        <EditDealModal
          deal={editingDeal}
          companies={companies}
          users={users}
          onClose={() => setEditingDeal(null)}
          submitting={updateMutation.isPending}
          error={updateMutation.error}
          onSubmit={(data) => updateMutation.mutate({ id: editingDeal.id, data })}
        />
      )}

      {losingDeal && (
        <LostModal
          deal={losingDeal}
          onClose={() => setLosingDeal(null)}
          submitting={closeMutation.isPending}
          onSubmit={(motivo) => closeMutation.mutate({ id: losingDeal.id, data: { status: 'perdido', motivo_perda: motivo } })}
        />
      )}
    </>
  )
}

function DealsBoard({ query, filters, companiesById, usersById, colorMode, stageTintById, onDropStage, onOpen, onEdit, onWon, onLost, onToggleCommit }) {
  const [dragOverStage, setDragOverStage] = useState(null)
  if (query.isLoading) return <p className="state-msg">Carregando…</p>
  if (query.isError) return <p className="state-msg error">Não foi possível carregar o board agora.</p>

  const columns = (query.data?.columns ?? [])
    .filter((col) => !filters.stageId || col.stage.id === filters.stageId)
    .map((col) => ({
      stage: col.stage,
      deals: col.deals.filter((d) =>
        (!filters.status || d.status === filters.status) &&
        (!filters.responsavelId || d.responsavel_id === filters.responsavelId) &&
        (!filters.busca || d.nome.toLowerCase().includes(filters.busca.toLowerCase())),
      ),
    }))

  return (
    <div className="kanban-scroll">
      <div className="kanban">
        {columns.map(({ stage, deals }) => {
          const valorTotal = deals.reduce((sum, d) => sum + (d.valor_previsto ?? 0), 0)
          const valorPonderado = deals.reduce((sum, d) => sum + (d.valor_previsto ?? 0) * ((d.probabilidade ?? stage.probabilidade ?? 0) / 100), 0)
          return (
          <div className="kb-col" key={stage.id}>
            <div className="kb-col-head">
              <div className="kb-col-title">
                <StageLabel nome={stage.nome} mode={colorMode} tint={stageTintById[stage.id]} />
              </div>
              <span className="kb-col-count">{deals.length}</span>
            </div>
            <div
              className={`kb-col-body${dragOverStage === stage.id ? ' drag-over' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setDragOverStage(stage.id) }}
              onDragLeave={() => setDragOverStage(null)}
              onDrop={(e) => {
                e.preventDefault()
                setDragOverStage(null)
                const id = e.dataTransfer.getData('text/deal-id')
                if (id) onDropStage(id, stage.id)
              }}
            >
              {deals.map((d) => (
                <div
                  key={d.id}
                  className="kb-card"
                  draggable
                  onDragStart={(e) => e.dataTransfer.setData('text/deal-id', d.id)}
                  onClick={() => onOpen(d)}
                >
                  <div className="kb-card-name">{d.nome}</div>
                  <div className="kb-card-company">{companiesById[d.company_id] ?? '—'}</div>
                  <div className="kb-card-value">{formatCurrency(d.valor_previsto)}</div>
                  {isStalled(d, stage) && <span className="stalled-tag" title={`Sem interação há mais de ${stage.sla_horas}h`}>⚠ Negócio parado</span>}
                  <div className="kb-card-foot">
                    <span className="kb-card-prob">
                      {d.probabilidade != null ? `${d.probabilidade}%` : ''}
                      {d.commit && <span className="kb-card-commit" title="Compromisso deste mês (Previsão Comercial)">★ Compromisso</span>}
                    </span>
                    <div className="kb-card-tools" onClick={(e) => e.stopPropagation()}>
                      {d.status === 'aberto' && (
                        <button
                          className={`commit-star${d.commit ? ' active' : ''}`}
                          title={d.commit ? 'Remover do Compromisso' : 'Marcar como Compromisso deste mês'}
                          onClick={() => onToggleCommit(d)}
                        >
                          {d.commit ? '★' : '☆'}
                        </button>
                      )}
                      <button title="Editar" onClick={() => onEdit(d)}>✎</button>
                      {d.status === 'aberto' && <button className="won" title="Marcar como ganho" onClick={() => onWon(d)}>✓</button>}
                      {d.status === 'aberto' && <button className="lost" title="Marcar como perdido" onClick={() => onLost(d)}>✕</button>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="kb-col-foot">
              <div className="kb-col-foot-row">
                <span>{formatCurrency(valorTotal)}</span>
                <span className="kb-col-foot-label">Valor total</span>
              </div>
              <div className="kb-col-foot-row">
                <span>{formatCurrency(valorPonderado)} <span className="kb-col-foot-pct">({stage.probabilidade}%)</span></span>
                <span className="kb-col-foot-label">Valor ponderado</span>
              </div>
            </div>
          </div>
          )
        })}
      </div>
    </div>
  )
}

function DealsList({ query, page, setPage, companiesById, usersById, stages, colorMode, stageTintById, onOpen, onEdit, onWon, onLost, onToggleCommit }) {
  const stagesById = Object.fromEntries(stages.map((s) => [s.id, s.nome]))
  const stageObjById = Object.fromEntries(stages.map((s) => [s.id, s]))
  const total = query.data?.total ?? 0
  const items = query.data?.items ?? []
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const queryClient = useQueryClient()
  const [selected, setSelected] = useState({})
  const [showBulkEnroll, setShowBulkEnroll] = useState(false)
  const [showBulkTask, setShowBulkTask] = useState(false)
  const selectedIds = Object.keys(selected).filter((id) => selected[id])
  const selectedDeals = items.filter((d) => selected[d.id])

  function toggleSelect(id) {
    setSelected((s) => ({ ...s, [id]: !s[id] }))
  }
  function toggleSelectAll() {
    const allSelected = items.length > 0 && items.every((d) => selected[d.id])
    const next = {}
    if (!allSelected) items.forEach((d) => { next[d.id] = true })
    setSelected(next)
  }
  async function handleBulkDelete() {
    if (!confirm(`Excluir ${selectedIds.length} negócio(s) selecionado(s)?`)) return
    await Promise.all(selectedIds.map((id) => deleteDeal(id)))
    setSelected({})
    queryClient.invalidateQueries({ queryKey: ['deals'] })
  }

  return (
    <div className="card">
      {selectedIds.length > 0 && (
        <div className="bulk-bar show">
          <span><b>{selectedIds.length}</b> selecionados</span>
          <div className="link-btn">
            <a onClick={() => setShowBulkEnroll(true)}>Inscrever</a>
            <a onClick={() => setShowBulkTask(true)}>+ Tarefa</a>
            <a onClick={handleBulkDelete}>Excluir</a>
          </div>
        </div>
      )}

      {query.isLoading && <p className="state-msg">Carregando…</p>}
      {query.isError && <p className="state-msg error">Não foi possível carregar os negócios agora.</p>}
      {query.data && (
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr>
                <th className="checkbox-col">
                  <input type="checkbox" checked={items.length > 0 && items.every((d) => selected[d.id])} onChange={toggleSelectAll} />
                </th>
                <th>Negócio</th><th>Empresa</th><th>Etapa</th>
                <th style={{ textAlign: 'right' }}>Valor</th><th>Responsável</th><th>Prev. fechamento</th><th className="actions-col"></th>
              </tr>
            </thead>
            <tbody>
              {items.map((d) => (
                <tr key={d.id} className={selected[d.id] ? 'row-selected' : ''} onClick={() => onOpen(d)} style={{ cursor: 'pointer' }}>
                  <td className="checkbox-col" onClick={(e) => e.stopPropagation()}>
                    <input type="checkbox" checked={!!selected[d.id]} onChange={() => toggleSelect(d.id)} />
                  </td>
                  <td><div className="row-title">{d.nome}</div></td>
                  <td>{companiesById[d.company_id] ?? '—'}</td>
                  <td>
                    <StageLabel nome={stagesById[d.stage_id] ?? '—'} mode={colorMode} tint={stageTintById[d.stage_id]} />
                    {isStalled(d, stageObjById[d.stage_id]) && (
                      <span className="stalled-tag" title={`Sem interação há mais de ${stageObjById[d.stage_id].sla_horas}h`}>⚠ Parado</span>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>{formatCurrency(d.valor_previsto)}</td>
                  <td>{usersById[d.responsavel_id] ?? '—'}</td>
                  <td>{d.data_prev_fechamento ? new Date(d.data_prev_fechamento + 'T00:00:00').toLocaleDateString('pt-BR') : '—'}</td>
                  <td className="actions-col" onClick={(e) => e.stopPropagation()}>
                    {d.status === 'aberto' && (
                      <button
                        className={`row-action commit-star${d.commit ? ' active' : ''}`}
                        title={d.commit ? 'Remover do Compromisso' : 'Marcar como Compromisso deste mês'}
                        onClick={() => onToggleCommit(d)}
                      >
                        {d.commit ? '★' : '☆'}
                      </button>
                    )}
                    <button className="row-action" title="Editar" onClick={() => onEdit(d)}>✎</button>
                    {d.status === 'aberto' && <button className="row-action" title="Ganho" onClick={() => onWon(d)}>✓</button>}
                    {d.status === 'aberto' && <button className="row-action" title="Perdido" onClick={() => onLost(d)}>✕</button>}
                  </td>
                </tr>
              ))}
              {items.length === 0 && <tr><td colSpan={8} className="empty-cell">Nenhum negócio encontrado.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      <div className="pagination">
        <span className="info">{total > 0 ? `mostrando ${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, total)} de ${total}` : 'sem resultados'}</span>
        <div className="controls">
          <button className="page-btn" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>‹</button>
          <button className="page-btn" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>›</button>
        </div>
      </div>

      {showBulkEnroll && (
        <EnrollModal
          alvos={selectedIds.map((id) => ({ deal_id: id }))}
          alvoLabel={`${selectedIds.length} negócio(s) selecionado(s)`}
          onClose={() => setShowBulkEnroll(false)}
          onEnrolled={() => setSelected({})}
        />
      )}

      {showBulkTask && (
        <BulkTaskModal
          alvos={selectedDeals.map((d) => ({ deal_id: d.id, company_id: d.company_id, contact_id: d.contact_id }))}
          alvoLabel={`${selectedIds.length} negócio(s) selecionado(s)`}
          onClose={() => setShowBulkTask(false)}
          onCreated={() => setSelected({})}
        />
      )}
    </div>
  )
}

export function DealDrawer({ pipeline, companies, presetCompanyId, presetContactId, users, onClose, onSubmit, submitting, error }) {
  const [form, setForm] = useState({
    nome: '', company_id: presetCompanyId ?? '', contact_id: presetContactId ?? '', responsavel_id: '',
    stage_id: pipeline.stages.find((s) => s.tipo === 'aberta')?.id ?? '',
    valor_previsto: '', probabilidade: '', data_prev_fechamento: '',
  })

  const contactsQuery = useQuery({
    queryKey: ['contacts', 'for-deal', form.company_id],
    queryFn: () => listContacts({ companyId: form.company_id, size: 100 }),
    enabled: Boolean(form.company_id),
  })

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!form.nome.trim() || !form.company_id || !form.responsavel_id || !form.stage_id) return
    onSubmit({
      nome: form.nome.trim(),
      company_id: form.company_id,
      contact_id: form.contact_id || null,
      responsavel_id: form.responsavel_id,
      stage_id: form.stage_id,
      valor_previsto: form.valor_previsto === '' ? null : Number(form.valor_previsto),
      probabilidade: form.probabilidade === '' ? null : parseInt(form.probabilidade, 10),
      data_prev_fechamento: form.data_prev_fechamento || null,
    })
  }

  const openStages = pipeline.stages.filter((s) => s.tipo === 'aberta').sort((a, b) => a.ordem - b.ordem)
  const selectedCompany = companies.find((c) => c.id === form.company_id)

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div><h2>Novo negócio</h2><p>Pipeline "{pipeline.nome}"</p></div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-group">
              <label className="f-label">Nome do negócio <span className="req">*</span></label>
              <input className="f-input" value={form.nome} onChange={set('nome')} placeholder="Ex.: Expansão de frota — filial SP" required />
            </div>
            <div className="f-group">
              <label className="f-label">Empresa <span className="req">*</span></label>
              <select className="f-select" value={form.company_id} onChange={(e) => setForm((f) => ({ ...f, company_id: e.target.value, contact_id: '' }))} required>
                <option value="" disabled>Selecione a empresa</option>
                {companies.map((c) => <option key={c.id} value={c.id}>{c.razao_social}</option>)}
              </select>
            </div>
            <div className="f-group">
              <label className="f-label">Contato <span className="opt">opcional</span></label>
              <select className="f-select" value={form.contact_id} onChange={set('contact_id')} disabled={!form.company_id}>
                <option value="">{form.company_id ? 'Sem contato específico' : 'Selecione uma empresa primeiro'}</option>
                {(contactsQuery.data?.items ?? []).map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
              </select>
            </div>
            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Responsável <span className="req">*</span></label>
                <select className="f-select" value={form.responsavel_id} onChange={set('responsavel_id')} required>
                  <option value="" disabled>Selecione</option>
                  {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
                </select>
              </div>
              <div className="f-group">
                <label className="f-label">Etapa <span className="req">*</span></label>
                <select className="f-select" value={form.stage_id} onChange={set('stage_id')} required>
                  {openStages.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
                </select>
              </div>
            </div>
            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Valor previsto (R$) <span className="opt">opcional</span></label>
                <input className="f-input" type="number" min="0" step="0.01" value={form.valor_previsto} onChange={set('valor_previsto')} placeholder="0,00" />
              </div>
              <div className="f-group">
                <label className="f-label">Probabilidade (%) <span className="opt">opcional</span></label>
                <input className="f-input" type="number" min="0" max="100" value={form.probabilidade} onChange={set('probabilidade')} placeholder="0" />
              </div>
            </div>
            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Previsão de fechamento <span className="opt">opcional</span></label>
                <input className="f-input" type="date" value={form.data_prev_fechamento} onChange={set('data_prev_fechamento')} />
              </div>
              <div className="f-group">
                <label className="f-label">Origem</label>
                <input className="f-input" value={selectedCompany?.origem || 'Sem origem'} disabled />
                <span className="f-hint">Herdada da empresa selecionada — para mudar, edite a origem em Empresas.</span>
              </div>
            </div>
            {error && <p className="state-msg error">Não foi possível salvar. Confira os dados e tente de novo.</p>}
          </div>
          <div className="drawer-foot">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Criar negócio'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function EditDealModal({ deal, companies, users, onClose, onSubmit, submitting, error }) {
  const [form, setForm] = useState({
    nome: deal.nome,
    responsavel_id: deal.responsavel_id,
    valor_previsto: deal.valor_previsto ?? '',
    probabilidade: deal.probabilidade ?? '',
    data_prev_fechamento: deal.data_prev_fechamento ?? '',
    commit: deal.commit ?? false,
  })

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    onSubmit({
      nome: form.nome.trim(),
      responsavel_id: form.responsavel_id,
      valor_previsto: form.valor_previsto === '' ? null : Number(form.valor_previsto),
      probabilidade: form.probabilidade === '' ? null : parseInt(form.probabilidade, 10),
      data_prev_fechamento: form.data_prev_fechamento || null,
      commit: form.commit,
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Editar negócio</h2>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="nome">Nome do negócio</label>
            <input id="nome" required value={form.nome} onChange={set('nome')} />
          </div>
          <div className="field">
            <label htmlFor="responsavel_id">Responsável</label>
            <select id="responsavel_id" value={form.responsavel_id} onChange={set('responsavel_id')}>
              {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
            </select>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="valor_previsto">Valor previsto (R$)</label>
              <input id="valor_previsto" type="number" min="0" step="0.01" value={form.valor_previsto} onChange={set('valor_previsto')} />
            </div>
            <div className="field">
              <label htmlFor="probabilidade">Probabilidade (%)</label>
              <input id="probabilidade" type="number" min="0" max="100" value={form.probabilidade} onChange={set('probabilidade')} />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="data_prev_fechamento">Previsão de fechamento</label>
              <input id="data_prev_fechamento" type="date" value={form.data_prev_fechamento ?? ''} onChange={set('data_prev_fechamento')} />
            </div>
            <div className="field">
              <label htmlFor="origem">Origem</label>
              <input id="origem" value={companies.find((c) => c.id === deal.company_id)?.origem || 'Sem origem'} disabled />
            </div>
          </div>
          <label className="field-checkbox">
            <input type="checkbox" checked={form.commit} onChange={(e) => setForm((f) => ({ ...f, commit: e.target.checked }))} />
            Compromisso — confirmo que este negócio fecha no mês previsto
          </label>
          {error && <p className="state-msg error">Não foi possível salvar. Confira os dados e tente de novo.</p>}
          <div className="modal-actions">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function LostModal({ deal, onClose, onSubmit, submitting }) {
  const [motivo, setMotivo] = useState('')
  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h3>Marcar como perdido</h3>
        <p className="sub">Por que o negócio <strong>{deal.nome}</strong> foi perdido?</p>
        <div className="f-group">
          <label className="f-label">Motivo <span className="req">*</span></label>
          <textarea className="f-input" rows={3} value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Ex.: Fechou com concorrente por preço" />
        </div>
        <div className="row">
          <button className="btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn-danger" disabled={submitting || !motivo.trim()} onClick={() => onSubmit(motivo.trim())}>
            {submitting ? 'Salvando…' : 'Marcar como perdido'}
          </button>
        </div>
      </div>
    </div>
  )
}
