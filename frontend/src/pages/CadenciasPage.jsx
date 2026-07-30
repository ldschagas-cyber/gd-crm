import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  cloneCadence, createCadence, deleteCadence, listCadenceEnrollments, listCadences, updateCadence,
} from '../api/cadences'
import { listEmailTemplates } from '../api/emailTemplates'
import '../styles/dataTable.css'
import './CadenciasPage.css'

const ENROLL_STATUS_LABEL = { ativa: 'ativa', pausada: 'pausada', concluida: 'concluída', cancelada: 'cancelada' }
const PREVIEW_SAMPLE = { nome: 'Ana Beatriz Souza', empresa: 'Distribuidora Rio Verde', cargo: 'Gerente de Compras', responsavel: 'Felipe Nogueira' }

function mergeVars(text) {
  return (text ?? '').replace(/\{\{(\w+)\}\}/g, (m, key) => PREVIEW_SAMPLE[key] ?? m)
}

function totalDias(steps) {
  return steps.reduce((sum, s) => sum + (Number(s.dias_espera) || 0), 0)
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

export default function CadenciasPage() {
  const queryClient = useQueryClient()
  const [drawerCadence, setDrawerCadence] = useState(undefined) // undefined = fechado, null = nova, obj = editar
  const [helpOpen, setHelpOpen] = useState(false)

  const listQuery = useQuery({ queryKey: ['cadences', 'list'], queryFn: () => listCadences({ size: 100 }) })
  const items = listQuery.data?.items ?? []

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['cadences'] })
  }

  const createMutation = useMutation({ mutationFn: createCadence, onSuccess: () => { setDrawerCadence(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateCadence(id, data), onSuccess: () => { setDrawerCadence(undefined); invalidate() } })
  const deleteMutation = useMutation({ mutationFn: deleteCadence, onSuccess: invalidate })
  const cloneMutation = useMutation({ mutationFn: cloneCadence, onSuccess: invalidate })

  const totalAtivas = items.filter((c) => c.ativo).length
  const totalInscritos = items.reduce((acc, c) => acc + c.inscritos_ativos, 0)

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Cadências</h1>
          <p>{items.length.toLocaleString('pt-BR')} cadência(s) · {totalAtivas} ativa(s) · {totalInscritos} inscrição(ões) em andamento</p>
        </div>
        <button className="btn-primary" onClick={() => setDrawerCadence(null)}>+ Nova cadência</button>
      </header>

      <div className="content">
        <button className="info-trigger" onClick={() => setHelpOpen(true)}>
          <IconInfo /> Como funcionam as cadências de e-mail
        </button>

        <div className="card">
          {listQuery.isLoading && <p className="state-msg">Carregando cadências…</p>}
          {listQuery.isError && <p className="state-msg error">Não foi possível carregar as cadências agora.</p>}

          {listQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>Cadência</th>
                    <th>Status</th>
                    <th>Pausa por resposta</th>
                    <th>E-mails</th>
                    <th>Duração</th>
                    <th>Inscritos ativos</th>
                    <th className="actions-col"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <div className="row-title" onClick={() => setDrawerCadence(c)}>{c.nome}</div>
                        <div className="row-sub">{c.criar_followup ? 'Cria tarefa de follow-up ao final' : 'Sem follow-up automático'}</div>
                      </td>
                      <td><span className={`status-pill ${c.ativo ? 'ativo' : 'inativo'}`}><span className="d" />{c.ativo ? 'Ativa' : 'Inativa'}</span></td>
                      <td><span className={`pause-badge ${c.pausar_em_resposta ? 'on' : 'off'}`}>{c.pausar_em_resposta ? 'Sim' : 'Não'}</span></td>
                      <td className="mono">{c.steps.length}</td>
                      <td className="mono">{totalDias(c.steps)} dias</td>
                      <td className="mono">{c.inscritos_ativos}</td>
                      <td className="actions-col">
                        <button className="icon-btn" title="Clonar" onClick={() => cloneMutation.mutate(c.id)}>⧉</button>
                        <button className="icon-btn" title="Editar" onClick={() => setDrawerCadence(c)}>✎</button>
                        <button
                          className="icon-btn danger"
                          title="Excluir"
                          onClick={() => { if (confirm(`Excluir "${c.nome}"? As inscrições ativas serão canceladas.`)) deleteMutation.mutate(c.id) }}
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && <tr><td colSpan={7} className="empty-cell">Nenhuma cadência cadastrada.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {drawerCadence !== undefined && (
        <CadenceDrawer
          cadence={drawerCadence}
          onClose={() => setDrawerCadence(undefined)}
          onSubmit={(data) => {
            if (drawerCadence) updateMutation.mutate({ id: drawerCadence.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {helpOpen && (
        <div className="scrim show" onClick={() => setHelpOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3><IconInfo />Como funcionam as cadências de e-mail</h3>
            <p className="sub">
              Cadência é uma sequência restrita a <b>e-mail</b>: cada etapa espera N dias após a anterior e envia
              um modelo, com <code>{'{{nome}}'}</code> <code>{'{{empresa}}'}</code> <code>{'{{cargo}}'}</code>{' '}
              <code>{'{{responsavel}}'}</code> substituídos no momento do envio. Sem uma camada de envio de e-mail
              configurada ainda (SMTP/Microsoft 365), cada etapa vencida hoje gera uma <b>tarefa de e-mail</b> para
              o responsável enviar manualmente pelo modelo indicado — não é um disparo automático de verdade.
            </p>
            <div className="row"><button className="btn-ghost" onClick={() => setHelpOpen(false)}>Fechar</button></div>
          </div>
        </div>
      )}
    </>
  )
}

function CadenceDrawer({ cadence, onClose, onSubmit, submitting, error }) {
  const [nome, setNome] = useState(cadence?.nome ?? '')
  const [ativo, setAtivo] = useState(cadence?.ativo ?? true)
  const [pausarResposta, setPausarResposta] = useState(cadence?.pausar_em_resposta ?? true)
  const [criarFollowup, setCriarFollowup] = useState(cadence?.criar_followup ?? true)
  const [followupTitulo, setFollowupTitulo] = useState(cadence?.followup_titulo ?? '')
  const [previewIdx, setPreviewIdx] = useState(null)
  const [draggingIdx, setDraggingIdx] = useState(null)

  const templatesQuery = useQuery({ queryKey: ['email-templates', 'list'], queryFn: () => listEmailTemplates({ size: 100 }) })
  const templates = templatesQuery.data?.items ?? []

  const [steps, setSteps] = useState(
    cadence
      ? cadence.steps.map((s) => ({ dias_espera: s.dias_espera, template_id: s.template_id }))
      : []
  )

  const enrollmentsQuery = useQuery({
    queryKey: ['cadences', cadence?.id, 'enrollments'],
    queryFn: () => listCadenceEnrollments(cadence.id),
    enabled: Boolean(cadence),
  })
  const enrollments = enrollmentsQuery.data ?? []

  const [touched, setTouched] = useState(false)
  const okNome = nome.trim().length > 0
  const okSteps = steps.length > 0 && steps.every((s) => s.template_id)

  function updateStep(idx, patch) {
    setSteps((prev) => prev.map((s, i) => (i === idx ? { ...s, ...patch } : s)))
  }
  function removeStep(idx) {
    setSteps((prev) => prev.filter((_, i) => i !== idx))
  }
  function addStep() {
    const lastDia = steps.length ? steps[steps.length - 1].dias_espera : -4
    setSteps((prev) => [...prev, { dias_espera: Number(lastDia) + 4, template_id: templates[0]?.id ?? null }])
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
      criar_followup: criarFollowup, followup_titulo: criarFollowup ? (followupTitulo.trim() || null) : null,
      steps: steps.map((s) => ({ dias_espera: Number(s.dias_espera) || 0, template_id: s.template_id })),
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>{cadence ? 'Editar cadência' : 'Nova cadência'}</h2>
            <p>Configure os e-mails e acompanhe quem está inscrito</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-group">
              <label className="f-label">Nome da cadência <span className="req">*</span></label>
              <input
                className={`f-input${touched && !okNome ? ' err' : ''}`}
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Ex.: Cadência de reativação — leads frios"
              />
              <span className={`f-err${touched && !okNome ? ' show' : ''}`}>Informe o nome da cadência.</span>
            </div>

            <div className="toggle-row">
              <div><div className="t">Ativa</div><div className="sub">Cadências inativas não disparam novos envios nem aceitam novas inscrições</div></div>
              <label className="switch"><input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} /><span className="track" /><span className="knob" /></label>
            </div>
            <div className="toggle-row">
              <div><div className="t">Pausar quando houver resposta</div><div className="sub">Requer e-mail conectado em Preferências (Microsoft 365) — hoje não pausa automaticamente</div></div>
              <label className="switch"><input type="checkbox" checked={pausarResposta} onChange={(e) => setPausarResposta(e.target.checked)} /><span className="track" /><span className="knob" /></label>
            </div>

            <div className="section-title"><span>E-mails</span></div>
            {templates.length === 0 && !templatesQuery.isLoading && (
              <p className="state-msg">Cadastre um modelo em <b>Modelos de e-mail</b> antes de montar a cadência.</p>
            )}
            <div className="step-list">
              {steps.map((step, idx) => {
                const tpl = templates.find((t) => t.id === step.template_id)
                return (
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
                      <span className="step-num">#{idx + 1}</span>
                      <div className="step-wait">
                        <span className="suffix">espera</span>
                        <input type="number" min="0" value={step.dias_espera} onChange={(e) => updateStep(idx, { dias_espera: e.target.value })} />
                        <span className="suffix">dias</span>
                      </div>
                      <div className="step-tpl">
                        <select value={step.template_id ?? ''} onChange={(e) => updateStep(idx, { template_id: e.target.value })}>
                          <option value="" disabled>Selecione um modelo</option>
                          {templates.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
                        </select>
                      </div>
                      <button type="button" className="step-preview-btn" onClick={() => setPreviewIdx(previewIdx === idx ? null : idx)}>Prévia</button>
                      <button type="button" className="icon-btn danger step-del" title="Remover e-mail" onClick={() => removeStep(idx)}>✕</button>
                    </div>
                    {previewIdx === idx && tpl && (
                      <div className="step-preview show">
                        <div className="pv-subject">{mergeVars(tpl.assunto)}</div>
                        <div className="pv-body">{mergeVars(tpl.corpo)}</div>
                        <div className="pv-note">Prévia com dados de exemplo — as variáveis reais são resolvidas no momento do envio.</div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
            <button type="button" className="add-step-btn" onClick={addStep} disabled={templates.length === 0}>+ Adicionar e-mail</button>
            <span className={`f-err${touched && !okSteps ? ' show' : ''}`}>A cadência precisa de pelo menos um e-mail com modelo selecionado.</span>

            <div className="section-title"><span>Ao final da cadência</span></div>
            <div className="followup-box">
              <div className="toggle-row">
                <div><div className="t">Criar tarefa de follow-up</div><div className="sub">Se ninguém responder até o último e-mail, cria uma tarefa pro responsável</div></div>
                <label className="switch"><input type="checkbox" checked={criarFollowup} onChange={(e) => setCriarFollowup(e.target.checked)} /><span className="track" /><span className="knob" /></label>
              </div>
              {criarFollowup && (
                <div className="f-group">
                  <label className="f-label">Título da tarefa</label>
                  <input
                    className="f-input"
                    value={followupTitulo}
                    onChange={(e) => setFollowupTitulo(e.target.value)}
                    placeholder="Ex.: Ligar — sem resposta na cadência"
                  />
                </div>
              )}
            </div>

            {cadence && (
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
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar cadência'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
