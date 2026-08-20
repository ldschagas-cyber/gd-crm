import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getCentralLeadsResumo, listCentralLeads, setCompanyFunilEstagio, updateCompany,
} from '../api/companies'
import { listTimeline } from '../api/timeline'
import { listUsers } from '../api/users'
import { initials } from '../utils/avatar'
import '../styles/dataTable.css'
import './CentralLeadsPage.css'

const STAGES = [
  { id: 'novo', nome: 'Novo', color: 'var(--hs-blue-soft)', desc: 'Promovido / capturado, ainda sem trabalho comercial' },
  { id: 'qualificando', nome: 'Qualificando', color: 'var(--hs-blue)', desc: 'Discovery em andamento' },
  { id: 'cadencia', nome: 'Em cadência', color: 'var(--hs-purple)', desc: 'Inscrito numa sequência automática de contato' },
  { id: 'mql', nome: 'MQL', color: 'var(--hs-gold)', desc: 'Marketing Qualified — perfil + engajamento cruzaram o corte', manual: true },
  { id: 'sql', nome: 'SQL', color: 'var(--hs-orange)', desc: 'Sales Qualified — vendas aceitou', manual: true },
  { id: 'convertido', nome: 'Convertido em negócio', color: 'var(--hs-orange-deep)', desc: 'Negócio aberto no Pipeline' },
]
const STAGE_BY_ID = Object.fromEntries(STAGES.map((s) => [s.id, s]))
const MANUAL_STAGES = STAGES.filter((s) => s.manual).map((s) => s.id)

