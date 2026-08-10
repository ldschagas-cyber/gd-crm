import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { closeDeal, getDeal, moveDealStage, updateDeal } from '../api/deals'
import { getCompany } from '../api/companies'
import { getContact } from '../api/contacts'
import { getPipeline } from '../api/pipelines'
import { listUsers } from '../api/users'
import { listTasks, completeTask } from '../api/tasks'
import { listDealTimeline, addDealTimelineNote } from '../api/timeline'
import EnrollModal from '../components/EnrollModal.jsx'
import TimelineComposer from '../components/TimelineComposer.jsx'
import { useSoftphone } from '../context/SoftphoneContext.jsx'
import '../styles/dataTable.css'
import '../styles/detailPage.css'
import './DealDetailPage.css'

const MOTIVOS_PERDA = ['Preço', 'Concorrência', 'Não é o momento', 'Sem orçamento', 'Perda de contato', 'Outro']

function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}
function formatCurrency(v) {
  return v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}
function tipoGlyph(tipo) {
  const map = { nota: '📝', ligacao: '📞', email: '✉️', reuniao: '📅', pipeline: '📈', tarefa: '✔️', cadastro: '●' }
  return map[tipo] ?? '●'
}

export default function DealDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { conectado: chamadasConectadas, call: ligar } = useSoftphone()
  const [showLostModal, setShowLostModal] = useState(false)
  const [showEnrollModal, setShowEnrollModal] = useState(false)

  const dealQuery = useQuery({ queryKey: ['deals', 'detail', id], queryFn: () => getDeal(id) })
  const deal = dealQuery.data

  const pipelineQuery = useQuery({
    queryKey: ['pipelines', 'detail', deal?.pipeline_id],
    queryFn: () => getPipeline(deal.pipeline_id),
    enabled: Boolean(deal),
  })
  const companyQuery = useQuery({
    queryKey: ['companies', 'detail-mini', deal?.company_id],
    queryFn: () => getCompany(deal.company_id),
    enabled: Boolean(deal),
  })
  const contactQuery = useQuery({
    queryKey: ['contacts', 'detail-mini', deal?.contact_id],
    queryFn: () => getContact(deal.contact_id),
    enabled: Boolean(deal?.contact_id),
  })
  const usersQuery = useQuery({ queryKey: ['users', 'for-assign'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const timelineQuery = useQuery({ queryKey: ['deal-timeline', id], queryFn: () => listDealTimeline(id) })
  const tasksQuery = useQuery({ queryKey: ['tasks', 'mini-deal', id], queryFn: () => listTasks({ dealId: id, size: 20 }) })

  const usersById = Object.fromEntries((usersQuery.data?.items ?? []).map((u) => [u.id, u.nome]))

  function invalidateDeal() {
    queryClient.invalidateQueries({ queryKey: ['deals', 'detail', id] })
  }

  const updateMutation = useMutation({ mutationFn: (data) => updateDeal(id, data), onSuccess: invalidateDeal })
  const stageMutation = useMutation({ mutationFn: (stageId) => moveDealStage(id, stageId), onSuccess: invalidateDeal })
  const closeMutation = useMutation({
    mutationFn: (data) => closeDeal(id, data),
    onSuccess: () => { setShowLostModal(false); invalidateDeal() },
  })
  const noteMutation = useMutation({
    mutationFn: (data) => addDealTimelineNote(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deal-timeline', id] }),
  })
  const completeTaskMutation = useMutation({
    mutationFn: completeTask,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks', 'mini-deal', id] }),
  })

  const [form, setForm] = useState(null)
  useEffect(() => {
    if (deal) {
      setForm({
        valor_previsto: deal.valor_previsto ?? '',
        probabilidade: deal.probabilidade ?? '',
        data_prev_fechamento: deal.data_prev_fechamento ?? '',
        commit: deal.commit ?? false,
      })
    }
  }, [deal])

  if (dealQuery.isLoading) return <div className="content"><p className="state-msg">Carregando…</p></div>
  if (dealQuery.isError) return <div className="content"><p className="state-msg error">Negócio não encontrado.</p></div>

  const stages = pipelineQuery.data?.stages ?? []
  const currentStage = stages.find((s) => s.id === deal.stage_id)
  const company = companyQuery.data
  const contact = contactQuery.data

  function handleSaveDetails() {
    updateMutation.mutate({
      valor_previsto: form.valor_previsto === '' ? null : Number(form.valor_previsto),
      probabilidade: form.probabilidade === '' ? null : Number(form.probabilidade),
      data_prev_fechamento: form.data_prev_fechamento || null,
      commit: form.commit,
    })
  }

  return (
    <>
      <header className="topbar">
        <div className="breadcrumb">
          <Link to="/negocios">Negócios</Link>
          <span>/</span>
          <span className="current">{deal.nome}</span>
        </div>
      </header>

      <div className="content">
        <section className="deal-head">
          <div>
            <h1>{deal.nome}</h1>
            <div className="deal-head-meta">
              {company && (
                <span className="company-chip" onClick={() => navigate(`/empresas/${company.id}`)}>{company.razao_social}</span>
              )}
              <span>·</span>
              <span className={`stage-pill-lg ${deal.status}`}><span className="d" />{currentStage?.nome ?? '—'}</span>
              <span>·</span>
              <span>Responsável: <strong>{usersById[deal.responsavel_id] ?? '—'}</strong></span>
            </div>
          </div>
          <div className="deal-actions">
            <button className="btn-ghost" onClick={() => setShowEnrollModal(true)}>Inscrever</button>
            {deal.status === 'aberto' && (
              <>
                <button className="btn-danger-outline" onClick={() => setShowLostModal(true)}>Marcar como perdido</button>
                <button className="btn-good" disabled={closeMutation.isPending} onClick={() => closeMutation.mutate({ status: 'ganho' })}>
                  Marcar como ganho
                </button>
              </>
            )}
          </div>
        </section>

        {deal.status !== 'aberto' && (
          <div className={`closed-banner show ${deal.status}`}>
            {deal.status === 'ganho' ? 'Negócio marcado como ganho.' : `Negócio marcado como perdido — motivo: ${deal.motivo_perda ?? '—'}.`}
          </div>
        )}

        <div className="stat-strip">
          <div className="stat-tile"><div className="t">Valor previsto</div><div className="v">{formatCurrency(deal.valor_previsto)}</div></div>
          <div className="stat-tile"><div className="t">Probabilidade</div><div className="v">{deal.probabilidade != null ? `${deal.probabilidade}%` : '—'}</div></div>
          <div className="stat-tile"><div className="t">Previsão de fechamento</div><div className="v">{deal.data_prev_fechamento ? new Date(`${deal.data_prev_fechamento}T00:00:00`).toLocaleDateString('pt-BR') : '—'}</div></div>
          <div className="stat-tile"><div className="t">Origem</div><div className="v" style={{ fontSize: 15 }}>{deal.origem ?? '—'}</div></div>
          <div className="stat-tile">
            <div className="t">Commit</div>
            <div className="v" style={{ fontSize: 15, color: deal.commit ? 'var(--amber-dark)' : 'var(--ink-faint)' }}>
              {deal.commit ? '★ Confirmado' : 'Não confirmado'}
            </div>
          </div>
        </div>

        <div className="grid-main">
          <div className="col">
            <div className="card">
              <div className="card-head"><h2>Adicionar atividade</h2></div>
              <TimelineComposer
                placeholder="Escreva uma nota sobre este negócio…"
                submitting={noteMutation.isPending}
                submitLabel="Adicionar"
                pendingLabel="Adicionando…"
                onSubmit={(payload, reset) => noteMutation.mutate(payload, { onSuccess: reset })}
              />
            </div>

            <div className="card">
              <div className="card-head"><h2>Linha do tempo</h2></div>
              <div className="timeline">
                {timelineQuery.isLoading && <p className="state-msg">Carregando…</p>}
                {(timelineQuery.data?.items ?? []).map((e) => (
                  <div className="tl-item" key={e.id}>
                    <div className={`tl-icon t-${e.tipo}`}>{tipoGlyph(e.tipo)}</div>
                    <div className="tl-body">
                      <div className="tl-title">
                        {e.titulo}
                        {e.evento_meta?.enviado && <span className="tl-tag ok">Enviado</span>}
                        {e.evento_meta?.teams_join_url && <span className="tl-tag teams">Teams</span>}
                        {e.evento_meta?.transcricao_status === 'erro' && <span className="tl-tag err">Transcrição falhou</span>}
                      </div>
                      {e.descricao && <div className="tl-desc">{e.descricao}</div>}
                      {e.evento_meta?.teams_join_url && (
                        <a className="tl-teams-link" href={e.evento_meta.teams_join_url} target="_blank" rel="noopener noreferrer">
                          Entrar na reunião do Teams
                        </a>
                      )}
                      {e.evento_meta?.transcricao && (
                        <details className="tl-transcript">
                          <summary>Ver transcrição</summary>
                          <div className="tl-desc">{e.evento_meta.transcricao}</div>
                        </details>
                      )}
                      <div className="tl-meta">
                        {e.user_id && <span className="who">{usersById[e.user_id] ?? ''}</span>}
                        <span>{new Date(e.created_at).toLocaleString('pt-BR')}</span>
                      </div>
                    </div>
                  </div>
                ))}
                {timelineQuery.data && timelineQuery.data.items.length === 0 && (
                  <p className="state-msg">Nenhuma atividade registrada ainda.</p>
                )}
              </div>
            </div>
          </div>

          <div className="col">
            {form && (
              <div className="card">
                <div className="card-head"><h2>Detalhes do negócio</h2></div>
                <div className="card-body">
                  <div className="f-group">
                    <label className="f-label">Pipeline</label>
                    <input className="f-input" value={pipelineQuery.data?.nome ?? '—'} disabled />
                  </div>
                  <div className="f-group">
                    <label className="f-label">Etapa</label>
                    <select
                      className="f-select"
                      value={deal.stage_id}
                      disabled={deal.status !== 'aberto' || stageMutation.isPending}
                      onChange={(e) => stageMutation.mutate(e.target.value)}
                    >
                      {stages.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
                    </select>
                    <span className="f-hint">Mudar aqui reflete no board de Negócios.</span>
                  </div>
                  <div className="f-group">
                    <label className="f-label">Valor previsto (R$)</label>
                    <input className="f-input" type="number" step="0.01" value={form.valor_previsto} onChange={(e) => setForm((f) => ({ ...f, valor_previsto: e.target.value }))} />
                  </div>
                  <div className="f-group">
                    <label className="f-label">Probabilidade (%)</label>
                    <input className="f-input" type="number" min="0" max="100" value={form.probabilidade} onChange={(e) => setForm((f) => ({ ...f, probabilidade: e.target.value }))} />
                  </div>
                  <div className="f-group">
                    <label className="f-label">Previsão de fechamento</label>
                    <input className="f-input" type="date" value={form.data_prev_fechamento} onChange={(e) => setForm((f) => ({ ...f, data_prev_fechamento: e.target.value }))} />
                  </div>
                  <div className="f-group">
                    <label className="f-label">Origem</label>
                    <input className="f-input" value={deal.origem ?? 'Sem origem'} disabled />
                    <span className="f-hint">Herdada da empresa — edite a origem em Empresas para mudar.</span>
                  </div>
                  <label className="field-checkbox" style={{ marginBottom: 14 }}>
                    <input type="checkbox" checked={form.commit} onChange={(e) => setForm((f) => ({ ...f, commit: e.target.checked }))} />
                    Commit — confirmo que este negócio fecha no mês previsto
                  </label>
                  <button className="btn-primary btn-sm" disabled={updateMutation.isPending} onClick={handleSaveDetails} style={{ width: 'fit-content' }}>
                    {updateMutation.isPending ? 'Salvando…' : 'Salvar alterações'}
                  </button>
                </div>
              </div>
            )}

            {company && (
              <div className="card">
                <div className="card-head"><h2>Empresa</h2><Link className="link-action" to={`/empresas/${company.id}`}>Ver empresa</Link></div>
                <div className="card-body">
                  <div className="mini-card">
                    <span className="avatar">{initials(company.razao_social)}</span>
                    <div className="mini-body">
                      <div className="mini-title">{company.razao_social}</div>
                      <div className="mini-sub">{company.segmento ?? '—'}</div>
                    </div>
                  </div>
                  <div className="mini-facts">
                    {company.cidade && <div className="mini-fact">{company.cidade}/{company.uf}</div>}
                    {company.telefone && <div className="mini-fact">{company.telefone}</div>}
                  </div>
                </div>
              </div>
            )}

            {deal.contact_id && contact && (
              <div className="card">
                <div className="card-head"><h2>Contato principal</h2><Link className="link-action" to={`/contatos?empresa=${deal.company_id}`}>Ver contatos</Link></div>
                <div className="card-body">
                  <div className="mini-card">
                    <span className="avatar">{initials(contact.nome)}</span>
                    <div className="mini-body">
                      <div className="mini-title">{contact.nome}</div>
                      <div className="mini-sub">{contact.cargo ?? '—'}</div>
                    </div>
                  </div>
                  <div className="quick-icons">
                    {contact.email && <a href={`mailto:${contact.email}`} title="E-mail">✉️</a>}
                    {contact.telefone && (
                      chamadasConectadas ? (
                        <button
                          type="button" className="quick-icons-btn" title="Ligar"
                          onClick={() => ligar(contact.telefone, { label: contact.nome, contactId: contact.id, companyId: deal.company_id, dealId: deal.id })}
                        >
                          📞
                        </button>
                      ) : (
                        <a href={`tel:${contact.telefone}`} title="Telefone">📞</a>
                      )
                    )}
                    {contact.tem_whatsapp && contact.telefone && (
                      <a href={`https://wa.me/55${contact.telefone.replace(/\D/g, '')}`} target="_blank" rel="noopener noreferrer" title="WhatsApp">💬</a>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div className="card">
              <div className="card-head"><h2>Tarefas vinculadas</h2><Link className="link-action" to="/tarefas">Nova tarefa</Link></div>
              <div className="task-list">
                {(tasksQuery.data?.items ?? []).map((t) => (
                  <div className={`task-item${t.status === 'concluida' ? ' done' : ''}`} key={t.id}>
                    <button className="task-check" onClick={() => t.status !== 'concluida' && completeTaskMutation.mutate(t.id)}>
                      {t.status === 'concluida' && '✓'}
                    </button>
                    <div>
                      <div className="task-title">{t.titulo}</div>
                      {t.descricao && <div className="task-desc" title={t.descricao}>{t.descricao}</div>}
                      <div className="task-meta">{new Date(`${t.data}T00:00:00`).toLocaleDateString('pt-BR')}{t.hora ? ` às ${t.hora}` : ''}</div>
                    </div>
                  </div>
                ))}
                {tasksQuery.data && tasksQuery.data.items.length === 0 && (
                  <p className="state-msg">Nenhuma tarefa vinculada.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {showLostModal && (
        <LostModal
          onClose={() => setShowLostModal(false)}
          submitting={closeMutation.isPending}
          onSubmit={(motivo) => closeMutation.mutate({ status: 'perdido', motivo_perda: motivo })}
        />
      )}

      {showEnrollModal && (
        <EnrollModal
          alvos={[{ deal_id: id }]}
          alvoLabel={deal.nome}
          onClose={() => setShowEnrollModal(false)}
        />
      )}
    </>
  )
}

function LostModal({ onClose, onSubmit, submitting }) {
  const [motivo, setMotivo] = useState('')
  const [showErr, setShowErr] = useState(false)

  function handleConfirm() {
    if (!motivo) { setShowErr(true); return }
    onSubmit(motivo)
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h3>Marcar como perdido</h3>
        <p className="sub">Registrar o motivo ajuda a entender padrões de perda.</p>
        <div className="f-group">
          <label className="f-label">Motivo da perda</label>
          <select className="f-select" value={motivo} onChange={(e) => { setMotivo(e.target.value); setShowErr(false) }}>
            <option value="">Selecione…</option>
            {MOTIVOS_PERDA.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          {showErr && <span className="f-err show">Selecione um motivo.</span>}
        </div>
        <div className="row">
          <button className="btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn-danger" disabled={submitting} onClick={handleConfirm}>Confirmar perda</button>
        </div>
      </div>
    </div>
  )
}
