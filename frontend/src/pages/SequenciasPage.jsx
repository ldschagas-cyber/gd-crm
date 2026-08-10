import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  cloneSequence, createSequence, deleteSequence, listSequenceEnrollments, listSequences, updateSequence,
} from '../api/sequences'
import { listEmailTemplates } from '../api/emailTemplates'
import { listMessageTemplates } from '../api/messageTemplates'
import { TIPO_LABEL, TaskTypeIcon } from '../components/TaskTypeIcon'
import '../styles/dataTable.css'
import './SequenciasPage.css'

const ENROLL_STATUS_LABEL = { ativa: 'ativa', pausada: 'pausada', concluida: 'concluída', cancelada: 'cancelada' }
const CANAIS_MESSAGE_TEMPLATE = ['whatsapp', 'linkedin_conexao', 'linkedin_mensagem']

function emptyStep(lastDia) {
  return { dia_offset: lastDia + 3, tipo: 'ligacao', template_id: null, message_template_id: null, instrucoes: '' }
}

function usaTemplate(tipo) {
  return tipo === 'email'
}

// tipo do step === canal do MessageTemplate (whatsapp/linkedin_conexao/linkedin_mensagem)
function usaMessageTemplate(tipo) {
  return CANAIS_MESSAGE_TEMPLATE.includes(tipo)
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

export default function SequenciasPage() {
  const queryClient = useQueryClient()
  const [drawerSequence, setDrawerSequence] = useState(undefined) // undefined = fechado, null = nova, obj = editar
  const [helpOpen, setHelpOpen] = useState(false)

  const listQuery = useQuery({ queryKey: ['sequences', 'list'], queryFn: () => listSequences({ size: 100 }) })
  const items = listQuery.data?.items ?? []

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['sequences'] })
  }

  const createMutation = useMutation({ mutationFn: createSequence, onSuccess: () => { setDrawerSequence(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateSequence(id, data), onSuccess: () => { setDrawerSequence(undefined); invalidate() } })
  const deleteMutation = useMutation({ mutationFn: deleteSequence, onSuccess: invalidate })
  const cloneMutation = useMutation({ mutationFn: cloneSequence, onSuccess: invalidate })

  const totalAtivas = items.filter((s) => s.ativo).length
  const totalInscritos = items.reduce((acc, s) => acc + s.inscritos_ativos, 0)

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Sequências</h1>
          <p>{items.length.toLocaleString('pt-BR')} sequência(s) · {totalAtivas} ativa(s) · {totalInscritos} inscrição(ões) em andamento</p>
        </div>
        <button className="btn-primary" onClick={() => setDrawerSequence(null)}>+ Nova sequência</button>
      </header>

      <div className="content">
        <button className="info-trigger" onClick={() => setHelpOpen(true)}>
          <IconInfo /> Como funciona a pausa automática
        </button>

        <div className="card">
          {listQuery.isLoading && <p className="state-msg">Carregando sequências…</p>}
          {listQuery.isError && <p className="state-msg error">Não foi possível carregar as sequências agora.</p>}

          {listQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>Sequência</th>
                    <th>Status</th>
                    <th>Pausa por resposta</th>
                    <th>Etapas</th>
                    <th>Inscritos ativos</th>
                    <th className="actions-col"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((s) => {
                    const ultimoDia = s.steps.length ? s.steps[s.steps.length - 1].dia_offset : 0
                    return (
                      <tr key={s.id}>
                        <td>
                          <div className="row-title" onClick={() => setDrawerSequence(s)}>{s.nome}</div>
                          <div className="row-sub">{s.steps.length} etapa{s.steps.length === 1 ? '' : 's'} · até dia {ultimoDia}</div>
                        </td>
                        <td><span className={`status-pill ${s.ativo ? 'ativo' : 'inativo'}`}><span className="d" />{s.ativo ? 'Ativa' : 'Inativa'}</span></td>
                        <td><span className={`pause-badge ${s.pausar_em_resposta ? 'on' : 'off'}`}>{s.pausar_em_resposta ? 'Sim' : 'Não'}</span></td>
                        <td className="mono">{s.steps.length}</td>
                        <td className="mono">{s.inscritos_ativos}</td>
                        <td className="actions-col">
                          <button className="icon-btn" title="Clonar" onClick={() => cloneMutation.mutate(s.id)}>⧉</button>
                          <button className="icon-btn" title="Editar" onClick={() => setDrawerSequence(s)}>✎</button>
                          <button
                            className="icon-btn danger"
                            title="Excluir"
                            onClick={() => { if (confirm(`Excluir "${s.nome}"? As inscrições ativas serão canceladas.`)) deleteMutation.mutate(s.id) }}
                          >
                            ✕
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                  {items.length === 0 && <tr><td colSpan={6} className="empty-cell">Nenhuma sequência cadastrada.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {drawerSequence !== undefined && (
        <SequenceDrawer
          sequence={drawerSequence}
          onClose={() => setDrawerSequence(undefined)}
          onSubmit={(data) => {
            if (drawerSequence) updateMutation.mutate({ id: drawerSequence.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {helpOpen && (
        <div className="scrim show" onClick={() => setHelpOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3><IconInfo />Como funciona a pausa automática</h3>
            <p className="sub">
              Uma sequência dispara tarefas automaticamente conforme dias decorridos (ligação, e-mail, WhatsApp,
              LinkedIn, follow-up) para quem está inscrito. <b>Pausar quando houver resposta</b> depende da integração de
              e-mail em Preferências (Microsoft 365/Graph) — sem isso conectado, a sequência não sabe se alguém
              respondeu, então essa opção hoje não pausa automaticamente nada.
            </p>
            <div className="row"><button className="btn-ghost" onClick={() => setHelpOpen(false)}>Fechar</button></div>
          </div>
        </div>
      )}
    </>
  )
}

function SequenceDrawer({ sequence, onClose, onSubmit, submitting, error }) {
  const [nome, setNome] = useState(sequence?.nome ?? '')
  const [ativo, setAtivo] = useState(sequence?.ativo ?? true)
  const [pausarResposta, setPausarResposta] = useState(sequence?.pausar_em_resposta ?? true)
  const [steps, setSteps] = useState(
    sequence
      ? sequence.steps.map((s) => ({
          dia_offset: s.dia_offset, tipo: s.tipo, template_id: s.template_id,
          message_template_id: s.message_template_id, instrucoes: s.instrucoes ?? '',
        }))
      : [emptyStep(-3)]
  )
  const [touched, setTouched] = useState(false)
  const [draggingIdx, setDraggingIdx] = useState(null)

  const templatesQuery = useQuery({ queryKey: ['email-templates', 'list'], queryFn: () => listEmailTemplates({ size: 100 }) })
  const templates = templatesQuery.data?.items ?? []

  const messageTemplatesQuery = useQuery({ queryKey: ['message-templates', 'list'], queryFn: () => listMessageTemplates({ size: 100 }) })
  const messageTemplates = messageTemplatesQuery.data?.items ?? []

  const enrollmentsQuery = useQuery({
    queryKey: ['sequences', sequence?.id, 'enrollments'],
    queryFn: () => listSequenceEnrollments(sequence.id),
    enabled: Boolean(sequence),
  })
  const enrollments = enrollmentsQuery.data ?? []

  const okNome = nome.trim().length > 0
  const okSteps = steps.length > 0

  function updateStep(idx, patch) {
    setSteps((prev) => prev.map((s, i) => (i === idx ? { ...s, ...patch } : s)))
  }
  function removeStep(idx) {
    setSteps((prev) => prev.filter((_, i) => i !== idx))
  }
  function addStep() {
    const lastDia = steps.length ? steps[steps.length - 1].dia_offset : -3
    setSteps((prev) => [...prev, emptyStep(lastDia)])
  }
  function moveStep(fromIdx, toIdx) {
    setSteps((prev) => {
      const next = [...prev]
      const [moved] = next.splice(fromIdx, 1)
      next.splice(toIdx, 0, moved)
      return next
    })
  }

  function handleSubmit(e) {
    e.preventDefault()
    setTouched(true)
    if (!okNome || !okSteps) return
    onSubmit({
      nome: nome.trim(), ativo, pausar_em_resposta: pausarResposta,
      steps: steps.map((s) => ({
        dia_offset: Number(s.dia_offset) || 0, tipo: s.tipo,
        template_id: usaTemplate(s.tipo) ? (s.template_id || null) : null,
        message_template_id: usaMessageTemplate(s.tipo) ? (s.message_template_id || null) : null,
        instrucoes: (usaTemplate(s.tipo) || usaMessageTemplate(s.tipo)) ? null : (s.instrucoes?.trim() || null),
      })),
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>{sequence ? 'Editar sequência' : 'Nova sequência'}</h2>
            <p>Configure as etapas e acompanhe quem está inscrito</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-group">
              <label className="f-label">Nome da sequência <span className="req">*</span></label>
              <input
                className={`f-input${touched && !okNome ? ' err' : ''}`}
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Ex.: Prospecção fria — Indústria"
              />
              <span className={`f-err${touched && !okNome ? ' show' : ''}`}>Informe o nome da sequência.</span>
            </div>

            <div className="toggle-row">
              <div><div className="t">Ativa</div><div className="sub">Sequências inativas não disparam novas tarefas nem aceitam novas inscrições</div></div>
              <label className="switch"><input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} /><span className="track" /><span className="knob" /></label>
            </div>
            <div className="toggle-row">
              <div><div className="t">Pausar quando houver resposta</div><div className="sub">Requer e-mail conectado em Preferências (Microsoft 365) — hoje não pausa automaticamente</div></div>
              <label className="switch"><input type="checkbox" checked={pausarResposta} onChange={(e) => setPausarResposta(e.target.checked)} /><span className="track" /><span className="knob" /></label>
            </div>

            <div className="section-title"><span>Etapas</span></div>
            <div className="step-list">
              {steps.map((step, idx) => (
                <div
                  key={idx}
                  className={`step-row${draggingIdx === idx ? ' dragging' : ''}`}
                  draggable
                  onDragStart={() => setDraggingIdx(idx)}
                  onDragEnd={() => setDraggingIdx(null)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => { e.preventDefault(); if (draggingIdx !== null && draggingIdx !== idx) moveStep(draggingIdx, idx) }}
                >
                  <div className="step-row-top">
                    <span className="step-drag">⠿</span>
                    <div className="step-day">
                      <span className="suffix">dia</span>
                      <input type="number" min="0" value={step.dia_offset} onChange={(e) => updateStep(idx, { dia_offset: e.target.value })} />
                    </div>
                    <div className="step-tipo">
                      <TaskTypeIcon tipo={step.tipo} />
                      <select
                        value={step.tipo}
                        onChange={(e) => updateStep(idx, { tipo: e.target.value, template_id: null, message_template_id: null })}
                      >
                        {Object.entries(TIPO_LABEL).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
                      </select>
                    </div>
                    <button type="button" className="icon-btn danger step-del" title="Remover etapa" onClick={() => removeStep(idx)}>✕</button>
                  </div>
                  <div className="step-detail">
                    {usaTemplate(step.tipo) ? (
                      <select value={step.template_id ?? ''} onChange={(e) => updateStep(idx, { template_id: e.target.value || null })}>
                        <option value="">Sem modelo (rascunho manual)</option>
                        {templates.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
                      </select>
                    ) : usaMessageTemplate(step.tipo) ? (
                      <select
                        value={step.message_template_id ?? ''}
                        onChange={(e) => updateStep(idx, { message_template_id: e.target.value || null })}
                      >
                        <option value="">Sem modelo (roteiro manual)</option>
                        {messageTemplates.filter((t) => t.canal === step.tipo).map((t) => (
                          <option key={t.id} value={t.id}>{t.nome}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        value={step.instrucoes ?? ''}
                        onChange={(e) => updateStep(idx, { instrucoes: e.target.value })}
                        placeholder="Roteiro / instruções para quem for executar…"
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
            <button type="button" className="add-step-btn" onClick={addStep}>+ Adicionar etapa</button>
            <span className={`f-err${touched && !okSteps ? ' show' : ''}`}>A sequência precisa de pelo menos uma etapa.</span>

            {sequence && (
              <>
                <div className="section-title">
                  <span>Inscritos</span>
                  <span className="mono">{enrollments.length} inscrito{enrollments.length === 1 ? '' : 's'}</span>
                </div>
                <div>
                  {enrollmentsQuery.isLoading && <p className="state-msg">Carregando inscrições…</p>}
                  {enrollments.length === 0 && !enrollmentsQuery.isLoading && (
                    <div className="enroll-empty">Nenhuma inscrição ainda.</div>
                  )}
                  {enrollments.map((e) => (
                    <div className="enroll-row" key={e.id}>
                      <div className="enroll-body">
                        <div className="enroll-name">{e.alvo_nome}</div>
                        <div className="enroll-meta">
                          {e.alvo_tipo} · etapa {e.step_atual + 1} · desde {new Date(e.iniciado_em).toLocaleDateString('pt-BR')}
                          {e.pausado_motivo ? ` · motivo: ${e.pausado_motivo.replace('_', ' ')}` : ''}
                        </div>
                      </div>
                      <span className={`enroll-status ${e.status}`}>{ENROLL_STATUS_LABEL[e.status] ?? e.status}</span>
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
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar sequência'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
