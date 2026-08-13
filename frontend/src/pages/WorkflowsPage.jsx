import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createWorkflow, deleteWorkflow, listWorkflowLogs, listWorkflows, updateWorkflow } from '../api/workflows'
import { listEmailTemplates } from '../api/emailTemplates'
import { listPipelines } from '../api/pipelines'
import { listSequences } from '../api/sequences'
import { TIPO_LABEL as TIPO_TAREFA_LABEL } from '../components/TaskTypeIcon'
import '../styles/dataTable.css'
import './WorkflowsPage.css'

const GATILHO_LABEL = {
  empresa_criada: 'Empresa criada', contato_criado: 'Contato criado', negocio_criado: 'Negócio criado',
  mudanca_etapa: 'Mudança de etapa', resposta_recebida: 'Resposta recebida',
}
const GATILHO_HINT = {
  empresa_criada: 'Dispara assim que uma empresa é cadastrada (manual, importação ou Pesquisa de Leads promovida).',
  contato_criado: 'Dispara quando um novo contato é cadastrado em qualquer empresa.',
  negocio_criado: 'Dispara quando um negócio novo entra no Pipeline.',
  mudanca_etapa: 'Dispara toda vez que um negócio muda de etapa no board de Negócios.',
  resposta_recebida: 'Depende da integração de e-mail (Microsoft 365) em Preferências — sem isso conectado, esse gatilho nunca dispara de verdade.',
}
const GATILHO_CAMPOS = {
  empresa_criada: ['origem', 'segmento', 'uf', 'porte'],
  contato_criado: ['cargo'],
  negocio_criado: ['pipeline', 'origem', 'valor_previsto'],
  mudanca_etapa: ['etapa_destino', 'pipeline'],
  resposta_recebida: ['canal'],
}
const OPERADORES = ['igual a', 'diferente de', 'contém', 'maior que', 'menor que']
const TIPO_ACAO_LABEL = {
  criar_tarefa: 'Criar tarefa', enviar_email: 'Enviar e-mail', alterar_pipeline: 'Alterar etapa',
  notificar_usuario: 'Notificar usuário', inscrever_em_sequencia: 'Inscrever em Sequência',
  executar_enriquecimento: 'Executar enriquecimento (IA)',
}
const DESTINATARIOS = ['Responsável pelo registro', 'Gestor comercial', 'Administrador']
const RESULTADO_LABEL = { sucesso: '✓', erro: '✕' }

function defaultParams(tipo) {
  if (tipo === 'criar_tarefa') return { titulo: '', tipo_tarefa: 'followup', dias_apos: 0, destinatario: DESTINATARIOS[0] }
  if (tipo === 'enviar_email') return { template_id: '', dias_apos: 0 }
  if (tipo === 'alterar_pipeline') return { stage_id: '' }
  if (tipo === 'notificar_usuario') return { destinatario: DESTINATARIOS[0], mensagem: '' }
  if (tipo === 'inscrever_em_sequencia') return { sequence_id: '' }
  return {}
}

function IconInfo() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="10" r="7.3" />
      <path d="M10 9v4.2" strokeLinecap="round" />
      <circle cx="10" cy="6.8" r=".9" fill="currentColor" stroke="none" />
    </svg>
  )
}

