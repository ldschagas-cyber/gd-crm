import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getCompany, runSdrArgos, setCompanyStatus, updateCompany } from '../api/companies'
import { listContacts, createContact } from '../api/contacts'
import { listDeals, createDeal } from '../api/deals'
import { listPipelines } from '../api/pipelines'
import { listTasks, completeTask, createTask } from '../api/tasks'
import { listTimeline, addTimelineNote } from '../api/timeline'
import { getContactEmails } from '../api/contacts'
import { listUsers } from '../api/users'
import { createAssinatura, listAssinaturas } from '../api/subscriptions'
import { CompanyModal } from './EmpresasPage.jsx'
import { ContactModal } from './ContatosPage.jsx'
import { DealDrawer } from './NegociosPage.jsx'
import { TaskModal } from './TarefasPage.jsx'
import { NewSubscriptionModal, SubscriptionDrawer } from './ReceitaRecorrentePage.jsx'
import EnrollModal from '../components/EnrollModal.jsx'
import TimelineComposer from '../components/TimelineComposer.jsx'
import CompanyTabs from '../components/CompanyTabs.jsx'
import { useSoftphone } from '../context/SoftphoneContext.jsx'
import '../styles/dataTable.css'
import '../styles/detailPage.css'
import './CompanyDetailPage.css'

