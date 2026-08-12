import { useNavigate } from 'react-router-dom'
import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  completeTask, createTask, deleteTask, exportTasks, listTasks, updateTask,
} from '../api/tasks'
import {
  createSlaRule, deleteSlaRule, getSlaResumo, listSlaRules, updateSlaRule,
} from '../api/activitySla'
import { listCompanies } from '../api/companies'
import { listContacts } from '../api/contacts'
import { listDeals } from '../api/deals'
import { listUsers } from '../api/users'
import { listSnippets } from '../api/snippets'
import { TIPO_LABEL, TaskTypeChip } from '../components/TaskTypeIcon'
import SnippetInsertButton from '../components/SnippetInsertButton'
import { handleSnippetExpand } from '../utils/snippets'
import '../styles/dataTable.css'
import './TarefasPage.css'

const PRIO_LABEL = { alta: 'Alta', media: 'Média', baixa: 'Baixa' }
const MESSAGE_TASK_TYPES = ['whatsapp', 'linkedin_conexao', 'linkedin_mensagem']

// Mesmos rótulos de CompanyStatus usados em EmpresasPage/CompanyDetailPage — sem fonte
// única hoje pros dois-três lugares que precisam (mesmo padrão já existente).
const COMPANY_STATUS_LABEL = { lead: 'Lead', qualificado: 'Qualificado', cliente: 'Cliente', perdido: 'Perdido', inativo: 'Inativo' }
const GATILHO_TIPO_LABEL = { company_status: 'Status da empresa', milestone: 'Marco (dispara 1x)', deal_stage: 'Etapa de negócio' }
const SLA_ESTADO_LABEL = { em_andamento: 'Em dia', em_risco: 'Em risco', estourado: 'Estourado', cumprido: 'Cumprido' }
const SLA_ESTADO_CLASS = { em_andamento: 'sla-ok', em_risco: 'sla-risco', estourado: 'sla-estourado', cumprido: 'sla-cumprido' }

function fmtHoras(h) {
  if (h == null) return '—'
  if (h < 1) return `${Math.round(h * 60)}min`
  if (h < 48) return `${Math.round(h)}h`
  return `${Math.round(h / 24)}d`
}

function fmtDateTime(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }) + ' ' +
    d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

export function SlaBadge({ estado }) {
  if (!estado) return null
  return (
    <span className={`status-pill ${SLA_ESTADO_CLASS[estado] ?? ''}`}>
      <span className="d" />{SLA_ESTADO_LABEL[estado] ?? estado}
    </span>
  )
}

// Uma empresa pode ter mais de uma régua em curso (ex.: SLA de status + SLA de negócio) — a
// lista de tarefas mostra só a mais severa, mesma lógica de prioridade do painel de SLA.
const ESTADO_SEVERIDADE = { estourado: 3, em_risco: 2, em_andamento: 1, cumprido: 0 }
function pickWorstSlaByCompany(items) {
  const byCompany = {}
  items.forEach((it) => {
    const atual = byCompany[it.company_id]
    if (!atual || ESTADO_SEVERIDADE[it.estado] > ESTADO_SEVERIDADE[atual.estado]) {
      byCompany[it.company_id] = it
    }
  })
  return byCompany
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return
    } catch {
      // segue pro fallback abaixo (ex.: página não está em contexto seguro)
    }
  }
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  try { document.execCommand('copy') } catch { /* melhor esforço — sem clipboard, usuário seleciona manualmente */ }
  document.body.removeChild(ta)
}

function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}

function dayDiff(dateStr) {
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const d = new Date(dateStr + 'T00:00:00')
  return Math.round((d - today) / 86400000)
}

function dateLabel(dateStr) {
  const diff = dayDiff(dateStr)
  if (diff === 0) return 'Hoje'
  if (diff === 1) return 'Amanhã'
  if (diff === -1) return 'Ontem'
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })
}

