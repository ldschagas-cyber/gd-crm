import { useNavigate } from 'react-router-dom'
import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  completeTask, createTask, deleteTask, exportTasks, listTasks, updateTask,
} from '../api/tasks'
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
          <button className="btn-ghost" onClick={() => exportTasks(filters)}>Exportar</button>
          <button className="btn-primary" disabled={pendentes.length === 0} onClick={iniciarFila}>
            ▸ Iniciar {pendentes.length} tarefa{pendentes.length === 1 ? '' : 's'}
          </button>
          <button className="btn-primary" onClick={() => setModalTask(null)}>+ Nova tarefa</button>
        </div>
      </header>

      <div className="content">
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
                  onComplete={() => completeMutation.mutate(t.id)}
                  onEdit={() => setModalTask(t)}
                  onDelete={() => setDeletingTask(t)}
                />
              ))}
            </div>
          ))}
        </div>
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

function TaskRow({ task, companiesById, usersById, onComplete, onEdit, onDelete }) {
  const overdue = task.status === 'pendente' && dayDiff(task.data) < 0
  const done = task.status === 'concluida'

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
        {task.descricao && <div className="task-descricao" title={task.descricao}>{task.descricao}</div>}
        <div className="task-meta-row">
          <span className="task-meta-item mono">{task.hora ? task.hora.slice(0, 5) : 'Dia todo'}</span>
          <span className="task-meta-item"><TaskTypeChip tipo={task.tipo} /></span>
          <span className={`prio prio-${task.prioridade}`}><span className="prio-dot" />{PRIO_LABEL[task.prioridade] ?? task.prioridade}</span>
          {overdue && <span className="overdue-pill">Atrasada {Math.abs(dayDiff(task.data))}d</span>}
          {task.company_id && <span className="task-meta-item link-chip">{companiesById[task.company_id] ?? '—'}</span>}
        </div>
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
                placeholder="Roteiro / instruções para quem for executar… — digite #atalho e espaço pra inserir um snippet"
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
