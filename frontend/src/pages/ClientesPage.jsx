import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createCheckin, getClientesResumo, getCompanyHealth, listClientes, listOnboarding,
  setCompanyCs, setCompanyCsFase, setOnboardingItemStatus,
} from '../api/customerSuccess'
import { cancelarAssinatura, renovarAssinatura } from '../api/subscriptions'
import { listTimeline } from '../api/timeline'
import { listUsers } from '../api/users'
import { initials } from '../utils/avatar'
import '../styles/dataTable.css'
import './ClientesPage.css'

const FASES = [
  { id: 'implantacao', nome: 'Implantação', color: 'var(--hs-blue)', desc: 'Negócio ganho — checklist de onboarding em andamento' },
  { id: 'ativo', nome: 'Ativo', color: 'var(--hs-purple)', desc: 'Onboarding concluído — operação estável' },
  { id: 'em_risco', nome: 'Em risco', color: 'var(--hs-orange)', desc: 'Health Score abaixo do corte ou renovação próxima sem contato' },
  { id: 'em_expansao', nome: 'Em expansão', color: 'var(--hs-gold)', desc: 'Negócio de upsell aberto para este cliente' },
  { id: 'churn', nome: 'Encerrado', color: 'var(--ink-faint)', desc: 'Contrato cancelado — fica visível para auditoria', terminal: true },
]
const FASE_BY_ID = Object.fromEntries(FASES.map((f) => [f.id, f]))
const TABS = [
  { id: 'geral', label: 'Visão geral' },
  { id: 'implantacao', label: 'Implantação' },
  { id: 'saude', label: 'Saúde' },
  { id: 'renovacao', label: 'Renovação & Expansão' },
]