export default function TarefasPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [busca, setBusca] = useState('')
  const [responsavelId, setResponsavelId] = useState('')
  const [tipo, setTipo] = useState('')
  const [prioridade, setPrioridade] = useState('')
  const [companyId, setCompanyId] = useState('')
  const [dataInicio, setDataInicio] = useState('')
  const [dataFim, setDataFim] = useState('')
  const [hideDone, setHideDone] = useState(false)
  const [modalTask, setModalTask] = useState(undefined) // undefined = fechado, null = criar, obj = editar
  const [deletingTask, setDeletingTask] = useState(null)
  const [tab, setTab] = useState('tarefas') // 'tarefas' | 'sla'

  const filters = {
    busca: busca || undefined, responsavelId: responsavelId || undefined,
    tipo: tipo || undefined, prioridade: prioridade || undefined,
    companyId: companyId || undefined, dataInicio: dataInicio || undefined, dataFim: dataFim || undefined,
  }

  const companiesQuery = useQuery({ queryKey: ['companies', 'for-select'], queryFn: () => listCompanies({ size: 100 }) })
  const companies = companiesQuery.data?.items ?? []
  const companiesById = Object.fromEntries(companies.map((c) => [c.id, c.razao_social]))

  const usersQuery = useQuery({ queryKey: ['users', 'for-assign'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const users = usersQuery.data?.items ?? []
  const usersById = Object.fromEntries(users.map((u) => [u.id, u.nome]))

  const tasksQuery = useQuery({
    queryKey: ['tasks', 'agenda', filters],
    queryFn: () => listTasks({ size: 100, ...filters }),
  })

  // SLA Comercial (docs/PLANO_SLA_COMERCIAL.md) — carregado sempre, não só na aba SLA,
  // pra alimentar o badge por empresa na lista de tarefas também.
  const resumoQuery = useQuery({ queryKey: ['sla-resumo'], queryFn: getSlaResumo, retry: false })
  const slaByCompany = pickWorstSlaByCompany(resumoQuery.data?.items ?? [])

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['tasks'] })
  }

  const createMutation = useMutation({ mutationFn: createTask, onSuccess: () => { setModalTask(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateTask(id, data), onSuccess: () => { setModalTask(undefined); invalidate() } })
  const deleteMutation = useMutation({ mutationFn: deleteTask, onSuccess: () => { setDeletingTask(null); invalidate() } })
  const completeMutation = useMutation({ mutationFn: completeTask, onSuccess: invalidate })

  const allItems = tasksQuery.data?.items ?? []
  const items = hideDone ? allItems.filter((t) => t.status !== 'concluida') : allItems

  const groups = {}
  items.forEach((t) => { (groups[t.data] ??= []).push(t) })
  const dates = Object.keys(groups).sort()
  dates.forEach((d) => groups[d].sort((a, b) => (a.hora ?? '').localeCompare(b.hora ?? '')))

  // Fila de execução (Melhoria 1, docs/PLANO_FILA_TAREFAS.md): roda sobre a
  // lista filtrada atual, na mesma ordem já exibida — só as pendentes, não
  // faz sentido "executar" uma tarefa já concluída.
  const pendentes = dates.flatMap((d) => groups[d].filter((t) => t.status === 'pendente'))

  function iniciarFila() {
    if (pendentes.length === 0) return
    navigate('/tarefas/executar', { state: { taskIds: pendentes.map((t) => t.id) } })
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Tarefas</h1>
          <p>{items.length.toLocaleString('pt-BR')} tarefa(s)</p>
        </div>
        <div className="page-actions">
          {tab === 'tarefas' && <button className="btn-ghost" onClick={() => exportTasks(filters)}>Exportar</button>}
          {tab === 'tarefas' && (
            <button className="btn-primary" disabled={pendentes.length === 0} onClick={iniciarFila}>
              ▸ Iniciar {pendentes.length} tarefa{pendentes.length === 1 ? '' : 's'}
            </button>
          )}
          {tab === 'tarefas' && <button className="btn-primary" onClick={() => setModalTask(null)}>+ Nova tarefa</button>}
        </div>
      </header>

      <div className="content">
        <div className="tabs-row segmented" role="tablist">
          <button className={tab === 'tarefas' ? 'active' : ''} onClick={() => setTab('tarefas')} role="tab" aria-selected={tab === 'tarefas'}>
            Minhas tarefas
          </button>
          <button className={tab === 'sla' ? 'active' : ''} onClick={() => setTab('sla')} role="tab" aria-selected={tab === 'sla'}>
            SLA Comercial
            {resumoQuery.data && (resumoQuery.data.stats.estourado > 0) && (
              <span className="chip">{resumoQuery.data.stats.estourado}</span>
            )}
          </button>
        </div>

        {tab === 'tarefas' && (
          <>
            <div className="filters-bar">
              <div className="search">
                <input type="text" placeholder="Buscar por título" value={busca} onChange={(e) => setBusca(e.target.value)} />
              </div>
              <select className="filter-select" value={responsavelId} onChange={(e) => setResponsavelId(e.target.value)}>
                <option value="">Todos os responsáveis</option>
                {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
              </select>
              <select className="filter-select" value={tipo} onChange={(e) => setTipo(e.target.value)}>
                <option value="">Todos os tipos</option>
                {Object.entries(TIPO_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <select className="filter-select" value={prioridade} onChange={(e) => setPrioridade(e.target.value)}>
                <option value="">Toda prioridade</option>
                {Object.entries(PRIO_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <select className="filter-select" value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
                <option value="">Todas as empresas</option>
                {companies.map((c) => <option key={c.id} value={c.id}>{c.razao_social}</option>)}
              </select>
              <div className="period-filter">
                <input type="date" className="filter-select" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} title="De" />
                <span className="period-sep">até</span>
                <input type="date" className="filter-select" value={dataFim} onChange={(e) => setDataFim(e.target.value)} title="Até" />
              </div>
              <label className="chip-toggle">
                <input type="checkbox" checked={hideDone} onChange={(e) => setHideDone(e.target.checked)} />
                Ocultar concluídas
              </label>
            </div>

            <div className="card">
              {tasksQuery.isLoading && <p className="state-msg">Carregando tarefas…</p>}
              {tasksQuery.isError && <p className="state-msg error">Não foi possível carregar as tarefas agora.</p>}
              {tasksQuery.data && dates.length === 0 && <p className="state-msg">Nenhuma tarefa encontrada.</p>}

              {dates.map((d) => (
                <div key={d}>
                  <div className="agenda-date-label">{dateLabel(d)}</div>
                  {groups[d].map((t) => (
                    <TaskRow
                      key={t.id}
                      task={t}
                      companiesById={companiesById}
                      usersById={usersById}
                      slaItem={t.company_id ? slaByCompany[t.company_id] : undefined}
                      onComplete={() => completeMutation.mutate(t.id)}
                      onEdit={() => setModalTask(t)}
                      onDelete={() => setDeletingTask(t)}
                    />
                  ))}
                </div>
              ))}
            </div>
          </>
        )}

        {tab === 'sla' && <SlaComercialPanel usersById={usersById} />}
      </div>

      {modalTask !== undefined && (
        <TaskModal
          task={modalTask}
          companies={companies}
          users={users}
          onClose={() => setModalTask(undefined)}
          onSubmit={(data) => {
            if (modalTask?.id) updateMutation.mutate({ id: modalTask.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {deletingTask && (
        <div className="scrim show" onClick={() => setDeletingTask(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Excluir tarefa</h3>
            <p className="sub">Tem certeza que deseja excluir <strong>{deletingTask.titulo}</strong>?</p>
            <div className="row">
              <button className="btn-ghost" onClick={() => setDeletingTask(null)}>Cancelar</button>
              <button className="btn-danger" disabled={deleteMutation.isPending} onClick={() => deleteMutation.mutate(deletingTask.id)}>
                Excluir
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function TaskRow({ task, companiesById, usersById, slaItem, onComplete, onEdit, onDelete }) {
  const overdue = task.status === 'pendente' && dayDiff(task.data) < 0
  const done = task.status === 'concluida'
  const [msgOpen, setMsgOpen] = useState(false)
  const [copiado, setCopiado] = useState(false)
  // Tarefa de WhatsApp/LinkedIn gerada por Sequência com modelo já vem com o texto
  // mesclado (nome/empresa/etc.) em descricao — mostra painel de copiar/colar em
  // vez do resumo de uma linha só.
  const isMensagem = MESSAGE_TASK_TYPES.includes(task.tipo) && Boolean(task.descricao)

  async function handleCopy() {
    await copyText(task.descricao)
    setCopiado(true)
    setTimeout(() => setCopiado(false), 2000)
  }

  return (
    <div className={`task-row${overdue ? ' overdue' : ''}${done ? ' done' : ''}`}>
      <button
        className="task-check"
        disabled={done}
        title={done ? 'Concluída' : 'Marcar como concluída'}
        onClick={onComplete}
      >
        {done && '✓'}
      </button>
      <div className="task-body">
        <div className="task-title">{task.titulo}</div>
        {task.descricao && !isMensagem && <div className="task-descricao" title={task.descricao}>{task.descricao}</div>}
        <div className="task-meta-row">
          <span className="task-meta-item mono">{task.hora ? task.hora.slice(0, 5) : 'Dia todo'}</span>
          <span className="task-meta-item"><TaskTypeChip tipo={task.tipo} /></span>
          <span className={`prio prio-${task.prioridade}`}><span className="prio-dot" />{PRIO_LABEL[task.prioridade] ?? task.prioridade}</span>
          {overdue && <span className="overdue-pill">Atrasada {Math.abs(dayDiff(task.data))}d</span>}
          {task.company_id && <span className="task-meta-item link-chip">{companiesById[task.company_id] ?? '—'}</span>}
          {slaItem && <SlaBadge estado={slaItem.estado} />}
        </div>

        {isMensagem && (
          <button type="button" className="task-msg-toggle" onClick={() => setMsgOpen((v) => !v)}>
            {msgOpen ? 'Ocultar mensagem' : 'Ver mensagem'}
          </button>
        )}
        {isMensagem && msgOpen && (
          <div className="msg-panel">
            <div className="msg-panel-text">{task.descricao}</div>
            <div className="msg-panel-actions">
              <button type="button" className="btn-ghost" onClick={handleCopy}>{copiado ? 'Copiado ✓' : 'Copiar mensagem'}</button>
              {task.tipo === 'whatsapp' && task.contato_whatsapp && (
                <a
                  className="btn-whats"
                  target="_blank" rel="noopener noreferrer"
                  href={`https://wa.me/${task.contato_whatsapp.replace(/\D/g, '')}?text=${encodeURIComponent(task.descricao)}`}
                >
                  Abrir no WhatsApp
                </a>
              )}
              {task.tipo.startsWith('linkedin') && task.contato_linkedin && (
                <a className="btn-ghost" target="_blank" rel="noopener noreferrer" href={task.contato_linkedin}>
                  Abrir perfil no LinkedIn
                </a>
              )}
            </div>
          </div>
        )}
      </div>
      <div className="task-side">
        <span className="avatar" title={usersById[task.responsavel_id] ?? ''}>{initials(usersById[task.responsavel_id])}</span>
        <div className="task-actions">
          <button className="icon-btn" title="Editar" onClick={onEdit}>✎</button>
          <button className="icon-btn danger" title="Excluir" onClick={onDelete}>✕</button>
        </div>
      </div>
    </div>
  )
}

export function TaskModal({ task, companies, users, onClose, onSubmit, submitting, error }) {
  const isEdit = Boolean(task?.id)
  const roteiroRef = useRef(null)
  const snippetsQuery = useQuery({ queryKey: ['snippets', 'for-task-modal'], queryFn: () => listSnippets({ size: 100 }) })
  const snippets = snippetsQuery.data?.items ?? []
  const [form, setForm] = useState({
    titulo: task?.titulo ?? '',
    descricao: task?.descricao ?? '',
    tipo: task?.tipo ?? 'ligacao',
    prioridade: task?.prioridade ?? 'media',
    data: task?.data ?? new Date().toISOString().slice(0, 10),
    hora: task?.hora?.slice(0, 5) ?? '',
    responsavel_id: task?.responsavel_id ?? '',
    company_id: task?.company_id ?? '',
    contact_id: task?.contact_id ?? '',
    deal_id: task?.deal_id ?? '',
  })

  const contactsQuery = useQuery({
    queryKey: ['contacts', 'for-task', form.company_id],
    queryFn: () => listContacts({ companyId: form.company_id, size: 100 }),
    enabled: Boolean(form.company_id),
  })
  const dealsQuery = useQuery({
    queryKey: ['deals', 'for-task', form.company_id],
    queryFn: () => listDeals({ companyId: form.company_id, size: 100 }),
    enabled: Boolean(form.company_id),
  })

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  // Vars pro merge de snippet no roteiro ({{nome}}/{{empresa}}/{{cargo}}/{{responsavel}})
  // — mesma convenção de Snippets/Modelos de e-mail, preenchidas com o que já
  // estiver selecionado no formulário (fica em branco, sem mesclar, até selecionar).
  const selectedContact = (contactsQuery.data?.items ?? []).find((c) => c.id === form.contact_id)
  const selectedCompany = companies.find((c) => c.id === form.company_id)
  const selectedResponsavel = users.find((u) => u.id === form.responsavel_id)
  const roteiroVars = {
    nome: selectedContact?.nome,
    empresa: selectedCompany?.razao_social,
    cargo: selectedContact?.cargo,
    responsavel: selectedResponsavel?.nome,
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!form.titulo.trim() || !form.responsavel_id || !form.data) return
    onSubmit({
      titulo: form.titulo.trim(),
      descricao: form.descricao.trim() || null,
      tipo: form.tipo,
      prioridade: form.prioridade,
      data: form.data,
      hora: form.hora || null,
      responsavel_id: form.responsavel_id,
      company_id: form.company_id || null,
      contact_id: form.contact_id || null,
      deal_id: form.deal_id || null,
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div><h2>{isEdit ? 'Editar tarefa' : 'Nova tarefa'}</h2><p>Preencha os dados da tarefa</p></div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-group">
              <label className="f-label">Título <span className="req">*</span></label>
              <input className="f-input" value={form.titulo} onChange={set('titulo')} placeholder="Ex.: Ligar para confirmar reunião" required />
            </div>
            <div className="f-group">
              <label className="f-label">
                <span>Descrição / roteiro <span className="opt">opcional</span></span>
                <SnippetInsertButton
                  targetRef={roteiroRef}
                  value={form.descricao}
                  onChange={(v) => setForm((f) => ({ ...f, descricao: v }))}
                  vars={roteiroVars}
                />
              </label>
              <textarea
                ref={roteiroRef}
                className="f-input"
                rows={3}
                value={form.descricao}
                onChange={(e) => handleSnippetExpand(e, {
                  onChange: (v) => setForm((f) => ({ ...f, descricao: v })),
                  snippets,
                  vars: roteiroVars,
                })}
                placeholder="Roteiro / instruções para quem for executar… — digite #atalho e espaço pra inserir uma resposta rápida"
              />
            </div>
            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Tipo <span className="req">*</span></label>
                <select className="f-select" value={form.tipo} onChange={set('tipo')}>
                  {Object.entries(TIPO_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <div className="f-group">
                <label className="f-label">Prioridade</label>
                <select className="f-select" value={form.prioridade} onChange={set('prioridade')}>
                  {Object.entries(PRIO_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
            </div>
            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Data <span className="req">*</span></label>
                <input className="f-input" type="date" value={form.data} onChange={set('data')} required />
              </div>
              <div className="f-group">
                <label className="f-label">Hora <span className="opt">opcional — dia todo se em branco</span></label>
                <input className="f-input" type="time" value={form.hora} onChange={set('hora')} />
              </div>
            </div>
            <div className="f-group">
              <label className="f-label">Responsável <span className="req">*</span></label>
              <select className="f-select" value={form.responsavel_id} onChange={set('responsavel_id')} required>
                <option value="" disabled>Selecione</option>
                {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
              </select>
            </div>
            <div className="f-group">
              <label className="f-label">Empresa <span className="opt">opcional</span></label>
              <select
                className="f-select"
                value={form.company_id}
                onChange={(e) => setForm((f) => ({ ...f, company_id: e.target.value, contact_id: '', deal_id: '' }))}
              >
                <option value="">Nenhuma</option>
                {companies.map((c) => <option key={c.id} value={c.id}>{c.razao_social}</option>)}
              </select>
            </div>
            <div className="f-group">
              <label className="f-label">Contato <span className="opt">opcional</span></label>
              <select className="f-select" value={form.contact_id} onChange={set('contact_id')} disabled={!form.company_id}>
                <option value="">{form.company_id ? 'Nenhum' : 'Selecione uma empresa primeiro'}</option>
                {(contactsQuery.data?.items ?? []).map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
              </select>
            </div>
            <div className="f-group">
              <label className="f-label">Negócio <span className="opt">opcional</span></label>
              <select className="f-select" value={form.deal_id} onChange={set('deal_id')} disabled={!form.company_id}>
                <option value="">{form.company_id ? 'Nenhum' : 'Selecione uma empresa primeiro'}</option>
                {(dealsQuery.data?.items ?? []).map((d) => <option key={d.id} value={d.id}>{d.nome}</option>)}
              </select>
            </div>
            {error && <p className="state-msg error">Não foi possível salvar. Confira os dados e tente de novo.</p>}
          </div>
          <div className="drawer-foot">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---- SLA Comercial (docs/PLANO_SLA_COMERCIAL.md) --------------------------------

const SLA_ORIGEM_LABEL = { company_status: 'Status', milestone: 'Marco', deal_stage: 'Negócio' }

function SlaComercialPanel({ usersById }) {
  const queryClient = useQueryClient()
  const [ruleModal, setRuleModal] = useState(undefined) // undefined = fechado, null = criar, obj = editar
  const [deletingRule, setDeletingRule] = useState(null)
  const [filtro, setFiltro] = useState('todos')

  const rulesQuery = useQuery({ queryKey: ['sla-rules'], queryFn: listSlaRules })
  const resumoQuery = useQuery({ queryKey: ['sla-resumo'], queryFn: getSlaResumo })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['sla-rules'] })
    queryClient.invalidateQueries({ queryKey: ['sla-resumo'] })
  }

  const createMutation = useMutation({ mutationFn: createSlaRule, onSuccess: () => { setRuleModal(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateSlaRule(id, data), onSuccess: () => { setRuleModal(undefined); invalidate() } })
  const deleteMutation = useMutation({ mutationFn: deleteSlaRule, onSuccess: () => { setDeletingRule(null); invalidate() } })
  const toggleMutation = useMutation({ mutationFn: ({ id, ativo }) => updateSlaRule(id, { ativo }), onSuccess: invalidate })

  const rules = rulesQuery.data ?? []
  const stats = resumoQuery.data?.stats
  const items = resumoQuery.data?.items ?? []
  const filteredItems = filtro === 'todos' ? items : items.filter((i) => i.estado === filtro)

  return (
    <div className="view-panel">
      <div className="info-banner">
        <span>
          <b>SLA por etapa de negócio</b> (ex.: "Proposta enviada, 48h") continua sendo editado em
          Configurações › Pipelines — aparece automaticamente no painel de cumprimento abaixo, sem precisar
          duplicar a configuração aqui. As regras desta tela cobrem os dois gatilhos que faltavam: status da
          empresa/lead e marcos que disparam uma vez só (ex.: 1ª reunião como cliente).
        </span>
      </div>

      <div className="stat-strip">
        <div className="stat-tile"><div className="t">Regras ativas</div><div className="v">{stats ? `${stats.regras_ativas} / ${stats.regras_total}` : '—'}</div></div>
        <div className="stat-tile"><div className="t">Em dia</div><div className="v" style={{ color: 'var(--good)' }}>{stats?.em_dia ?? '—'}</div></div>
        <div className="stat-tile"><div className="t">Em risco</div><div className="v" style={{ color: 'var(--warning)' }}>{stats?.em_risco ?? '—'}</div></div>
        <div className="stat-tile"><div className="t">Estourado</div><div className="v" style={{ color: 'var(--critical)' }}>{stats?.estourado ?? '—'}</div></div>
        <div className="stat-tile"><div className="t">Cumprido</div><div className="v" style={{ color: 'var(--good)' }}>{stats?.cumprido ?? '—'}</div></div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h3>Regras de SLA</h3>
            <p>Prazo entre a empresa entrar num status/marco e uma atividade do tipo certo ser concluída.</p>
          </div>
          <button className="btn-primary" onClick={() => setRuleModal(null)}>+ Nova regra</button>
        </div>
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr><th>Regra</th><th>Gatilho</th><th>Prazo</th><th>Atividade esperada</th><th>Ativa</th><th className="actions-col"></th></tr>
            </thead>
            <tbody>
              {rulesQuery.isLoading && <tr><td colSpan={6} className="empty-cell">Carregando regras…</td></tr>}
              {rulesQuery.isError && <tr><td colSpan={6} className="empty-cell error">Não foi possível carregar as regras agora.</td></tr>}
              {rulesQuery.data && rules.length === 0 && (
                <tr><td colSpan={6} className="empty-cell">Nenhuma regra cadastrada ainda — comece com "Nova regra".</td></tr>
              )}
              {rules.map((r) => (
                <tr key={r.id}>
                  <td className="row-title">{r.nome}</td>
                  <td className="row-sub" style={{ fontFamily: 'inherit' }}>
                    {GATILHO_TIPO_LABEL[r.gatilho_tipo] ?? r.gatilho_tipo} · vira {COMPANY_STATUS_LABEL[r.gatilho_valor] ?? r.gatilho_valor}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }}>{r.prazo_horas}h</td>
                  <td className="row-sub" style={{ fontFamily: 'inherit' }}>
                    {r.tipo_atividade_esperado ? (TIPO_LABEL[r.tipo_atividade_esperado] ?? r.tipo_atividade_esperado) : 'Qualquer atividade'}
                  </td>
                  <td>
                    <label className="switch">
                      <input
                        type="checkbox" checked={r.ativo}
                        onChange={(e) => toggleMutation.mutate({ id: r.id, ativo: e.target.checked })}
                      />
                      <span className="track" />
                    </label>
                  </td>
                  <td className="actions-col">
                    <button className="icon-btn" title="Editar" onClick={() => setRuleModal(r)}>✎</button>
                    <button className="icon-btn danger" title="Excluir" onClick={() => setDeletingRule(r)}>✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h3>Painel de cumprimento</h3>
            <p>Empresas com uma régua de SLA em curso ou resolvida (companies vencendo/venceram no período mais recente).</p>
          </div>
          <div className="segmented">
            {[['todos', 'Todos'], ['em_risco', 'Em risco'], ['estourado', 'Estourado'], ['cumprido', 'Cumprido']].map(([v, l]) => (
              <button key={v} className={filtro === v ? 'active' : ''} onClick={() => setFiltro(v)}>{l}</button>
            ))}
          </div>
        </div>
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr><th>Empresa</th><th>Origem</th><th>Regra aplicada</th><th>Disparado em</th><th>Prazo</th><th>Status</th><th>Responsável</th></tr>
            </thead>
            <tbody>
              {resumoQuery.isLoading && <tr><td colSpan={7} className="empty-cell">Carregando…</td></tr>}
              {resumoQuery.isError && <tr><td colSpan={7} className="empty-cell error">Não foi possível carregar o painel agora.</td></tr>}
              {resumoQuery.data && filteredItems.length === 0 && <tr><td colSpan={7} className="empty-cell">Nenhuma empresa neste filtro.</td></tr>}
              {filteredItems.map((it, idx) => (
                <tr key={`${it.origem}-${it.regra_id}-${it.company_id}-${idx}`}>
                  <td className="row-title">{it.empresa_nome}</td>
                  <td><span className="origin-tag">{SLA_ORIGEM_LABEL[it.origem] ?? it.origem}</span></td>
                  <td className="row-sub" style={{ fontFamily: 'inherit' }}>{it.regra_nome}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{fmtDateTime(it.gatilho_em)}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{fmtDateTime(it.prazo_em)}</td>
                  <td>
                    <SlaBadge estado={it.estado} />
                    <div className="row-sub">
                      {it.estado === 'estourado' && `+${fmtHoras(it.horas_atraso)} de atraso`}
                      {it.estado === 'cumprido' && 'concluída a tempo'}
                      {(it.estado === 'em_risco' || it.estado === 'em_andamento') && `${fmtHoras(it.horas_restantes)} restantes`}
                    </div>
                  </td>
                  <td>
                    <div className="row-resp">
                      <span className="avatar">{initials(usersById[it.responsavel_id])}</span>
                      {usersById[it.responsavel_id] ?? '—'}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {ruleModal !== undefined && (
        <SlaRuleModal
          rule={ruleModal}
          onClose={() => setRuleModal(undefined)}
          onSubmit={(data) => {
            if (ruleModal?.id) updateMutation.mutate({ id: ruleModal.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {deletingRule && (
        <div className="scrim show" onClick={() => setDeletingRule(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Excluir regra de SLA</h3>
            <p className="sub">Tem certeza que deseja excluir <strong>{deletingRule.nome}</strong>?</p>
            <div className="row">
              <button className="btn-ghost" onClick={() => setDeletingRule(null)}>Cancelar</button>
              <button className="btn-danger" disabled={deleteMutation.isPending} onClick={() => deleteMutation.mutate(deletingRule.id)}>
                Excluir
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function SlaRuleModal({ rule, onClose, onSubmit, submitting, error }) {
  const isEdit = Boolean(rule?.id)
  const [form, setForm] = useState({
    nome: rule?.nome ?? '',
    gatilho_tipo: rule?.gatilho_tipo ?? 'company_status',
    gatilho_valor: rule?.gatilho_valor ?? 'lead',
    prazo_horas: rule?.prazo_horas ?? 24,
    tipo_atividade_esperado: rule?.tipo_atividade_esperado ?? '',
    ativo: rule?.ativo ?? true,
  })

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!form.nome.trim() || !form.prazo_horas) return
    onSubmit({
      nome: form.nome.trim(),
      gatilho_tipo: form.gatilho_tipo,
      gatilho_valor: form.gatilho_valor,
      prazo_horas: Number(form.prazo_horas),
      tipo_atividade_esperado: form.tipo_atividade_esperado || null,
      ativo: form.ativo,
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div><h2>{isEdit ? 'Editar regra de SLA' : 'Nova regra de SLA'}</h2><p>Prazo entre o gatilho e uma atividade concluída</p></div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-group">
              <label className="f-label">Nome da regra <span className="req">*</span></label>
              <input className="f-input" value={form.nome} onChange={set('nome')} placeholder="Ex.: Responder novo lead" required />
            </div>
            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Gatilho</label>
                <select className="f-select" value={form.gatilho_tipo} onChange={set('gatilho_tipo')}>
                  <option value="company_status">Status da empresa</option>
                  <option value="milestone">Marco (dispara 1x)</option>
                </select>
              </div>
              <div className="f-group">
                <label className="f-label">Quando</label>
                <select className="f-select" value={form.gatilho_valor} onChange={set('gatilho_valor')}>
                  {Object.entries(COMPANY_STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>vira {l}</option>)}
                </select>
              </div>
            </div>
            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Prazo (horas) <span className="req">*</span></label>
                <input className="f-input" type="number" min="1" value={form.prazo_horas} onChange={set('prazo_horas')} required />
              </div>
              <div className="f-group">
                <label className="f-label">Atividade esperada</label>
                <select className="f-select" value={form.tipo_atividade_esperado} onChange={set('tipo_atividade_esperado')}>
                  <option value="">Qualquer atividade</option>
                  {Object.entries(TIPO_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
            </div>
            <p className="f-hint">
              Cumprida = existe uma tarefa desse tipo <strong>concluída</strong> depois do gatilho e antes do
              prazo. "Qualquer atividade" aceita qualquer tarefa concluída vinculada à empresa.
            </p>
            <label className="chip-toggle">
              <input type="checkbox" checked={form.ativo} onChange={(e) => setForm((f) => ({ ...f, ativo: e.target.checked }))} />
              Regra ativa
            </label>
            {error && <p className="state-msg error">Não foi possível salvar. Confira os dados e tente de novo.</p>}
          </div>
          <div className="drawer-foot">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
