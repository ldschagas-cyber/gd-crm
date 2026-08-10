import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  completeTask, getTask, sendTaskEmail, uncompleteTask, updateTask,
} from '../api/tasks'
import { getCompany } from '../api/companies'
import { getContact } from '../api/contacts'
import { getDeal } from '../api/deals'
import { listSnippets } from '../api/snippets'
import { listEmailTemplates } from '../api/emailTemplates'
import { getIntegration } from '../api/me'
import { useSoftphone } from '../context/SoftphoneContext'
import { useAuth } from '../context/AuthContext'
import { TIPO_LABEL, TaskTypeChip } from '../components/TaskTypeIcon'
import SnippetInsertButton from '../components/SnippetInsertButton'
import { handleSnippetExpand, mergeSnippetVars } from '../utils/snippets'
import './TaskQueuePage.css'

// Espelha ResultadoLigacao em app/models/task.py — desfechos padrão de mercado
// (docs/PLANO_FILA_TAREFAS.md, ponto 3).
const RESULTADO_LABEL = {
  atendeu: 'Atendeu',
  recado_caixa_postal: 'Deixou recado / caixa postal',
  nao_atendeu: 'Não atendeu',
  ocupado: 'Ocupado',
  numero_errado: 'Número errado / inexistente',
  recusou_falar: 'Recusou falar',
}

function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}

function statusLabel(status, seconds) {
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0')
  const ss = String(seconds % 60).padStart(2, '0')
  switch (status) {
    case 'dialing': return 'Discando…'
    case 'ringing': return 'Chamando…'
    case 'in-call': return `Em chamada — ${mm}:${ss}`
    case 'incoming': return 'Chamada recebida'
    default: return 'Pronto para ligar'
  }
}

export default function TaskQueuePage() {
  const location = useLocation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const taskIds = location.state?.taskIds ?? []
  const [index, setIndex] = useState(0)
  const currentId = taskIds[index]

  const taskQuery = useQuery({
    queryKey: ['tasks', 'queue', currentId],
    queryFn: () => getTask(currentId),
    enabled: Boolean(currentId),
  })
  const task = taskQuery.data

  const companyQuery = useQuery({
    queryKey: ['companies', 'for-queue', task?.company_id],
    queryFn: () => getCompany(task.company_id),
    enabled: Boolean(task?.company_id),
  })
  const contactQuery = useQuery({
    queryKey: ['contacts', 'for-queue', task?.contact_id],
    queryFn: () => getContact(task.contact_id),
    enabled: Boolean(task?.contact_id),
  })
  const dealQuery = useQuery({
    queryKey: ['deals', 'for-queue', task?.deal_id],
    queryFn: () => getDeal(task.deal_id),
    enabled: Boolean(task?.deal_id),
  })

  function handleUpdated(updated) {
    queryClient.setQueryData(['tasks', 'queue', updated.id], updated)
    queryClient.invalidateQueries({ queryKey: ['tasks'] })
  }

  const completeMutation = useMutation({
    mutationFn: () => completeTask(task.id),
    onSuccess: handleUpdated,
  })
  const uncompleteMutation = useMutation({
    mutationFn: () => uncompleteTask(task.id),
    onSuccess: handleUpdated,
  })

  function backToList() {
    navigate('/tarefas')
  }

  if (taskIds.length === 0) {
    return (
      <div className="content">
        <div className="card tq-empty">
          <h3>Nenhuma fila em andamento</h3>
          <p>A fila de execução abre a partir da lista filtrada em Tarefas — volte lá e clique em "Iniciar tarefas".</p>
          <button className="btn-primary" onClick={backToList}>Ir para Tarefas</button>
        </div>
      </div>
    )
  }

  return (
    <div className="tq-shell">
      <div className="tq-top">
        <button className="tq-back" onClick={backToList}>
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12.5 15.5L7 10l5.5-5.5" /></svg>
          Tarefas
        </button>
        <div className="tq-sep" />
        <div className="tq-title">
          {task ? task.titulo : 'Carregando…'}
          {task && (contactQuery.data || companyQuery.data) && (
            <span> · {contactQuery.data?.nome ?? companyQuery.data?.nome_fantasia ?? companyQuery.data?.razao_social}</span>
          )}
        </div>
        <div className="tq-spacer" />
        <div className="tq-counter">
          <button className="tq-arrow" disabled={index === 0} onClick={() => setIndex((i) => i - 1)} title="Tarefa anterior">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12.5 15.5L7 10l5.5-5.5" /></svg>
          </button>
          Tarefa <b>{index + 1}</b>/{taskIds.length}
          <button className="tq-arrow" disabled={index === taskIds.length - 1} onClick={() => setIndex((i) => i + 1)} title="Próxima tarefa">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M7.5 4.5L13 10l-5.5 5.5" /></svg>
          </button>
        </div>
        {task && (
          <label className="tq-done">
            <input
              type="checkbox"
              checked={task.status === 'concluida'}
              disabled={completeMutation.isPending || uncompleteMutation.isPending}
              onChange={(e) => (e.target.checked ? completeMutation.mutate() : uncompleteMutation.mutate())}
            />
            Concluído
          </label>
        )}
        <button className="tq-close" onClick={backToList} title="Fechar fila">✕</button>
      </div>

      {taskQuery.isLoading && <div className="content"><p className="state-msg">Carregando tarefa…</p></div>}
      {taskQuery.isError && <div className="content"><p className="state-msg error">Não foi possível carregar essa tarefa.</p></div>}

      {task && (
        <div className="tq-body">
          <ContextCard
            key={`ctx-${task.id}`}
            task={task}
            company={companyQuery.data}
            contact={contactQuery.data}
            deal={dealQuery.data}
            onUpdated={handleUpdated}
          />
          <ActionPanel
            key={`action-${task.id}`}
            task={task}
            company={companyQuery.data}
            contact={contactQuery.data}
            deal={dealQuery.data}
            onCompleted={handleUpdated}
          />
        </div>
      )}
    </div>
  )
}