function healthClass(score) {
  if (score == null) return 'lo'
  return score >= 70 ? 'hi' : (score >= 40 ? 'mid' : 'lo')
}
function fmtRelative(iso) {
  if (!iso) return '—'
  const dias = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
  if (dias <= 0) return 'hoje'
  if (dias === 1) return 'ontem'
  if (dias < 7) return `há ${dias} dias`
  if (dias < 30) return `há ${Math.floor(dias / 7)} semana(s)`
  return `há ${Math.floor(dias / 30)} mês(es)`
}
function fmtDateBR(d) {
  return d ? new Date(`${d}T00:00:00`).toLocaleDateString('pt-BR') : '—'
}
function fmtMoney(v) {
  return (v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}
function diasAte(d) {
  if (!d) return null
  return Math.round((new Date(`${d}T00:00:00`).getTime() - Date.now()) / 86_400_000)
}
function apiErrorMessage(error, fallback) {
  return error?.response?.data?.error?.message ?? fallback
}

export default function ClientesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [view, setView] = useState('kanban')
  const [busca, setBusca] = useState('')
  const [csResponsavelId, setCsResponsavelId] = useState('')
  const [renovacaoAteDias, setRenovacaoAteDias] = useState('')
  const [healthFilter, setHealthFilter] = useState('')
  const [infoOpen, setInfoOpen] = useState(true)
  const [selectedId, setSelectedId] = useState(null)
  const [churnHint, setChurnHint] = useState(false)

  const usersQuery = useQuery({ queryKey: ['users', 'for-clientes'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const users = usersQuery.data?.items ?? []
  const usersById = Object.fromEntries(users.map((u) => [u.id, u.nome]))

  const serverFilters = {
    csResponsavelId: csResponsavelId || undefined,
    busca: busca || undefined,
    renovacaoAteDias: renovacaoAteDias ? Number(renovacaoAteDias) : undefined,
  }
  const clientesQuery = useQuery({ queryKey: ['clientes', serverFilters], queryFn: () => listClientes(serverFilters) })
  const resumoQuery = useQuery({ queryKey: ['clientes', 'resumo'], queryFn: getClientesResumo })

  const allClientes = clientesQuery.data ?? []
  const clientes = healthFilter
    ? allClientes.filter((c) => {
      if (healthFilter === '70') return (c.health_score ?? 0) >= 70
      if (healthFilter === '40') return (c.health_score ?? 0) >= 40 && (c.health_score ?? 0) < 70
      return (c.health_score ?? 0) < 40
    })
    : allClientes

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['clientes'] })
  }

  const moveMutation = useMutation({
    mutationFn: ({ id, fase }) => setCompanyCsFase(id, fase),
    onSuccess: invalidate,
  })

  function attemptMove(cliente, novaFase) {
    if (cliente.cs_fase === novaFase) return
    if (novaFase === 'churn') {
      setChurnHint(true)
      return
    }
    moveMutation.mutate({ id: cliente.id, fase: novaFase })
  }

  const selectedCliente = allClientes.find((c) => c.id === selectedId) ?? null

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Clientes</h1>
          <p>
            <span className="mono">{resumoQuery.data?.total ?? '—'}</span> clientes ativos ·{' '}
            <span className="mono">{fmtMoney(resumoQuery.data?.mrr_total)}</span> MRR ·{' '}
            <span className="mono">{resumoQuery.data?.em_risco ?? '—'}</span> em risco
          </p>
        </div>
      </header>

      <div className="content">
        {infoOpen && (
          <div className="info-banner">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7">
              <circle cx="10" cy="10" r="7.3" /><path d="M10 9v4.4M10 6.6v.1" />
            </svg>
            <span>
              Customer Success começa quando um <b>Negócio é ganho</b> — o cliente entra automaticamente na fase
              Implantação. <b>Encerramento (churn) só acontece cancelando a Assinatura</b> na aba Renovação &
              Expansão, nunca arrastando o card direto pra cá.
            </span>
            <button onClick={() => setInfoOpen(false)}>Fechar</button>
          </div>
        )}

        <div className="funnel-strip">
          {FASES.map((f) => (
            <div key={f.id} className="funnel-step" style={{ background: f.color }} title={f.desc}>
              {f.nome}{f.terminal && <span className="manual-badge">🔒 manual</span>}
              <span className="n">{resumoQuery.data?.por_fase?.find((e) => e.fase === f.id)?.total ?? 0}</span>
            </div>
          ))}
        </div>

        <div className="stat-strip" style={{ marginBottom: 16 }}>
          <div className="stat-tile"><div className="t">Clientes ativos</div><div className="v">{resumoQuery.data?.total ?? '—'}</div></div>
          <div className="stat-tile"><div className="t">MRR total</div><div className="v">{fmtMoney(resumoQuery.data?.mrr_total)}</div></div>
          <div className="stat-tile"><div className="t">ARR projetado</div><div className="v">{fmtMoney(resumoQuery.data?.arr_total)}</div></div>
          <div className="stat-tile"><div className="t">Health médio</div><div className="v">{resumoQuery.data?.health_medio ?? '—'}pt</div></div>
          <div className="stat-tile"><div className="t">Em risco</div><div className="v" style={{ color: 'var(--serious, #ec835a)' }}>{resumoQuery.data?.em_risco ?? '—'}</div></div>
          <div className="stat-tile"><div className="t">Renovação 60d</div><div className="v">{resumoQuery.data?.renovacao_60d ?? '—'}</div></div>
        </div>

        <div className="filters-bar">
          <div className="search">
            <input type="text" placeholder="Buscar cliente" value={busca} onChange={(e) => setBusca(e.target.value)} />
          </div>
          <select className="filter-select" value={csResponsavelId} onChange={(e) => setCsResponsavelId(e.target.value)}>
            <option value="">Todos os CSMs</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
          <select className="filter-select" value={healthFilter} onChange={(e) => setHealthFilter(e.target.value)}>
            <option value="">Todo Health Score</option>
            <option value="70">70+ (saudável)</option>
            <option value="40">40-69 (atenção)</option>
            <option value="0">Abaixo de 40 (em risco)</option>
          </select>
          <select className="filter-select" value={renovacaoAteDias} onChange={(e) => setRenovacaoAteDias(e.target.value)}>
            <option value="">Toda renovação</option>
            <option value="30">Em até 30 dias</option>
            <option value="60">Em até 60 dias</option>
            <option value="90">Em até 90 dias</option>
          </select>

          <div className="segmented" role="tablist" aria-label="Alternar visualização">
            <button className={view === 'kanban' ? 'active' : ''} onClick={() => setView('kanban')}>Kanban</button>
            <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')}>Lista</button>
          </div>
        </div>

        {clientesQuery.isLoading && <p className="state-msg">Carregando clientes…</p>}
        {clientesQuery.isError && <p className="state-msg error">Não foi possível carregar os Clientes agora.</p>}

        {clientesQuery.data && view === 'kanban' && (
          <KanbanBoard clientes={clientes} usersById={usersById} onOpen={setSelectedId} onMove={attemptMove} />
        )}
        {clientesQuery.data && view === 'list' && (
          <ListView clientes={clientes} usersById={usersById} onOpen={setSelectedId} />
        )}
      </div>

      {selectedCliente && (
        <ClienteDrawer
          cliente={selectedCliente}
          users={users}
          onClose={() => setSelectedId(null)}
          onMove={(novaFase) => attemptMove(selectedCliente, novaFase)}
          onOpenExpansao={() => {
            navigate('/negocios', {
              state: { presetCompanyId: selectedCliente.id, presetCompanyNome: selectedCliente.razao_social, presetTipo: 'expansao' },
            })
          }}
        />
      )}

      {churnHint && (
        <div className="scrim" onClick={() => setChurnHint(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-kicker">🔒 Encerramento não é uma troca de fase direta</div>
            <h3>Cancele a Assinatura para encerrar este cliente</h3>
            <p className="sub">
              A fase "Encerrado" reflete o cancelamento da Assinatura (Receita Recorrente), não o contrário — assim
              o Customer Success nunca mostra um cliente como encerrado enquanto ele ainda está sendo cobrado.
              Abra o cliente e use a aba <b>Renovação & Expansão</b> para cancelar a Assinatura.
            </p>
            <div className="row">
              <button className="btn-primary" onClick={() => setChurnHint(false)}>Entendi</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function KanbanBoard({ clientes, usersById, onOpen, onMove }) {
  const [dragOverFase, setDragOverFase] = useState(null)

  return (
    <div className="kanban-scroll">
      <div className="kanban">
        {FASES.map((fase) => {
          const faseClientes = clientes.filter((c) => c.cs_fase === fase.id)
          return (
            <div className="kb-col" style={{ '--stage-color': fase.color }} key={fase.id}>
              <div className="kb-col-head">
                <div className="kb-col-title"><span className="name">{fase.nome}</span>{fase.terminal && <span className="manual-badge">🔒</span>}</div>
                <span className="kb-col-count">{faseClientes.length}</span>
              </div>
              <div className="kb-col-sub">{fase.desc}</div>
              <div
                className={`kb-col-body${dragOverFase === fase.id ? ' drag-over' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragOverFase(fase.id) }}
                onDragLeave={() => setDragOverFase(null)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragOverFase(null)
                  const id = e.dataTransfer.getData('text/cliente-id')
                  const cliente = clientes.find((c) => c.id === id)
                  if (cliente) onMove(cliente, fase.id)
                }}
              >
                {faseClientes.length === 0 && <div className="kb-col-empty">Nenhum cliente aqui</div>}
                {faseClientes.map((cliente) => (
                  <ClienteCard key={cliente.id} cliente={cliente} csmNome={usersById[cliente.cs_responsavel_id]} onOpen={() => onOpen(cliente.id)} />
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ClienteCard({ cliente, csmNome, onOpen }) {
  const isRisco = cliente.cs_fase === 'em_risco'
  return (
    <div
      className={`kb-card${isRisco ? ' stalled' : ''}`}
      draggable
      onDragStart={(e) => e.dataTransfer.setData('text/cliente-id', cliente.id)}
      onClick={onOpen}
    >
      <div className="kb-card-top">
        <div>
          <div className="kb-card-name">{cliente.razao_social}</div>
          {cliente.segmento && <div className="kb-card-seg">{cliente.segmento}{cliente.uf ? ` · ${cliente.uf}` : ''}</div>}
        </div>
        <span className={`score-badge ${healthClass(cliente.health_score)}`}>{cliente.health_score ?? '—'}</span>
      </div>
      <div className="kb-card-row">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="10" cy="10" r="7.3" /><path d="M10 5.6v4.4l3 1.8" /></svg>
        {fmtRelative(cliente.ultima_interacao)}
        <span className="kb-card-mrr">{fmtMoney(cliente.assinatura?.valor_mensal)}/mês</span>
      </div>
      {cliente.cs_fase === 'implantacao' && (
        <div className="kb-card-progress">
          <div className="track"><div className="fill" style={{ width: `${cliente.onboarding_progresso}%` }} /></div>
          <div className="lbl">Onboarding: {cliente.onboarding_progresso}% concluído</div>
        </div>
      )}
      {cliente.expansao_aberta && <div className="kb-card-cadence">↗ Negócio de expansão em andamento</div>}
      <div className="kb-card-foot">
        <span className="avatar">{initials(csmNome)}</span>
        <span className="resp-name">{csmNome ?? 'Sem CSM'}</span>
      </div>
    </div>
  )
}

function ListView({ clientes, usersById, onOpen }) {
  return (
    <div className="card">
      <div className="table-scroll">
        <table className="data">
          <thead>
            <tr>
              <th>Cliente</th><th>Fase</th><th>Health</th><th>MRR</th><th>Renovação</th><th>CSM</th><th></th>
            </tr>
          </thead>
          <tbody>
            {clientes.length === 0 && <tr><td colSpan={7} className="empty-cell">Nenhum cliente encontrado.</td></tr>}
            {clientes.map((cliente) => {
              const fase = FASE_BY_ID[cliente.cs_fase]
              const du = diasAte(cliente.assinatura?.data_renovacao)
              return (
                <tr key={cliente.id} onClick={() => onOpen(cliente.id)} style={{ cursor: 'pointer' }}>
                  <td><div className="row-title">{cliente.razao_social}</div><div className="row-sub">{cliente.segmento ?? '—'}{cliente.uf ? ` · ${cliente.uf}` : ''}</div></td>
                  <td><span className="status-pill" style={{ background: fase.color, color: '#fff' }}><span className="d" style={{ background: 'rgba(255,255,255,.75)' }} />{fase.nome}</span></td>
                  <td><span className={`score-badge ${healthClass(cliente.health_score)}`}>{cliente.health_score ?? '—'}pt</span></td>
                  <td className="row-sub" style={{ fontFamily: 'var(--font-mono)' }}>{fmtMoney(cliente.assinatura?.valor_mensal)}</td>
                  <td className="row-sub" style={{ fontFamily: 'var(--font-mono)' }}>
                    {cliente.assinatura?.data_renovacao ? `${fmtDateBR(cliente.assinatura.data_renovacao)} (${du}d)` : '—'}
                  </td>
                  <td><div className="row-resp"><span className="avatar">{initials(usersById[cliente.cs_responsavel_id])}</span>{usersById[cliente.cs_responsavel_id] ?? '—'}</div></td>
                  <td className="actions-col"><button className="icon-btn" title="Abrir">→</button></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ClienteDrawer({ cliente, users, onClose, onMove, onOpenExpansao }) {
  const [tab, setTab] = useState('geral')
  const queryClient = useQueryClient()

  const respMutation = useMutation({
    mutationFn: (csResponsavelId) => setCompanyCs(cliente.id, csResponsavelId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clientes'] }),
  })

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show cs-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>{cliente.razao_social}</h2>
            <p>{cliente.segmento ?? '—'}{cliente.uf ? ` · ${cliente.uf}` : ''}</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>

        <div className="dr-tabs" role="tablist">
          {TABS.map((t) => (
            <button key={t.id} className={`dr-tab${tab === t.id ? ' active' : ''}`} onClick={() => setTab(t.id)}>{t.label}</button>
          ))}
        </div>

        <div className="drawer-body">
          {tab === 'geral' && (
            <VisaoGeralTab cliente={cliente} users={users} onMove={onMove} onSetResponsavel={(id) => respMutation.mutate(id)} />
          )}
          {tab === 'implantacao' && <ImplantacaoTab cliente={cliente} onMove={onMove} />}
          {tab === 'saude' && <SaudeTab cliente={cliente} />}
          {tab === 'renovacao' && <RenovacaoTab cliente={cliente} onOpenExpansao={onOpenExpansao} />}
        </div>

        <div className="drawer-foot">
          <button className="btn-ghost" onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  )
}

function VisaoGeralTab({ cliente, users, onMove, onSetResponsavel }) {
  const timelineQuery = useQuery({ queryKey: ['timeline', cliente.id, 'mini'], queryFn: () => listTimeline(cliente.id, { size: 5 }) })
  const du = diasAte(cliente.assinatura?.data_renovacao)

  return (
    <>
      <div>
        <div className="dr-section-title">Fase de Customer Success</div>
        <select className="dr-stage-select" value={cliente.cs_fase} onChange={(e) => onMove(e.target.value)}>
          {FASES.map((f) => <option key={f.id} value={f.id} disabled={f.terminal && f.id !== cliente.cs_fase}>{f.nome}{f.terminal ? ' 🔒' : ''}</option>)}
        </select>
      </div>

      <div className="cs-kpi-grid">
        <div className="cs-kpi-card">
          <div className="t">Health Score</div>
          <div className={`v ${(cliente.health_score ?? 0) >= 70 ? 'good' : ''}`}>{cliente.health_score ?? '—'}pt</div>
        </div>
        <div className="cs-kpi-card">
          <div className="t">MRR</div>
          <div className="v">{fmtMoney(cliente.assinatura?.valor_mensal)}</div>
        </div>
        <div className="cs-kpi-card">
          <div className="t">Cliente desde</div>
          <div className="v sm">{fmtDateBR(cliente.assinatura?.data_inicio)}</div>
        </div>
        <div className="cs-kpi-card">
          <div className="t">Próxima renovação</div>
          <div className="v sm">{fmtDateBR(cliente.assinatura?.data_renovacao)}</div>
          {du != null && <div className="d">{du >= 0 ? `em ${du} dias` : `vencida há ${-du} dias`}</div>}
        </div>
      </div>

      <div>
        <div className="dr-section-title">Linha do tempo recente</div>
        {timelineQuery.isLoading && <p className="state-msg">Carregando…</p>}
        {timelineQuery.data && timelineQuery.data.items.length === 0 && <p className="row-sub">Nenhuma interação registrada ainda.</p>}
        {timelineQuery.data && timelineQuery.data.items.length > 0 && (
          <div className="timeline-mini">
            {timelineQuery.data.items.map((ev) => (
              <div className="tl-item" key={ev.id}>
                <div className="tl-dot" />
                <div><div className="tt">{ev.titulo}</div><div className="td">{fmtRelative(ev.created_at)}</div></div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <div className="dr-section-title">CSM responsável</div>
        <select className="filter-select" style={{ width: '100%' }} value={cliente.cs_responsavel_id ?? ''} onChange={(e) => onSetResponsavel(e.target.value || null)}>
          <option value="">Sem CSM</option>
          {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
        </select>
      </div>
    </>
  )
}

function ImplantacaoTab({ cliente, onMove }) {
  const queryClient = useQueryClient()
  const itemsQuery = useQuery({ queryKey: ['onboarding', cliente.id], queryFn: () => listOnboarding(cliente.id) })
  const toggleMutation = useMutation({
    mutationFn: ({ itemId, status }) => setOnboardingItemStatus(cliente.id, itemId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding', cliente.id] })
      queryClient.invalidateQueries({ queryKey: ['clientes'] })
    },
  })

  const items = itemsQuery.data ?? []
  const progresso = items.length ? Math.round(items.filter((i) => i.status === 'concluido').length / items.length * 100) : 100

  return (
    <div>
      <div className="dr-section-title">Checklist de onboarding — {progresso}% concluído</div>
      <div className="cl-progress-track"><div className="cl-progress-fill" style={{ width: `${progresso}%` }} /></div>
      {itemsQuery.isLoading && <p className="state-msg">Carregando…</p>}
      <div className="checklist">
        {items.map((item) => (
          <div className={`cl-item${item.status === 'concluido' ? ' done' : ''}`} key={item.id}>
            <button
              type="button"
              className={`cl-check${item.status === 'concluido' ? ' done' : ''}`}
              onClick={() => toggleMutation.mutate({ itemId: item.id, status: item.status === 'concluido' ? 'pendente' : 'concluido' })}
              aria-label={item.status === 'concluido' ? 'Marcar como pendente' : 'Marcar como concluído'}
            >
              {item.status === 'concluido' && <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M4 10l4 4 8-9" /></svg>}
            </button>
            <div>
              <div className="cl-title">{item.titulo}</div>
              <div className="cl-meta">{item.status === 'concluido' ? 'Concluído' : 'Pendente'}</div>
            </div>
          </div>
        ))}
      </div>
      {progresso === 100 && items.length > 0 && cliente.cs_fase === 'implantacao' && (
        <button className="btn-primary" style={{ marginTop: 12 }} onClick={() => onMove('ativo')}>
          Concluir implantação → mover para Ativo
        </button>
      )}
    </div>
  )
}

function SaudeTab({ cliente }) {
  const queryClient = useQueryClient()
  const healthQuery = useQuery({ queryKey: ['health', cliente.id], queryFn: () => getCompanyHealth(cliente.id) })
  const [usoPercebido, setUsoPercebido] = useState(50)
  const [satisfacao, setSatisfacao] = useState(50)
  const [notas, setNotas] = useState('')

  const checkinMutation = useMutation({
    mutationFn: () => createCheckin(cliente.id, { uso_percebido: usoPercebido, satisfacao, notas: notas || undefined }),
    onSuccess: () => {
      setNotas('')
      queryClient.invalidateQueries({ queryKey: ['health', cliente.id] })
      queryClient.invalidateQueries({ queryKey: ['clientes'] })
    },
  })

  const h = healthQuery.data
  return (
    <>
      {h && (
        <>
          <div className="info-banner" style={{ marginBottom: 0 }}>
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="10" cy="10" r="7.3" /><path d="M10 9v4.4M10 6.6v.1" /></svg>
            <span>Health Score = <b>30% Engajamento</b> + <b>25% Uso</b> + <b>20% Satisfação</b> + <b>25% Financeiro</b>.</span>
          </div>
          <div className="score-panel">
            <div className="score-row"><span className="lbl">Engajamento</span><div className="track"><div className="fill eng" style={{ width: `${h.engajamento}%` }} /></div><span className="num">{h.engajamento}</span></div>
            <div className="score-row"><span className="lbl">Uso/adoção</span><div className="track"><div className="fill icp" style={{ width: `${h.uso}%` }} /></div><span className="num">{h.uso}</span></div>
            <div className="score-row"><span className="lbl">Satisfação</span><div className="track"><div className="fill eng" style={{ width: `${h.satisfacao}%` }} /></div><span className="num">{h.satisfacao}</span></div>
            <div className="score-row"><span className="lbl">Financeiro</span><div className="track"><div className="fill icp" style={{ width: `${h.financeiro}%` }} /></div><span className="num">{h.financeiro}</span></div>
            <div className="score-total-row"><span>Health Score</span><span className={`big score-badge ${healthClass(h.score)}`}>{h.score}</span></div>
          </div>
          {h.breakdown?.length > 0 && (
            <ul className="cs-breakdown-list">
              {h.breakdown.map((b, i) => <li key={i}><span>{b.criterio} — {b.valor}</span><span className={b.pontos < 0 ? 'neg' : ''}>{b.pontos > 0 ? `+${b.pontos}` : b.pontos}</span></li>)}
            </ul>
          )}
          {h.precisa_checkin && (
            <div className="info-banner warn">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M10 2.5l8 14H2z" /><path d="M10 8v3.4M10 13.6v.1" /></svg>
              <span>Sem check-in recente — o pilar de Uso/Satisfação está usando um valor neutro por falta de dado.</span>
            </div>
          )}
        </>
      )}

      <div className="next-action-box">
        <div className="dr-section-title" style={{ marginBottom: 4 }}>Registrar check-in</div>
        <div className="f-group">
          <label className="f-label">Uso percebido ({usoPercebido}%)</label>
          <input type="range" min="0" max="100" value={usoPercebido} onChange={(e) => setUsoPercebido(Number(e.target.value))} />
        </div>
        <div className="f-group">
          <label className="f-label">Satisfação ({satisfacao}%)</label>
          <input type="range" min="0" max="100" value={satisfacao} onChange={(e) => setSatisfacao(Number(e.target.value))} />
        </div>
        <div className="f-group">
          <label className="f-label">Notas <span className="opt">opcional</span></label>
          <textarea className="f-textarea" rows={2} value={notas} onChange={(e) => setNotas(e.target.value)} placeholder="Ex.: time do cliente reportou uso diário do módulo de cotação..." />
        </div>
        <button className="btn-primary" disabled={checkinMutation.isPending} onClick={() => checkinMutation.mutate()}>
          {checkinMutation.isPending ? 'Salvando…' : 'Salvar check-in'}
        </button>
      </div>
    </>
  )
}

function RenovacaoTab({ cliente, onOpenExpansao }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [showCancel, setShowCancel] = useState(false)
  const [motivo, setMotivo] = useState('')
  const a = cliente.assinatura
  const du = diasAte(a?.data_renovacao)

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['clientes'] })
  }
  const renovarMutation = useMutation({ mutationFn: () => renovarAssinatura(a.id, {}), onSuccess: invalidate })
  const cancelarMutation = useMutation({
    mutationFn: () => cancelarAssinatura(a.id, { motivo_cancelamento: motivo || undefined }),
    onSuccess: () => { setShowCancel(false); invalidate() },
  })

  if (!a) {
    return (
      <div className="info-banner">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="10" cy="10" r="7.3" /><path d="M10 9v4.4M10 6.6v.1" /></svg>
        <span>
          Este cliente ainda não tem Assinatura cadastrada.{' '}
          <button style={{ background: 'none', border: 'none', color: 'var(--link)', cursor: 'pointer', textDecoration: 'underline', padding: 0, font: 'inherit' }} onClick={() => navigate('/receita-recorrente')}>
            Cadastrar em Receita Recorrente →
          </button>
        </span>
      </div>
    )
  }

  return (
    <>
      <div className="cs-renewal-box">
        <div className="cs-renewal-top">
          <span className="amt">{fmtMoney(a.valor_mensal)}<span className="unit"> /mês</span></span>
          {a.data_renovacao && (
            <span className={`cs-renewal-countdown ${du <= 30 ? 'urgent' : (du <= 60 ? 'soon' : 'ok')}`}>
              {du >= 0 ? `renova em ${du}d` : `vencida há ${-du}d`}
            </span>
          )}
        </div>
        <div className="cs-renewal-grid">
          <div><div className="k">Plano</div><div className="v">{a.nome_plano}</div></div>
          <div><div className="k">Status</div><div className="v">{a.status}</div></div>
          <div><div className="k">Início do contrato</div><div className="v">{fmtDateBR(a.data_inicio)}</div></div>
          <div><div className="k">Próxima renovação</div><div className="v">{fmtDateBR(a.data_renovacao)}</div></div>
        </div>
        {a.status === 'ativa' && (
          <div className="row" style={{ marginTop: 10 }}>
            {a.ciclo_renovacao_meses && (
              <button className="btn-ghost sm" disabled={renovarMutation.isPending} onClick={() => renovarMutation.mutate()}>
                Confirmar renovação
              </button>
            )}
            <button className="btn-ghost sm" style={{ color: 'var(--serious, #ec835a)' }} onClick={() => setShowCancel(true)}>
              Cancelar assinatura
            </button>
          </div>
        )}
      </div>

      <div>
        <div className="dr-section-title">Negócio de expansão</div>
        {cliente.expansao_aberta ? (
          <p className="row-sub">Já existe um negócio de expansão aberto para este cliente — acompanhe em Negócios.</p>
        ) : (
          <button className="btn-primary" onClick={onOpenExpansao}>Abrir negócio de expansão →</button>
        )}
      </div>

      {showCancel && (
        <div className="scrim" onClick={() => setShowCancel(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-kicker">🔒 Isto encerra o cliente no Customer Success</div>
            <h3>Cancelar a assinatura de {cliente.razao_social}?</h3>
            <div className="f-group">
              <label className="f-label">Motivo <span className="opt">opcional</span></label>
              <textarea className="f-textarea" rows={2} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
            </div>
            {cancelarMutation.isError && <p className="state-msg error">{apiErrorMessage(cancelarMutation.error, 'Não foi possível cancelar agora.')}</p>}
            <div className="row">
              <button className="btn-ghost" onClick={() => setShowCancel(false)}>Voltar</button>
              <button className="btn-primary" disabled={cancelarMutation.isPending} onClick={() => cancelarMutation.mutate()}>
                {cancelarMutation.isPending ? 'Cancelando…' : 'Confirmar cancelamento'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