const STATUS_LABEL = { lead: 'Lead', qualificado: 'Qualificado', cliente: 'Cliente', perdido: 'Perdido', inativo: 'Inativo' }
const FILTER_CHIPS = [
  { key: 'all', label: 'Tudo' },
  { key: 'ligacao', label: 'Ligações' },
  { key: 'email', label: 'E-mails' },
  { key: 'reuniao', label: 'Reuniões' },
  { key: 'pipeline', label: 'Negócios' },
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

export default function CompanyDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { conectado: chamadasConectadas, call: ligar } = useSoftphone()
  const [showEditModal, setShowEditModal] = useState(false)
  const [showNewContact, setShowNewContact] = useState(false)
  const [showNewDeal, setShowNewDeal] = useState(false)
  const [showNewTask, setShowNewTask] = useState(false)
  const [showEnrollModal, setShowEnrollModal] = useState(false)
  const [showNewSub, setShowNewSub] = useState(false)
  const [showSubDrawer, setShowSubDrawer] = useState(false)
  const [timelineFilter, setTimelineFilter] = useState('all')
  const [emailsContactId, setEmailsContactId] = useState('')
  const [sdrArgosQueuedAt, setSdrArgosQueuedAt] = useState(null)

  const companyQuery = useQuery({ queryKey: ['companies', 'detail', id], queryFn: () => getCompany(id) })
  const usersQuery = useQuery({ queryKey: ['users', 'for-assign'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const timelineQuery = useQuery({ queryKey: ['timeline', id], queryFn: () => listTimeline(id) })
  const contactsQuery = useQuery({ queryKey: ['contacts', 'mini', id], queryFn: () => listContacts({ companyId: id, size: 5 }) })
  const dealsQuery = useQuery({ queryKey: ['deals', 'mini', id], queryFn: () => listDeals({ companyId: id, size: 5 }) })
  const tasksQuery = useQuery({ queryKey: ['tasks', 'mini', id], queryFn: () => listTasks({ companyId: id, size: 5 }) })
  const assinaturasQuery = useQuery({ queryKey: ['assinaturas', 'by-company', id], queryFn: () => listAssinaturas({ companyId: id }) })
  const pipelinesQuery = useQuery({ queryKey: ['pipelines'], queryFn: () => listPipelines({ size: 100 }) })
  const pipelines = pipelinesQuery.data?.items ?? []
  const dealPipeline = pipelines.find((p) => p.is_default) ?? pipelines[0]
  const emailsQuery = useQuery({
    queryKey: ['contact-emails', emailsContactId],
    queryFn: () => getContactEmails(emailsContactId),
    enabled: false,
  })

  const usersById = Object.fromEntries((usersQuery.data?.items ?? []).map((u) => [u.id, u.nome]))

  const statusMutation = useMutation({
    mutationFn: (status) => setCompanyStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies', 'detail', id] })
      queryClient.invalidateQueries({ queryKey: ['timeline', id] })
    },
  })
  const updateMutation = useMutation({
    mutationFn: (data) => updateCompany(id, data),
    onSuccess: () => {
      setShowEditModal(false)
      queryClient.invalidateQueries({ queryKey: ['companies', 'detail', id] })
    },
  })
  const sdrArgosMutation = useMutation({
    mutationFn: () => runSdrArgos(id),
    onSuccess: () => {
      // Endpoint só enfileira (202) — o dossiê some/aparece na aba "Dossiê Comercial", não
      // aqui na Visão Geral, então isto é só feedback de "disparei" + reconsulta de bastidor
      // pra badge/estado eventualmente refletido nesta página não ficar desatualizado.
      const invalidate = () => queryClient.invalidateQueries({ queryKey: ['companies', 'detail', id] })
      setSdrArgosQueuedAt(Date.now())
      invalidate()
      ;[8000, 16000, 28000].forEach((ms) => setTimeout(invalidate, ms))
      setTimeout(() => setSdrArgosQueuedAt(null), 32000)
    },
  })
  const noteMutation = useMutation({
    mutationFn: (data) => addTimelineNote(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['timeline', id] }),
  })
  const createContactMutation = useMutation({
    mutationFn: createContact,
    onSuccess: () => {
      setShowNewContact(false)
      queryClient.invalidateQueries({ queryKey: ['contacts', 'mini', id] })
    },
  })
  const completeTaskMutation = useMutation({
    mutationFn: completeTask,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks', 'mini', id] }),
  })
  const createDealMutation = useMutation({
    mutationFn: createDeal,
    onSuccess: () => {
      setShowNewDeal(false)
      queryClient.invalidateQueries({ queryKey: ['deals', 'mini', id] })
      queryClient.invalidateQueries({ queryKey: ['timeline', id] })
    },
  })
  const createTaskMutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => {
      setShowNewTask(false)
      queryClient.invalidateQueries({ queryKey: ['tasks', 'mini', id] })
    },
  })
  const createSubMutation = useMutation({
    mutationFn: createAssinatura,
    onSuccess: () => {
      setShowNewSub(false)
      queryClient.invalidateQueries({ queryKey: ['assinaturas', 'by-company', id] })
    },
  })

  if (companyQuery.isLoading) return <div className="content"><p className="state-msg">Carregando…</p></div>
  if (companyQuery.isError) return <div className="content"><p className="state-msg error">Empresa não encontrada.</p></div>

  const company = companyQuery.data
  const assinaturaAtiva = (assinaturasQuery.data ?? []).find((a) => a.status === 'ativa') ?? null
  const timelineItems = (timelineQuery.data?.items ?? []).filter(
    (e) => timelineFilter === 'all' || e.tipo === timelineFilter,
  )

  return (
    <>
      <header className="topbar">
        <div className="breadcrumb">
          <Link to="/empresas">Empresas</Link>
          <span>/</span>
          <span className="current">{company.razao_social}</span>
        </div>
      </header>

      <div className="content">
        <CompanyTabs companyId={id} />

        <section className="card co-header">
          <div className="co-header-top">
            <div className="co-logo">{initials(company.razao_social)}</div>
            <div className="co-title-block">
              <div className="co-title-row">
                <h1>{company.razao_social}</h1>
                <div className="status-select-wrap">
                  <span className="dot" />
                  <select
                    className="status-select"
                    data-status={company.status}
                    value={company.status}
                    onChange={(e) => statusMutation.mutate(e.target.value)}
                  >
                    {Object.entries(STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </div>
              </div>
              {company.nome_fantasia && <p className="co-sub">{company.nome_fantasia}</p>}
              <div className="co-tags">
                {company.segmento && <span className="tag">{company.segmento}</span>}
                {company.porte && <span className="tag">{company.porte}</span>}
                {company.faixa_faturamento && <span className="tag">{company.faixa_faturamento}</span>}
                {company.origem && <span className="tag">{company.origem}</span>}
              </div>
            </div>
            <div className="co-actions">
              <button
                className="btn-ghost"
                disabled={sdrArgosMutation.isPending || !!sdrArgosQueuedAt}
                onClick={() => sdrArgosMutation.mutate()}
              >
                {sdrArgosMutation.isPending || sdrArgosQueuedAt ? 'SDR Argos rodando…' : 'SDR Argos ↻'}
              </button>
              <button className="btn-ghost" onClick={() => setShowEnrollModal(true)}>Inscrever</button>
              <button className="btn-ghost" onClick={() => setShowEditModal(true)}>Editar</button>
            </div>
          </div>

          <dl className="key-facts">
            <div className="fact"><dt>CNPJ</dt><dd>{company.cnpj ?? '—'}</dd></div>
            <div className="fact"><dt>Site</dt><dd>{company.site ? <a href={company.site.startsWith('http') ? company.site : `https://${company.site}`} target="_blank" rel="noopener noreferrer">{company.site}</a> : '—'}</dd></div>
            <div className="fact"><dt>LinkedIn</dt><dd>{company.linkedin ? <a href={company.linkedin.startsWith('http') ? company.linkedin : `https://${company.linkedin}`} target="_blank" rel="noopener noreferrer">{company.linkedin}</a> : '—'}</dd></div>
            <div className="fact">
              <dt>Telefone</dt>
              <dd>
                {company.telefone ?? '—'}
                {company.telefone && chamadasConectadas && (
                  <button
                    type="button" className="link-action call-inline-btn"
                    onClick={() => ligar(company.telefone, { label: company.razao_social, companyId: company.id })}
                  >
                    Ligar
                  </button>
                )}
              </dd>
            </div>
            <div className="fact"><dt>E-mail</dt><dd>{company.email ?? '—'}</dd></div>
            <div className="fact"><dt>Localização</dt><dd>{company.cidade ? `${company.cidade}, ${company.uf ?? ''}` : '—'}</dd></div>
            <div className="fact"><dt>Funcionários</dt><dd>{company.num_funcionarios?.toLocaleString('pt-BR') ?? '—'}</dd></div>
            <div className="fact"><dt>Faturamento estimado</dt><dd>{formatCurrency(company.faturamento_estimado)}</dd></div>
            <div className="fact resp"><dt>Responsável</dt><dd>{company.responsavel_id ? (usersById[company.responsavel_id] ?? '—') : '—'}</dd></div>
          </dl>
          {sdrArgosQueuedAt && (
            <p className="state-msg" style={{ padding: '0 0 14px' }}>
              SDR Argos disparado — roda em background (~10 a 30s). Veja o resultado em{' '}
              <Link to={`/empresas/${id}/dossie`}>Dossiê Comercial</Link>.
            </p>
          )}
        </section>

        <section className="grid-main">
          <div className="col">
            <div className="card">
              <div className="card-head"><div><h3>Timeline</h3><p>Todo o histórico de interações com esta empresa</p></div></div>

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
            <div className="card">
              <div className="card-head">
                <div><h3>Contatos</h3></div>
                <Link className="link-action" to={`/contatos?empresa=${id}`}>Ver todos</Link>
              </div>
              <div className="mini-list">
                {(contactsQuery.data?.items ?? []).map((c) => (
                  <div className="mini-row" key={c.id}>
                    <span className="avatar">{initials(c.nome)}</span>
                    <div className="mini-main">
                      <div className="mini-title">{c.nome}</div>
                      <div className="mini-sub">{c.cargo ?? '—'}</div>
                    </div>
                  </div>
                ))}
                {contactsQuery.data && contactsQuery.data.items.length === 0 && (
                  <p className="state-msg">
                    Nenhum contato ainda.
                    {company.contato_sugerido && <> Sugestão da pesquisa: <b>{company.contato_sugerido}</b>.</>}
                  </p>
                )}
              </div>
              <div className="add-row-btn" onClick={() => setShowNewContact(true)}>+ Novo contato</div>
            </div>

            <div className="card">
              <div className="card-head"><div><h3>E-mails trocados</h3><p>Busca sob demanda na sua caixa conectada</p></div></div>
              <div className="card-body">
                <div className="f-row" style={{ gap: 8 }}>
                  <select
                    className="f-select"
                    value={emailsContactId}
                    onChange={(e) => { setEmailsContactId(e.target.value); }}
                  >
                    <option value="">Selecione um contato…</option>
                    {(contactsQuery.data?.items ?? []).filter((c) => c.email).map((c) => (
                      <option key={c.id} value={c.id}>{c.nome}</option>
                    ))}
                  </select>
                  <button
                    className="btn-ghost"
                    disabled={!emailsContactId || emailsQuery.isFetching}
                    onClick={() => emailsQuery.refetch()}
                  >
                    {emailsQuery.isFetching ? 'Buscando…' : 'Buscar e-mails'}
                  </button>
                </div>
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
                <div><h3>Assinatura</h3></div>
                <Link className="link-action" to="/receita-recorrente">Ver receita recorrente</Link>
              </div>
              <div className="mini-list">
                {assinaturaAtiva && (
                  <div className="mini-row" style={{ cursor: 'pointer' }} onClick={() => setShowSubDrawer(true)}>
                    <div className="mini-main">
                      <div className="mini-title">{assinaturaAtiva.nome_plano}</div>
                      <span className="status-pill" data-status="ativa"><span className="d" />Ativa</span>
                    </div>
                    <div className="mini-val">{formatCurrency(assinaturaAtiva.valor_mensal)}</div>
                  </div>
                )}
                {assinaturasQuery.data && !assinaturaAtiva && (
                  <p className="state-msg">Nenhuma assinatura ativa.</p>
                )}
              </div>
              {!assinaturaAtiva && <div className="add-row-btn" onClick={() => setShowNewSub(true)}>+ Nova assinatura</div>}
            </div>

            <div className="card">
              <div className="card-head">
                <div><h3>Negócios</h3></div>
                <Link className="link-action" to="/negocios">Ver todos</Link>
              </div>
              <div className="mini-list">
                {(dealsQuery.data?.items ?? []).map((d) => (
                  <div className="mini-row" key={d.id}>
                    <div className="mini-main">
                      <div className="mini-title">{d.nome}</div>
                      <span className={`deal-status-pill deal-status-${d.status}`}>{d.status}</span>
                    </div>
                    <div className="mini-val">{formatCurrency(d.valor_previsto)}</div>
                  </div>
                ))}
                {dealsQuery.data && dealsQuery.data.items.length === 0 && (
                  <p className="state-msg">Nenhum negócio ainda.</p>
                )}
              </div>
              {dealPipeline && <div className="add-row-btn" onClick={() => setShowNewDeal(true)}>+ Novo negócio</div>}
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
                      <div className="task-meta">{new Date(t.data).toLocaleDateString('pt-BR')}{t.hora ? ` às ${t.hora}` : ''} · {t.prioridade}</div>
                    </div>
                  </div>
                ))}
                {tasksQuery.data && tasksQuery.data.items.length === 0 && (
                  <p className="state-msg">Nenhuma tarefa vinculada.</p>
                )}
              </div>
              <div className="add-row-btn" onClick={() => setShowNewTask(true)}>+ Nova tarefa</div>
            </div>
          </div>
        </section>
      </div>

      {showEditModal && (
        <CompanyModal
          company={company}
          users={usersQuery.data?.items ?? []}
          usersError={usersQuery.isError}
          onClose={() => setShowEditModal(false)}
          onSubmit={(data) => updateMutation.mutate(data)}
          submitting={updateMutation.isPending}
          error={updateMutation.error}
        />
      )}

      {showNewContact && (
        <ContactModal
          contact={{ company_id: id }}
          companies={[company]}
          onClose={() => setShowNewContact(false)}
          onSubmit={(data) => createContactMutation.mutate({ ...data, company_id: id })}
          submitting={createContactMutation.isPending}
          error={createContactMutation.error}
        />
      )}

      {showEnrollModal && (
        <EnrollModal
          alvos={[{ company_id: id }]}
          alvoLabel={company.razao_social}
          onClose={() => setShowEnrollModal(false)}
        />
      )}

      {showNewDeal && dealPipeline && (
        <DealDrawer
          pipeline={dealPipeline}
          companies={[company]}
          presetCompanyId={id}
          users={usersQuery.data?.items ?? []}
          onClose={() => setShowNewDeal(false)}
          onSubmit={(data) => createDealMutation.mutate({ ...data, pipeline_id: dealPipeline.id })}
          submitting={createDealMutation.isPending}
          error={createDealMutation.error}
        />
      )}

      {showNewTask && (
        <TaskModal
          task={{ company_id: id }}
          companies={[company]}
          users={usersQuery.data?.items ?? []}
          onClose={() => setShowNewTask(false)}
          onSubmit={(data) => createTaskMutation.mutate(data)}
          submitting={createTaskMutation.isPending}
          error={createTaskMutation.error}
        />
      )}

      {showNewSub && (
        <NewSubscriptionModal
          companies={[company]}
          presetCompanyId={id}
          users={usersQuery.data?.items ?? []}
          onClose={() => setShowNewSub(false)}
          onSubmit={(data) => createSubMutation.mutate(data)}
          submitting={createSubMutation.isPending}
          error={createSubMutation.error}
        />
      )}

      {showSubDrawer && assinaturaAtiva && (
        <SubscriptionDrawer
          assinatura={assinaturaAtiva}
          companyNome={company.razao_social}
          onClose={() => setShowSubDrawer(false)}
          onChanged={() => queryClient.invalidateQueries({ queryKey: ['assinaturas', 'by-company', id] })}
        />
      )}
    </>
  )
}

function tipoGlyph(tipo) {
  const map = { nota: '📝', ligacao: '📞', email: '✉️', reuniao: '📅', pipeline: '📈', tarefa: '✔️', cadastro: '●' }
  return map[tipo] ?? '●'
}