export default function WorkflowsPage() {
  const queryClient = useQueryClient()
  const [drawerWorkflow, setDrawerWorkflow] = useState(undefined) // undefined = fechado, null = novo, obj = editar
  const [helpOpen, setHelpOpen] = useState(false)

  const listQuery = useQuery({ queryKey: ['workflows', 'list'], queryFn: () => listWorkflows({ size: 100 }) })
  const items = listQuery.data?.items ?? []

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['workflows'] })
  }

  const createMutation = useMutation({ mutationFn: createWorkflow, onSuccess: () => { setDrawerWorkflow(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateWorkflow(id, data), onSuccess: () => { setDrawerWorkflow(undefined); invalidate() } })
  const deleteMutation = useMutation({ mutationFn: deleteWorkflow, onSuccess: invalidate })

  const totalAtivos = items.filter((w) => w.ativo).length

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Workflows</h1>
          <p>{items.length.toLocaleString('pt-BR')} workflow(s) · {totalAtivos} ativo(s)</p>
        </div>
        <button className="btn-primary" onClick={() => setDrawerWorkflow(null)}>+ Novo workflow</button>
      </header>

      <div className="content">
        <button className="info-trigger" onClick={() => setHelpOpen(true)}>
          <IconInfo /> Como funcionam os workflows
        </button>

        <div className="card">
          {listQuery.isLoading && <p className="state-msg">Carregando workflows…</p>}
          {listQuery.isError && <p className="state-msg error">Não foi possível carregar os workflows agora.</p>}

          {listQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>Workflow</th>
                    <th>Gatilho</th>
                    <th>Status</th>
                    <th>Ações</th>
                    <th className="actions-col"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((w) => (
                    <tr key={w.id}>
                      <td>
                        <div className="row-title" onClick={() => setDrawerWorkflow(w)}>{w.nome}</div>
                        <div className="row-sub">{w.condicoes.length} condição(ões) · {w.actions.length} ação(ões)</div>
                      </td>
                      <td><span className="trigger-pill">{GATILHO_LABEL[w.gatilho] ?? w.gatilho}</span></td>
                      <td><span className={`status-pill ${w.ativo ? 'ativo' : 'inativo'}`}><span className="d" />{w.ativo ? 'Ativo' : 'Inativo'}</span></td>
                      <td className="mono">{w.actions.length}</td>
                      <td className="actions-col">
                        <button className="icon-btn" title="Editar" onClick={() => setDrawerWorkflow(w)}>✎</button>
                        <button
                          className="icon-btn danger"
                          title="Excluir"
                          onClick={() => { if (confirm(`Excluir "${w.nome}"? O histórico de execuções é preservado, mas ele deixa de disparar novas ações.`)) deleteMutation.mutate(w.id) }}
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && <tr><td colSpan={5} className="empty-cell">Nenhum workflow cadastrado.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {drawerWorkflow !== undefined && (
        <WorkflowDrawer
          workflow={drawerWorkflow}
          onClose={() => setDrawerWorkflow(undefined)}
          onSubmit={(data) => {
            if (drawerWorkflow) updateMutation.mutate({ id: drawerWorkflow.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {helpOpen && (
        <div className="scrim show" onClick={() => setHelpOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3><IconInfo />Como funcionam os workflows</h3>
            <p className="sub">
              Motor evento → condição → ação: quando um gatilho acontece (empresa criada, negócio criado, mudança
              de etapa, resposta recebida…), o workflow verifica as condições e dispara as ações em cadeia. A ação{' '}
              <b>Executar enriquecimento</b> atualiza o Resumo Executivo e a Próxima ação sugerida da empresa via IA
              (mesmo motor do Dossiê Comercial), sem precisar clicar em "Aplicar".
            </p>
            <div className="row"><button className="btn-ghost" onClick={() => setHelpOpen(false)}>Fechar</button></div>
          </div>
        </div>
      )}
    </>
  )
}

function WorkflowDrawer({ workflow, onClose, onSubmit, submitting, error }) {
  const [nome, setNome] = useState(workflow?.nome ?? '')
  const [ativo, setAtivo] = useState(workflow?.ativo ?? true)
  const [gatilho, setGatilho] = useState(workflow?.gatilho ?? 'empresa_criada')
  const [condicoes, setCondicoes] = useState(workflow?.condicoes ?? [])
  const [actions, setActions] = useState(
    workflow ? workflow.actions.map((a) => ({ tipo_acao: a.tipo_acao, parametros: { ...a.parametros } }))
             : [{ tipo_acao: 'criar_tarefa', parametros: defaultParams('criar_tarefa') }]
  )
  const [touched, setTouched] = useState(false)

  const templatesQuery = useQuery({ queryKey: ['email-templates', 'list'], queryFn: () => listEmailTemplates({ size: 100 }) })
  const templates = templatesQuery.data?.items ?? []
  const pipelinesQuery = useQuery({ queryKey: ['pipelines', 'for-workflow'], queryFn: () => listPipelines({ size: 50 }) })
  const pipelines = pipelinesQuery.data?.items ?? []
  const stageOptions = pipelines.flatMap((p) => p.stages.map((s) => ({ id: s.id, label: `${p.nome} / ${s.nome}` })))
  const sequencesQuery = useQuery({ queryKey: ['sequences', 'for-workflow'], queryFn: () => listSequences({ size: 100 }) })
  const sequences = sequencesQuery.data?.items ?? []

  const logsQuery = useQuery({
    queryKey: ['workflows', workflow?.id, 'logs'],
    queryFn: () => listWorkflowLogs(workflow.id),
    enabled: Boolean(workflow),
  })
  const logs = logsQuery.data ?? []

  const campos = GATILHO_CAMPOS[gatilho] ?? []
  const okNome = nome.trim().length > 0
  const okActions = actions.length > 0

  function handleGatilhoChange(next) {
    setGatilho(next)
    setCondicoes([])
  }

  function addCondicao() {
    setCondicoes((prev) => [...prev, { campo: campos[0] ?? '', operador: 'igual a', valor: '' }])
  }
  function updateCondicao(idx, patch) {
    setCondicoes((prev) => prev.map((c, i) => (i === idx ? { ...c, ...patch } : c)))
  }
  function removeCondicao(idx) {
    setCondicoes((prev) => prev.filter((_, i) => i !== idx))
  }

  function addAction() {
    setActions((prev) => [...prev, { tipo_acao: 'criar_tarefa', parametros: defaultParams('criar_tarefa') }])
  }
  function updateActionTipo(idx, novoTipo) {
    setActions((prev) => prev.map((a, i) => (i === idx ? { tipo_acao: novoTipo, parametros: defaultParams(novoTipo) } : a)))
  }
  function updateActionParam(idx, campo, valor) {
    setActions((prev) => prev.map((a, i) => (i === idx ? { ...a, parametros: { ...a.parametros, [campo]: valor } } : a)))
  }
  function removeAction(idx) {
    setActions((prev) => prev.filter((_, i) => i !== idx))
  }

  function handleSubmit(e) {
    e.preventDefault()
    setTouched(true)
    if (!okNome || !okActions) return
    onSubmit({ nome: nome.trim(), ativo, gatilho, condicoes, actions })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>{workflow ? 'Editar workflow' : 'Novo workflow'}</h2>
            <p>Defina o gatilho, as condições e a cadeia de ações</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-group">
              <label className="f-label">Nome <span className="req">*</span></label>
              <input
                className={`f-input${touched && !okNome ? ' err' : ''}`}
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Ex.: Boas-vindas a novo lead"
              />
              <span className={`f-err${touched && !okNome ? ' show' : ''}`}>Informe o nome do workflow.</span>
            </div>

            <div className="toggle-row">
              <div><div className="t">Ativo</div><div className="sub">Workflows inativos não disparam ações</div></div>
              <label className="switch"><input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} /><span className="track" /><span className="knob" /></label>
            </div>

            <div className="f-group">
              <label className="f-label">Gatilho <span className="req">*</span></label>
              <select className="f-select" value={gatilho} onChange={(e) => handleGatilhoChange(e.target.value)}>
                {Object.entries(GATILHO_LABEL).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </select>
              <span className="f-hint">{GATILHO_HINT[gatilho]}</span>
            </div>

            <div className="flow-diagram">
              <span className="flow-node trigger">{GATILHO_LABEL[gatilho]}</span>
              {condicoes.length > 0 && (
                <>
                  <span className="flow-arrow">→</span>
                  <span className="flow-node cond">{condicoes.length} condição(ões)</span>
                </>
              )}
              {actions.map((a, i) => (
                <Fragment key={i}>
                  <span className="flow-arrow">→</span>
                  <span className="flow-node action">{TIPO_ACAO_LABEL[a.tipo_acao]}</span>
                </Fragment>
              ))}
            </div>

            <div className="section-title"><span>Condições <span className="hint-inline">(opcional — todas precisam ser verdadeiras)</span></span></div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {condicoes.map((c, idx) => (
                <div className="cond-row" key={idx}>
                  <select className="cf-campo" value={c.campo} onChange={(e) => updateCondicao(idx, { campo: e.target.value })}>
                    {campos.map((f) => <option key={f} value={f}>{f}</option>)}
                  </select>
                  <select className="cf-op" value={c.operador} onChange={(e) => updateCondicao(idx, { operador: e.target.value })}>
                    {OPERADORES.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                  <input className="cf-valor" value={c.valor} onChange={(e) => updateCondicao(idx, { valor: e.target.value })} placeholder="valor" />
                  <button type="button" className="icon-btn danger" title="Remover" onClick={() => removeCondicao(idx)}>✕</button>
                </div>
              ))}
            </div>
            <button type="button" className="add-row-btn" onClick={addCondicao}>+ Adicionar condição</button>

            <div className="section-title"><span>Ações (em ordem)</span></div>
            <div className="action-list">
              {actions.map((a, idx) => (
                <div className="action-row" key={idx}>
                  <div className="action-row-top">
                    <span className="action-num">#{idx + 1}</span>
                    <div className="action-tipo">
                      <select value={a.tipo_acao} onChange={(e) => updateActionTipo(idx, e.target.value)}>
                        {Object.entries(TIPO_ACAO_LABEL).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
                      </select>
                    </div>
                    <button type="button" className="icon-btn danger" title="Remover ação" onClick={() => removeAction(idx)}>✕</button>
                  </div>
                  <ActionParams tipo={a.tipo_acao} parametros={a.parametros} templates={templates} stageOptions={stageOptions}
                                sequences={sequences} onChange={(campo, valor) => updateActionParam(idx, campo, valor)} />
                </div>
              ))}
            </div>
            <button type="button" className="add-action-btn" onClick={addAction}>+ Adicionar ação</button>
            <span className={`f-err${touched && !okActions ? ' show' : ''}`}>O workflow precisa de pelo menos uma ação.</span>

            {workflow && (
              <>
                <div className="section-title">
                  <span>Log de execuções</span>
                  <span className="mono">{logs.length} registro{logs.length === 1 ? '' : 's'}</span>
                </div>
                <div>
                  {logsQuery.isLoading && <p className="state-msg">Carregando…</p>}
                  {logs.length === 0 && !logsQuery.isLoading && <div className="enroll-empty">Nenhuma execução ainda.</div>}
                  {logs.map((l) => (
                    <div className="log-row" key={l.id}>
                      <span className={`log-icon ${l.resultado}`}>{RESULTADO_LABEL[l.resultado] ?? '?'}</span>
                      <div className="log-body">
                        <div className="lb-title">{l.resultado === 'sucesso' ? 'Executado com sucesso' : 'Falha na execução'}</div>
                        <div className="lb-detail">
                          {(l.detalhes?.acoes ?? []).map((a) => a.detalhe).join(' · ') || l.detalhes?.motivo || '—'}
                        </div>
                        <div className="lb-time">{new Date(l.executado_em).toLocaleString('pt-BR')}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}

            {error && (
              <p className="state-msg error">
                {error.response?.data?.error?.message ?? 'Não foi possível salvar. Confira os dados e tente de novo.'}
              </p>
            )}
          </div>
          <div className="drawer-foot">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar workflow'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ActionParams({ tipo, parametros, templates, stageOptions, sequences, onChange }) {
  if (tipo === 'criar_tarefa') {
    return (
      <div className="action-params">
        <input value={parametros.titulo ?? ''} onChange={(e) => onChange('titulo', e.target.value)} placeholder="Título da tarefa" />
        <div className="f-row-mini">
          <select value={parametros.tipo_tarefa ?? 'followup'} onChange={(e) => onChange('tipo_tarefa', e.target.value)}>
            {Object.entries(TIPO_TAREFA_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <input type="number" min="0" value={parametros.dias_apos ?? 0} onChange={(e) => onChange('dias_apos', Number(e.target.value) || 0)} placeholder="dias após" />
          <select value={parametros.destinatario ?? DESTINATARIOS[0]} onChange={(e) => onChange('destinatario', e.target.value)}>
            {DESTINATARIOS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
      </div>
    )
  }
  if (tipo === 'enviar_email') {
    return (
      <div className="action-params">
        <div className="f-row-mini">
          <select value={parametros.template_id ?? ''} onChange={(e) => onChange('template_id', e.target.value)}>
            <option value="" disabled>Selecione um modelo</option>
            {templates.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
          </select>
          <input type="number" min="0" value={parametros.dias_apos ?? 0} onChange={(e) => onChange('dias_apos', Number(e.target.value) || 0)} placeholder="dias após" />
        </div>
        <span className="f-hint">Enviado na hora, se houver contato com e-mail e integração conectada. "Dias após" só vale se cair para tarefa manual.</span>
      </div>
    )
  }
  if (tipo === 'inscrever_em_sequencia') {
    return (
      <div className="action-params">
        <select value={parametros.sequence_id ?? ''} onChange={(e) => onChange('sequence_id', e.target.value)}>
          <option value="" disabled>Selecione uma sequência</option>
          {sequences.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
        </select>
        <span className="f-hint">As etapas e o tempo de cada passo seguem o que estiver configurado na Sequência escolhida.</span>
      </div>
    )
  }
  if (tipo === 'alterar_pipeline') {
    return (
      <div className="action-params">
        <select value={parametros.stage_id ?? ''} onChange={(e) => onChange('stage_id', e.target.value)}>
          <option value="" disabled>Selecione a etapa</option>
          {stageOptions.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
      </div>
    )
  }
  if (tipo === 'notificar_usuario') {
    return (
      <div className="action-params">
        <select value={parametros.destinatario ?? DESTINATARIOS[0]} onChange={(e) => onChange('destinatario', e.target.value)}>
          {DESTINATARIOS.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <input value={parametros.mensagem ?? ''} onChange={(e) => onChange('mensagem', e.target.value)} placeholder="Mensagem da notificação" />
      </div>
    )
  }
  if (tipo === 'executar_enriquecimento') {
    return (
      <span className="f-hint">Atualiza o Resumo Executivo e a Próxima ação sugerida da empresa via IA (mesmo motor do Dossiê Comercial). Sem parâmetros — precisa da ANTHROPIC_API_KEY configurada no servidor.</span>
    )
  }
  return null
}