function ContextCard({ task, company, contact, deal, onUpdated }) {
  const roteiroRef = useRef(null)
  const [descricao, setDescricao] = useState(task.descricao ?? '')

  const snippetsQuery = useQuery({ queryKey: ['snippets', 'for-queue-roteiro'], queryFn: () => listSnippets({ size: 100 }) })
  const snippets = snippetsQuery.data?.items ?? []

  const vars = {
    nome: contact?.nome,
    empresa: company?.nome_fantasia || company?.razao_social,
    cargo: contact?.cargo,
  }

  const saveMutation = useMutation({
    mutationFn: (novaDescricao) => updateTask(task.id, { descricao: novaDescricao || null }),
    onSuccess: onUpdated,
  })

  function handleBlur() {
    if (descricao !== (task.descricao ?? '')) saveMutation.mutate(descricao)
  }

  const nomeExibicao = contact?.nome ?? company?.nome_fantasia ?? company?.razao_social ?? task.titulo
  const subtitulo = [contact?.cargo, company?.nome_fantasia ?? company?.razao_social].filter(Boolean).join(' · ')

  return (
    <div className="card tq-context">
      <div className="card-head"><h3>Contato</h3></div>
      <div className="tq-context-body">
        <div className="tq-ctx-name">{nomeExibicao}</div>
        {subtitulo && <div className="tq-ctx-sub">{subtitulo}</div>}

        <ul className="tq-ctx-list">
          {contact?.telefone && <li>{contact.telefone}</li>}
          {contact?.email && <li>{contact.email}</li>}
          {company && <li><Link to={`/empresas/${company.id}`}>{company.nome_fantasia || company.razao_social}</Link></li>}
          {deal && <li>Negócio: <Link to={`/negocios/${deal.id}`}>{deal.nome}</Link></li>}
          {!contact && !company && <li className="tq-ctx-empty">Tarefa sem contato/empresa vinculado.</li>}
        </ul>

        {contact && <Link className="tq-ctx-full-link" to={`/contatos/${contact.id}`}>Abrir ficha completa →</Link>}

        <div className="tq-roteiro-wrap">
          <div className="tq-roteiro-head">
            <h4>Roteiro da tarefa</h4>
            <SnippetInsertButton targetRef={roteiroRef} value={descricao} onChange={setDescricao} vars={vars} />
          </div>
          <textarea
            ref={roteiroRef}
            className="tq-roteiro-box"
            rows={7}
            value={descricao}
            onChange={(e) => handleSnippetExpand(e, { onChange: setDescricao, snippets, vars })}
            onBlur={handleBlur}
            placeholder="Roteiro / instruções — digite #atalho e espaço pra inserir um snippet"
          />
          <div className="tq-roteiro-caption">
            {saveMutation.isPending ? 'Salvando…' : 'Salvo no campo Descrição da tarefa.'}
          </div>
        </div>
      </div>
    </div>
  )
}