function scoreClass(score) {
  return score >= 70 ? 'hi' : (score >= 40 ? 'mid' : 'lo')
}
function isStalled(lead) {
  if (lead.funil_estagio === 'convertido') return false
  const dias = (Date.now() - new Date(lead.ultima_interacao).getTime()) / 86_400_000
  return dias >= 7
}
function fmtRelative(iso) {
  const dias = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
  if (dias <= 0) return 'hoje'
  if (dias === 1) return 'ontem'
  if (dias < 7) return `há ${dias} dias`
  if (dias < 30) return `há ${Math.floor(dias / 7)} semana(s)`
  return `há ${Math.floor(dias / 30)} mês(es)`
}
function fmtDateBR(iso) {
  const d = new Date(iso)
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`
}
const NEXT_ACTION_ICON = { ligacao: '📞', email: '📧', reuniao: '🤝', tarefa: '📋', ia: '✦' }

export default function CentralLeadsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [view, setView] = useState('kanban')
  const [busca, setBusca] = useState('')
  const [responsavelId, setResponsavelId] = useState('')
  const [scoreFilter, setScoreFilter] = useState('')
  const [onlyCadencia, setOnlyCadencia] = useState(false)
  const [onlyStalled, setOnlyStalled] = useState(false)
  const [hideConvertedDays, setHideConvertedDays] = useState('')
  const [infoOpen, setInfoOpen] = useState(true)
  const [selectedLeadId, setSelectedLeadId] = useState(null)
  const [confirmMove, setConfirmMove] = useState(null) // { lead, newStage }

  const usersQuery = useQuery({ queryKey: ['users', 'for-central-leads'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const users = usersQuery.data?.items ?? []
  const usersById = Object.fromEntries(users.map((u) => [u.id, u.nome]))

  const serverFilters = {
    responsavelId: responsavelId || undefined,
    busca: busca || undefined,
    leadScoreMin: scoreFilter === '70' ? 70 : (scoreFilter === '40' ? 40 : undefined),
    emCadencia: onlyCadencia || undefined,
    esconderConvertidosAposDias: hideConvertedDays ? Number(hideConvertedDays) : undefined,
  }

  const leadsQuery = useQuery({ queryKey: ['central-leads', serverFilters], queryFn: () => listCentralLeads(serverFilters) })
  const resumoQuery = useQuery({ queryKey: ['central-leads', 'resumo'], queryFn: getCentralLeadsResumo })

  const allLeads = leadsQuery.data ?? []
  const leads = useMemo(() => {
    let result = allLeads
    if (scoreFilter === '0') result = result.filter((l) => l.lead_score < 40)
    if (onlyStalled) result = result.filter(isStalled)
    return result
  }, [allLeads, scoreFilter, onlyStalled])

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['central-leads'] })
  }

  const moveMutation = useMutation({
    mutationFn: ({ id, stage }) => setCompanyFunilEstagio(id, stage),
    onSuccess: invalidate,
  })

  function attemptMove(lead, newStage) {
    if (lead.funil_estagio === newStage) return
    if (MANUAL_STAGES.includes(newStage)) {
      setConfirmMove({ lead, newStage })
    } else {
      moveMutation.mutate({ id: lead.id, stage: newStage })
    }
  }

  const selectedLead = allLeads.find((l) => l.id === selectedLeadId) ?? null

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Central de Leads</h1>
          <p>
            <span className="mono">{resumoQuery.data?.total_ativos ?? '—'}</span> leads ativos no funil ·{' '}
            <span className="mono">{resumoQuery.data?.parados ?? '—'}</span> parados há 7+ dias ·{' '}
            <span className="mono">{resumoQuery.data?.score_medio ?? '—'}</span> score médio
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
              Funil pós-promoção: Pesquisa de Leads continua separada — a ponte é só a promoção pra Empresa.{' '}
              <b>MQL e SQL são sempre confirmação manual</b>, mesmo com o Lead Score acima do corte. Negócios
              convertidos ficam visíveis aqui como histórico de conversão.
            </span>
            <button onClick={() => setInfoOpen(false)}>Fechar</button>
          </div>
        )}

        <div className="funnel-strip">
          {STAGES.map((s) => (
            <div key={s.id} className="funnel-step" style={{ '--step-color': s.color }} title={s.desc}>
              <span className="dot" />{s.nome}{s.manual && <span className="manual-badge">🔒 manual</span>}
              <span className="n">{resumoQuery.data?.por_estagio?.find((e) => e.estagio === s.id)?.total ?? 0}</span>
            </div>
          ))}
        </div>

        <div className="stat-strip" style={{ marginBottom: 16 }}>
          <div className="stat-tile"><div className="t">Total (com convertidos)</div><div className="v">{resumoQuery.data?.total ?? '—'}</div></div>
          <div className="stat-tile"><div className="t">Ativos</div><div className="v">{resumoQuery.data?.total_ativos ?? '—'}</div></div>
          <div className="stat-tile"><div className="t">Score médio</div><div className="v">{resumoQuery.data?.score_medio ?? '—'}</div></div>
          <div className="stat-tile"><div className="t">Parados 7d+</div><div className="v">{resumoQuery.data?.parados ?? '—'}</div></div>
        </div>

        <div className="filters-bar">
          <div className="search">
            <input type="text" placeholder="Buscar empresa" value={busca} onChange={(e) => setBusca(e.target.value)} />
          </div>
          <select className="filter-select" value={responsavelId} onChange={(e) => setResponsavelId(e.target.value)}>
            <option value="">Todos os responsáveis</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
          <select className="filter-select" value={scoreFilter} onChange={(e) => setScoreFilter(e.target.value)}>
            <option value="">Todo Lead Score</option>
            <option value="70">70+ (quente)</option>
            <option value="40">40+ (morno)</option>
            <option value="0">Abaixo de 40 (frio)</option>
          </select>
          <label className="chip-toggle">
            <input type="checkbox" checked={onlyCadencia} onChange={(e) => setOnlyCadencia(e.target.checked)} />
            Somente em cadência
          </label>
          <label className="chip-toggle">
            <input type="checkbox" checked={onlyStalled} onChange={(e) => setOnlyStalled(e.target.checked)} />
            Somente parados
          </label>
          <select className="filter-select" value={hideConvertedDays} onChange={(e) => setHideConvertedDays(e.target.value)}>
            <option value="">Convertidos: sempre mostrar</option>
            <option value="7">Ocultar convertidos há 7+ dias</option>
            <option value="30">Ocultar convertidos há 30+ dias</option>
          </select>

          <div className="segmented" role="tablist" aria-label="Alternar visualização">
            <button className={view === 'kanban' ? 'active' : ''} onClick={() => setView('kanban')}>Kanban</button>
            <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')}>Lista</button>
          </div>
        </div>

        {leadsQuery.isLoading && <p className="state-msg">Carregando leads…</p>}
        {leadsQuery.isError && <p className="state-msg error">Não foi possível carregar a Central de Leads agora.</p>}

        {leadsQuery.data && view === 'kanban' && (
          <KanbanBoard leads={leads} usersById={usersById} onOpen={setSelectedLeadId} onMove={attemptMove} />
        )}
        {leadsQuery.data && view === 'list' && (
          <ListView leads={leads} usersById={usersById} onOpen={setSelectedLeadId} />
        )}
      </div>

      {selectedLead && (
        <LeadDrawer
          lead={selectedLead}
          users={users}
          onClose={() => setSelectedLeadId(null)}
          onMove={(newStage) => attemptMove(selectedLead, newStage)}
          onConvert={() => {
            navigate('/negocios', { state: { presetCompanyId: selectedLead.id, presetCompanyNome: selectedLead.razao_social } })
          }}
        />
      )}

      {confirmMove && (
        <div className="scrim" onClick={() => setConfirmMove(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-kicker">🔒 Confirmação manual obrigatória</div>
            <h3>Marcar {confirmMove.lead.razao_social} como {STAGE_BY_ID[confirmMove.newStage].nome}?</h3>
            <p className="sub">
              MQL e SQL nunca são atingidos automaticamente — nem quando o Lead Score cruza o corte configurado
              (este lead está em <b>{confirmMove.lead.lead_score} pontos</b>). É sempre uma decisão humana de
              qualificação. Confirma a mudança de estágio?
            </p>
            <div className="row">
              <button className="btn-ghost" onClick={() => setConfirmMove(null)}>Cancelar</button>
              <button
                className="btn-primary"
                disabled={moveMutation.isPending}
                onClick={() => {
                  moveMutation.mutate({ id: confirmMove.lead.id, stage: confirmMove.newStage })
                  setConfirmMove(null)
                }}
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function KanbanBoard({ leads, usersById, onOpen, onMove }) {
  const [dragOverStage, setDragOverStage] = useState(null)

  return (
    <div className="kanban-scroll">
      <div className="kanban">
        {STAGES.map((stage) => {
          const stageLeads = leads.filter((l) => l.funil_estagio === stage.id)
          return (
            <div className="kb-col" style={{ '--stage-color': stage.color }} key={stage.id}>
              <div className="kb-col-head">
                <div className="kb-col-title"><span className="name">{stage.nome}</span>{stage.manual && <span className="manual-badge">🔒 manual</span>}</div>
                <span className="kb-col-count">{stageLeads.length}</span>
              </div>
              <div className="kb-col-sub">{stage.desc}</div>
              <div
                className={`kb-col-body${dragOverStage === stage.id ? ' drag-over' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragOverStage(stage.id) }}
                onDragLeave={() => setDragOverStage(null)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragOverStage(null)
                  const id = e.dataTransfer.getData('text/lead-id')
                  const lead = leads.find((l) => l.id === id)
                  if (lead) onMove(lead, stage.id)
                }}
              >
                {stageLeads.length === 0 && <div className="kb-col-empty">Nenhum lead aqui</div>}
                {stageLeads.map((lead) => (
                  <LeadCard key={lead.id} lead={lead} respNome={usersById[lead.responsavel_id]} onOpen={() => onOpen(lead.id)} />
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function LeadCard({ lead, respNome, onOpen }) {
  const stalled = isStalled(lead)
  return (
    <div
      className={`kb-card${stalled ? ' stalled' : ''}`}
      draggable
      onDragStart={(e) => e.dataTransfer.setData('text/lead-id', lead.id)}
      onClick={onOpen}
    >
      <div className="kb-card-top">
        <div>
          <div className="kb-card-name">{lead.razao_social}</div>
          {lead.segmento && <div className="kb-card-seg">{lead.segmento}{lead.uf ? ` · ${lead.uf}` : ''}</div>}
        </div>
        <span className={`score-badge ${scoreClass(lead.lead_score)}`}>{lead.lead_score}</span>
      </div>
      <div className="kb-card-row">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="10" cy="10" r="7.3" /><path d="M10 5.6v4.4l3 1.8" /></svg>
        {fmtRelative(lead.ultima_interacao)}
      </div>
      {lead.proxima_acao && (
        <div className={`kb-card-next${lead.proxima_acao.tipo === 'ia' ? ' ia' : ''}`}>
          <span>{NEXT_ACTION_ICON[lead.proxima_acao.tipo] ?? '📋'}</span>
          <span>{lead.proxima_acao.texto}{lead.proxima_acao.data ? ` · ${fmtDateBR(lead.proxima_acao.data)}` : ''}</span>
        </div>
      )}
      {lead.cadencia && (
        <div className="kb-card-cadence">🔁 {lead.cadencia.nome} · {lead.cadencia.etapa_atual}/{lead.cadencia.total_etapas}</div>
      )}
      {stalled && (
        <div className="kb-card-stall">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M10 2.5l8 14H2z" /><path d="M10 8v3.4M10 13.6v.1" /></svg>
          Parado — sem interação
        </div>
      )}
      <div className="kb-card-foot">
        <span className="avatar">{initials(respNome)}</span>
        <span className="resp-name">{respNome ?? 'Sem responsável'}</span>
      </div>
    </div>
  )
}

function ListView({ leads, usersById, onOpen }) {
  return (
    <div className="card">
      <div className="table-scroll">
        <table className="data">
          <thead>
            <tr>
              <th>Empresa</th><th>Estágio</th><th>Lead Score</th><th>Última interação</th>
              <th>Próxima ação</th><th>Cadência</th><th>Responsável</th><th></th>
            </tr>
          </thead>
          <tbody>
            {leads.length === 0 && <tr><td colSpan={8} className="empty-cell">Nenhum lead encontrado.</td></tr>}
            {leads.map((lead) => {
              const stage = STAGE_BY_ID[lead.funil_estagio]
              const stalled = isStalled(lead)
              return (
                <tr key={lead.id} onClick={() => onOpen(lead.id)} style={{ cursor: 'pointer' }}>
                  <td><div className="row-title">{lead.razao_social}</div><div className="row-sub">{lead.segmento ?? '—'}{lead.uf ? ` · ${lead.uf}` : ''}</div></td>
                  <td><span className="status-pill" style={{ background: stage.color, color: '#fff' }}><span className="d" style={{ background: 'rgba(255,255,255,.75)' }} />{stage.nome}</span></td>
                  <td><span className={`score-badge ${scoreClass(lead.lead_score)}`}>{lead.lead_score}pt</span></td>
                  <td className="row-sub" style={{ fontFamily: 'var(--font-mono)' }}>{fmtRelative(lead.ultima_interacao)}{stalled ? ' ⚠️' : ''}</td>
                  <td style={{ maxWidth: 220, fontSize: 12.3 }}>
                    {lead.proxima_acao
                      ? <>{lead.proxima_acao.tipo === 'ia' && <span className="ia-tag">✦ IA</span>} {lead.proxima_acao.texto}</>
                      : <span className="row-sub">—</span>}
                  </td>
                  <td>{lead.cadencia ? <span className="kb-card-cadence" style={{ marginTop: 0 }}>🔁 {lead.cadencia.etapa_atual}/{lead.cadencia.total_etapas}</span> : <span className="row-sub">—</span>}</td>
                  <td><div className="row-resp"><span className="avatar">{initials(usersById[lead.responsavel_id])}</span>{usersById[lead.responsavel_id] ?? '—'}</div></td>
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

function LeadDrawer({ lead, users, onClose, onMove, onConvert }) {
  const queryClient = useQueryClient()
  const timelineQuery = useQuery({ queryKey: ['timeline', lead.id, 'mini'], queryFn: () => listTimeline(lead.id, { size: 3 }) })
  const respMutation = useMutation({
    mutationFn: (responsavel_id) => updateCompany(lead.id, { responsavel_id }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['central-leads'] }),
  })

  return (
    <div className="scrim" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>{lead.razao_social}</h2>
            <p>{lead.segmento ?? '—'}{lead.uf ? ` · ${lead.uf}` : ''}{lead.origem ? ` · ${lead.origem}` : ''}</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          <div>
            <div className="dr-section-title">Estágio no funil</div>
            <select className="dr-stage-select" value={lead.funil_estagio} onChange={(e) => onMove(e.target.value)}>
              {STAGES.map((s) => <option key={s.id} value={s.id}>{s.nome}{s.manual ? ' 🔒' : ''}</option>)}
            </select>
          </div>

          <div>
            <div className="dr-section-title">Lead Score</div>
            <div className="score-panel">
              <div className="score-row"><span className="lbl">Fit ICP</span><div className="track"><div className="fill icp" style={{ width: `${lead.score_icp}%` }} /></div><span className="num">{lead.score_icp}</span></div>
              <div className="score-row"><span className="lbl">Engajamento</span><div className="track"><div className="fill eng" style={{ width: `${lead.score_engajamento}%` }} /></div><span className="num">{lead.score_engajamento}</span></div>
              <div className="score-total-row">
                <span>Lead Score (60% ICP + 40% engaj.)</span>
                <span className={`big score-badge ${scoreClass(lead.lead_score)}`}>{lead.lead_score}</span>
              </div>
            </div>
          </div>

          {lead.cadencia && (
            <div>
              <div className="dr-section-title">Cadência ativa</div>
              <div className="cadence-box">
                <div className="name">🔁 {lead.cadencia.nome}</div>
                <div className="cadence-progress-track"><div className="cadence-progress-fill" style={{ width: `${(lead.cadencia.etapa_atual / (lead.cadencia.total_etapas || 1)) * 100}%` }} /></div>
                <div className="step-lbl">Etapa {lead.cadencia.etapa_atual} de {lead.cadencia.total_etapas}</div>
              </div>
            </div>
          )}

          <div>
            <div className="dr-section-title">Próxima ação</div>
            <div className="next-action-box">
              {lead.proxima_acao ? (
                <>
                  {lead.proxima_acao.tipo === 'ia' && <span className="ia-tag">✦ sugestão da IA — revise antes de agir</span>}
                  <span>{lead.proxima_acao.texto}</span>
                  {lead.proxima_acao.data && <span className="row-sub">{new Date(lead.proxima_acao.data).toLocaleDateString('pt-BR')}</span>}
                </>
              ) : <span className="row-sub">Sem próxima ação definida.</span>}
            </div>
          </div>

          <div>
            <div className="dr-section-title">Linha do tempo (últimas interações)</div>
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
            <div className="dr-section-title">Responsável</div>
            <select
              className="filter-select"
              style={{ width: '100%' }}
              value={lead.responsavel_id ?? ''}
              onChange={(e) => respMutation.mutate(e.target.value || null)}
            >
              <option value="">Sem responsável</option>
              {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
            </select>
          </div>
        </div>
        <div className="drawer-foot">
          <button className="btn-ghost" onClick={onClose}>Fechar</button>
          {lead.funil_estagio === 'sql' && <button className="btn-primary" onClick={onConvert}>Converter em negócio →</button>}
        </div>
      </div>
    </div>
  )
}
