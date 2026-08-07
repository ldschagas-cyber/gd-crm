import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getContact, getContactEmails, updateContact } from '../api/contacts'
import { getCompany } from '../api/companies'
import { listDeals, createDeal } from '../api/deals'
import { listPipelines } from '../api/pipelines'
import { listTasks, completeTask, createTask } from '../api/tasks'
import { listContactTimeline, addContactTimelineNote } from '../api/timeline'
import { listUsers } from '../api/users'
import { ContactModal } from './ContatosPage.jsx'
import { DealDrawer } from './NegociosPage.jsx'
import { TaskModal } from './TarefasPage.jsx'
import TimelineComposer from '../components/TimelineComposer.jsx'
import { useSoftphone } from '../context/SoftphoneContext.jsx'
import '../styles/dataTable.css'
import '../styles/detailPage.css'

const FILTER_CHIPS = [
  { key: 'all', label: 'Tudo' },
  { key: 'ligacao', label: 'Ligações' },
  { key: 'email', label: 'E-mails' },
  { key: 'reuniao', label: 'Reuniões' },
  { key: 'nota', label: 'Notas' },
]

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
function onlyDigits(v) {
  return (v || '').replace(/\D/g, '')
}

export default function ContactDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { conectado: chamadasConectadas, call: ligar } = useSoftphone()
  const [showEditModal, setShowEditModal] = useState(false)
  const [showNewDeal, setShowNewDeal] = useState(false)
  const [showNewTask, setShowNewTask] = useState(false)
  const [timelineFilter, setTimelineFilter] = useState('all')

  const contactQuery = useQuery({ queryKey: ['contacts', 'detail', id], queryFn: () => getContact(id) })
  const contact = contactQuery.data

  const companyQuery = useQuery({
    queryKey: ['companies', 'detail-mini', contact?.company_id],
    queryFn: () => getCompany(contact.company_id),
    enabled: Boolean(contact),
  })
  const usersQuery = useQuery({ queryKey: ['users', 'for-assign'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const timelineQuery = useQuery({ queryKey: ['contact-timeline', id], queryFn: () => listContactTimeline(id) })
  const dealsQuery = useQuery({ queryKey: ['deals', 'mini-contact', id], queryFn: () => listDeals({ contactId: id, size: 5 }) })
  const tasksQuery = useQuery({ queryKey: ['tasks', 'mini-contact', id], queryFn: () => listTasks({ contactId: id, size: 20 }) })
  const pipelinesQuery = useQuery({ queryKey: ['pipelines'], queryFn: () => listPipelines({ size: 100 }) })
  const pipelines = pipelinesQuery.data?.items ?? []
  const dealPipeline = pipelines.find((p) => p.is_default) ?? pipelines[0]
  const emailsQuery = useQuery({
    queryKey: ['contact-emails', id],
    queryFn: () => getContactEmails(id),
    enabled: false,
  })

  const usersById = Object.fromEntries((usersQuery.data?.items ?? []).map((u) => [u.id, u.nome]))

  const updateMutation = useMutation({
    mutationFn: (data) => updateContact(id, data),
    onSuccess: () => {
      setShowEditModal(false)
      queryClient.invalidateQueries({ queryKey: ['contacts', 'detail', id] })
    },
  })
  const noteMutation = useMutation({
    mutationFn: (data) => addContactTimelineNote(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['contact-timeline', id] }),
  })
  const completeTaskMutation = useMutation({
    mutationFn: completeTask,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks', 'mini-contact', id] }),
  })
  const createDealMutation = useMutation({
    mutationFn: createDeal,
    onSuccess: () => {
      setShowNewDeal(false)
      queryClient.invalidateQueries({ queryKey: ['deals', 'mini-contact', id] })
      queryClient.invalidateQueries({ queryKey: ['contact-timeline', id] })
    },
  })
  const createTaskMutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => {
      setShowNewTask(false)
      queryClient.invalidateQueries({ queryKey: ['tasks', 'mini-contact', id] })
    },
  })

  if (contactQuery.isLoading) return <div className="content"><p className="state-msg">Carregando…</p></div>
  if (contactQuery.isError) return <div className="content"><p className="state-msg error">Contato não encontrado.</p></div>

  const company = companyQuery.data
  const timelineItems = (timelineQuery.data?.items ?? []).filter(
    (e) => timelineFilter === 'all' || e.tipo === timelineFilter,
  )

  return (
    <>
      <header className="topbar">
        <div className="breadcrumb">
          <Link to="/contatos">Contatos</Link>
          <span>/</span>
          <span className="current">{contact.nome}</span>
        </div>
      </header>

      <div className="content">
        <section className="card co-header">
          <div className="co-header-top">
            <div className="co-logo">{initials(contact.nome)}</div>
            <div className="co-title-block">
              <div className="co-title-row">
                <h1>{contact.nome}</h1>
              </div>
              {(contact.cargo || company) && (
                <p className="co-sub">
                  {contact.cargo}
                  {contact.cargo && company && ' — '}
                  {company && (
                    <span className="company-chip" onClick={() => navigate(`/empresas/${company.id}`)}>
                      {company.razao_social}
                    </span>
                  )}
                </p>
              )}
            </div>
            <div className="co-actions">
              <button className="btn-ghost" onClick={() => setShowEditModal(true)}>Editar</button>
            </div>
          </div>

          <dl className="key-facts">
            <div className="fact">
              <dt>Telefone</dt>
              <dd>
                {contact.telefone ?? '—'}
                {contact.telefone && chamadasConectadas && (
                  <button
                    type="button" className="link-action call-inline-btn"
                    onClick={() => ligar(contact.telefone, { label: contact.nome, contactId: contact.id, companyId: contact.company_id })}
                  >
                    Ligar
                  </button>
                )}
              </dd>
            </div>
            <div className="fact">
              <dt>WhatsApp</dt>
              <dd>
                {contact.whatsapp ? (
                  <a href={`https://wa.me/55${onlyDigits(contact.whatsapp)}`} target="_blank" rel="noopener noreferrer">{contact.whatsapp}</a>
                ) : '—'}
              </dd>
            </div>
            <div className="fact"><dt>E-mail</dt><dd>{contact.email ?? '—'}</dd></div>
            <div className="fact">
              <dt>LinkedIn</dt>
              <dd>
                {contact.linkedin ? (
                  <a href={contact.linkedin.startsWith('http') ? contact.linkedin : `https://${contact.linkedin}`} target="_blank" rel="noopener noreferrer">
                    Abrir perfil
                  </a>
                ) : '—'}
              </dd>
            </div>
            <div className="fact">
              <dt>Aniversário</dt>
              <dd>{contact.data_nascimento ? new Date(`${contact.data_nascimento}T00:00:00`).toLocaleDateString('pt-BR') : '—'}</dd>
            </div>
          </dl>
          {contact.observacoes && <p className="tl-desc" style={{ marginTop: 14 }}>{contact.observacoes}</p>}
        </section>

        <section className="grid-main">
          <div className="col">
            <div className="card">
              <div className="card-head"><div><h3>Timeline</h3><p>Todo o histórico de interações com este contato</p></div></div>

              <div className="filter-row">
                {FILTER_CHIPS.map((f) => (
                  <button key={f.key} className={`filter-chip${timelineFilter === f.key ? ' active' : ''}`} onClick={() => setTimelineFilter(f.key)}>
                    {f.label}
                  </button>
                ))}
              </div>

              <TimelineComposer
                placeholder="Registre uma nota, o resumo de uma ligação, e-mail ou reunião..."
                submitting={noteMutation.isPending}
                onSubmit={(payload, reset) => noteMutation.mutate(payload, { onSuccess: reset })}
              />

              <div className="timeline">
                {timelineQuery.isLoading && <p className="state-msg">Carregando…</p>}
                {timelineItems.map((e) => (
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
                {timelineQuery.data && timelineItems.length === 0 && (
                  <p className="state-msg">Nenhum evento com esse filtro.</p>
                )}
              </div>
            </div>
          </div>

          <div className="col">
            {company && (
              <div className="card">
                <div className="card-head"><div><h3>Empresa</h3></div><Link className="link-action" to={`/empresas/${company.id}`}>Ver empresa</Link></div>
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

            <div className="card">
              <div className="card-head"><div><h3>E-mails trocados</h3><p>Busca sob demanda na sua caixa conectada</p></div></div>
              <div className="card-body">
                <button
                  className="btn-ghost"
                  disabled={!contact.email || emailsQuery.isFetching}
                  onClick={() => emailsQuery.refetch()}
                >
                  {emailsQuery.isFetching ? 'Buscando…' : 'Buscar e-mails'}
                </button>
                {!contact.email && <p className="f-hint" style={{ marginTop: 8 }}>Este contato não tem e-mail cadastrado.</p>}
                {emailsQuery.isError && (
                  <p className="state-msg error">{emailsQuery.error?.response?.data?.error?.message ?? 'Não foi possível buscar.'}</p>
                )}
                {emailsQuery.data && (
                  <div className="email-lookup-list">
                    {emailsQuery.data.map((m, i) => (
                      <div className="email-lookup-row" key={i}>
                        <span className={`email-lookup-dir ${m.direcao}`}>{m.direcao === 'enviado' ? '↑' : '↓'}</span>
                        <div className="email-lookup-main">
                          <div className="email-lookup-subj">{m.assunto}</div>
                          <div className="email-lookup-snip">{m.resumo}</div>
                        </div>
                        {m.quando && <div className="email-lookup-when">{new Date(m.quando).toLocaleDateString('pt-BR')}</div>}
                      </div>
                    ))}
                    {emailsQuery.data.length === 0 && <p className="state-msg">Nenhum e-mail encontrado com este contato.</p>}
                  </div>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card-head">
                <div><h3>Negócios</h3></div>
                <Link className="link-action" to="/negocios">Ver todos</Link>
              </div>
              <div className="mini-list">
                {(dealsQuery.data?.items ?? []).map((d) => (
                  <div className="mini-row" key={d.id} onClick={() => navigate(`/negocios/${d.id}`)} style={{ cursor: 'pointer' }}>
                    <div className="mini-main">
                      <div className="mini-title">{d.nome}</div>
                      <span className={`deal-status-pill deal-status-${d.status}`}>{d.status}</span>
                    </div>
                    <div className="mini-val">{formatCurrency(d.valor_previsto)}</div>
                  </div>
                ))}
                {dealsQuery.data && dealsQuery.data.items.length === 0 && (
                  <p className="state-msg">Nenhum negócio vinculado.</p>
                )}
              </div>
              {company && dealPipeline && <div className="add-row-btn" onClick={() => setShowNewDeal(true)}>+ Novo negócio</div>}
            </div>

            <div className="card">
              <div className="card-head">
                <div><h3>Próximas tarefas</h3></div>
                <Link className="link-action" to="/tarefas">Ver agenda</Link>
              </div>
              <div className="task-list">
                {(tasksQuery.data?.items ?? []).map((t) => (
                  <div className={`task-item${t.status === 'concluida' ? ' done' : ''}`} key={t.id}>
                    <button
                      className="task-check"
                      onClick={() => t.status !== 'concluida' && completeTaskMutation.mutate(t.id)}
                    >
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
              {company && <div className="add-row-btn" onClick={() => setShowNewTask(true)}>+ Nova tarefa</div>}
            </div>
          </div>
        </section>
      </div>

      {showEditModal && company && (
        <ContactModal
          contact={contact}
          companies={[company]}
          onClose={() => setShowEditModal(false)}
          onSubmit={(data) => updateMutation.mutate(data)}
          submitting={updateMutation.isPending}
          error={updateMutation.error}
        />
      )}

      {showNewDeal && company && dealPipeline && (
        <DealDrawer
          pipeline={dealPipeline}
          companies={[company]}
          presetCompanyId={company.id}
          presetContactId={id}
          users={usersQuery.data?.items ?? []}
          onClose={() => setShowNewDeal(false)}
          onSubmit={(data) => createDealMutation.mutate({ ...data, pipeline_id: dealPipeline.id })}
          submitting={createDealMutation.isPending}
          error={createDealMutation.error}
        />
      )}

      {showNewTask && company && (
        <TaskModal
          task={{ company_id: company.id, contact_id: id }}
          companies={[company]}
          users={usersQuery.data?.items ?? []}
          onClose={() => setShowNewTask(false)}
          onSubmit={(data) => createTaskMutation.mutate(data)}
          submitting={createTaskMutation.isPending}
          error={createTaskMutation.error}
        />
      )}
    </>
  )
}