function ActionPanel({ task, company, contact, deal, onCompleted }) {
  if (task.tipo === 'ligacao') return <CallPanel task={task} company={company} contact={contact} deal={deal} onCompleted={onCompleted} />
  if (task.tipo === 'email') return <EmailPanel task={task} company={company} contact={contact} onCompleted={onCompleted} />
  return <GenericPanel task={task} onCompleted={onCompleted} />
}

function CallPanel({ task, company, contact, deal, onCompleted }) {
  const { status, conectado, seconds, call, hangup } = useSoftphone()
  const [showOutcome, setShowOutcome] = useState(false)
  const [resultado, setResultado] = useState('atendeu')
  const [observacoes, setObservacoes] = useState('')
  const wasCallingRef = useRef(false)

  useEffect(() => {
    if (status !== 'idle' && status !== 'incoming') wasCallingRef.current = true
    else if (status === 'idle' && wasCallingRef.current) {
      wasCallingRef.current = false
      setShowOutcome(true)
    }
  }, [status])

  const completeMutation = useMutation({
    mutationFn: () => completeTask(task.id, { resultado_ligacao: resultado, observacoes: observacoes || null }),
    onSuccess: (updated) => { onCompleted(updated); setShowOutcome(false) },
  })

  const numero = contact?.telefone || company?.telefone
  const emChamada = status !== 'idle' && status !== 'incoming'

  return (
    <div className="card tq-action-panel">
      <div className="tq-action-head">
        <TaskTypeChip tipo="ligacao" />
        <span className="tq-action-title">{task.titulo}</span>
      </div>
      <div className="tq-action-body tq-call">
        <div className="tq-call-avatar">{initials(contact?.nome ?? company?.razao_social)}</div>
        <div className="tq-call-phone">{numero || 'Sem telefone cadastrado'}</div>

        {!conectado ? (
          <p className="tq-generic-info">
            Chamadas ainda não configuradas — peça pro administrador conectar o Twilio Voice em Preferências → Chamadas.
          </p>
        ) : (
          <>
            <div className={`tq-call-status${status === 'in-call' ? ' live' : ''}`}>{statusLabel(status, seconds)}</div>
            {!emChamada && !showOutcome && (
              <button
                className="btn-primary"
                disabled={!numero}
                onClick={() => call(numero, { label: contact?.nome ?? company?.razao_social, contactId: contact?.id, companyId: company?.id, dealId: deal?.id })}
              >
                Ligar
              </button>
            )}
            {emChamada && <button className="btn-danger" onClick={hangup}>Encerrar</button>}
          </>
        )}

        {showOutcome && (
          <div className="tq-call-outcome">
            <label>Resultado da ligação</label>
            <select value={resultado} onChange={(e) => setResultado(e.target.value)}>
              {Object.entries(RESULTADO_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <textarea
              placeholder="Anotações da ligação…"
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
            />
            <button className="btn-primary" disabled={completeMutation.isPending} onClick={() => completeMutation.mutate()}>
              {completeMutation.isPending ? 'Salvando…' : 'Concluir tarefa'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function EmailPanel({ task, company, contact, onCompleted }) {
  const { user } = useAuth()
  const corpoRef = useRef(null)
  const [showTemplates, setShowTemplates] = useState(false)
  const [assunto, setAssunto] = useState(task.titulo)
  const [corpo, setCorpo] = useState(task.descricao ?? '')

  const integrationQuery = useQuery({ queryKey: ['me', 'integration', 'email'], queryFn: () => getIntegration('email') })
  const templatesQuery = useQuery({ queryKey: ['email-templates', 'for-queue'], queryFn: () => listEmailTemplates({ size: 100 }) })
  const snippetsQuery = useQuery({ queryKey: ['snippets', 'for-queue-email'], queryFn: () => listSnippets({ size: 100 }) })
  const templates = templatesQuery.data?.items ?? []
  const snippets = snippetsQuery.data?.items ?? []
  const conectado = integrationQuery.data?.ativo ?? false

  const vars = {
    nome: contact?.nome,
    empresa: company?.nome_fantasia || company?.razao_social,
    cargo: contact?.cargo,
    responsavel: user?.nome,
  }

  const sendMutation = useMutation({
    mutationFn: () => sendTaskEmail(task.id, { destinatario: contact.email, assunto, corpo }),
    onSuccess: onCompleted,
  })

  function applyTemplate(t) {
    setAssunto(mergeSnippetVars(t.assunto, vars))
    setCorpo(mergeSnippetVars(t.corpo, vars))
    setShowTemplates(false)
  }

  function openMailto() {
    window.location.href = `mailto:${contact?.email ?? ''}?subject=${encodeURIComponent(assunto)}&body=${encodeURIComponent(corpo)}`
  }

  if (!contact?.email) {
    return (
      <div className="card tq-action-panel">
        <div className="tq-action-head"><TaskTypeChip tipo="email" /><span className="tq-action-title">{task.titulo}</span></div>
        <div className="tq-action-body">
          <p className="tq-generic-info">Esse contato não tem e-mail cadastrado — não dá pra enviar por aqui.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card tq-action-panel">
      <div className="tq-action-head"><TaskTypeChip tipo="email" /><span className="tq-action-title">{task.titulo}</span></div>
      <div className="tq-action-body">
        {integrationQuery.isSuccess && !conectado && (
          <div className="tq-generic-info tq-warning">
            Você ainda não conectou sua conta Microsoft 365 em <Link to="/preferencias?tab=email">Preferências → E-mail</Link>.
            Sem isso o CRM não consegue enviar por você — "Abrir no meu e-mail" abre o rascunho no seu cliente de
            e-mail padrão, e a tarefa fica pra você confirmar manualmente que enviou.
          </div>
        )}

        <div className="tq-mail-row"><span className="k">Para</span><span className="v">{contact.nome} &lt;{contact.email}&gt;</span></div>
        <div className="tq-mail-row"><span className="k">De</span><span className="v">{user?.nome} &lt;{user?.email}&gt;</span></div>

        <div className="tq-mail-toolbar">
          <span className="snippet-insert">
            <button type="button" className="tq-mail-chip" onClick={() => setShowTemplates((o) => !o)}>Modelos</button>
            {showTemplates && (
              <div className="snippet-insert-menu">
                {templates.length === 0 && <div className="snippet-insert-empty">Nenhum modelo cadastrado.</div>}
                {templates.map((t) => (
                  <button type="button" key={t.id} className="snippet-insert-opt" onClick={() => applyTemplate(t)}>
                    <b>{t.nome}</b><span>{t.assunto}</span>
                  </button>
                ))}
              </div>
            )}
          </span>
          <SnippetInsertButton targetRef={corpoRef} value={corpo} onChange={setCorpo} vars={vars} />
        </div>

        <input className="tq-mail-subject" value={assunto} onChange={(e) => setAssunto(e.target.value)} placeholder="Assunto" />
        <textarea
          ref={corpoRef}
          className="tq-mail-body"
          value={corpo}
          onChange={(e) => handleSnippetExpand(e, { onChange: setCorpo, snippets, vars })}
          placeholder="Escreva o e-mail…"
        />

        {conectado ? (
          <button className="btn-primary" disabled={sendMutation.isPending} onClick={() => sendMutation.mutate()}>
            {sendMutation.isPending ? 'Enviando…' : 'Enviar e concluir tarefa'}
          </button>
        ) : (
          <button className="btn-primary" onClick={openMailto}>Abrir no meu e-mail</button>
        )}
        {sendMutation.isError && (
          <p className="state-msg error">
            {sendMutation.error?.response?.data?.error?.message ?? 'Não foi possível enviar. Confira a integração e tente de novo.'}
          </p>
        )}
      </div>
    </div>
  )
}

function GenericPanel({ task, onCompleted }) {
  const completeMutation = useMutation({ mutationFn: () => completeTask(task.id), onSuccess: onCompleted })
  const done = task.status === 'concluida'
  return (
    <div className="card tq-action-panel">
      <div className="tq-action-head">
        <TaskTypeChip tipo={task.tipo} />
        <span className="tq-action-title">{task.titulo}</span>
      </div>
      <div className="tq-action-body">
        <p className="tq-generic-info">
          {TIPO_LABEL[task.tipo] ?? task.tipo} não tem uma ação automática aqui — use o roteiro ao lado e conclua
          manualmente quando terminar, ou avance pra próxima tarefa sem concluir.
        </p>
        <button className="btn-primary" disabled={done || completeMutation.isPending} onClick={() => completeMutation.mutate()}>
          {done ? 'Concluída' : completeMutation.isPending ? 'Concluindo…' : 'Concluir tarefa'}
        </button>
      </div>
    </div>
  )
}
