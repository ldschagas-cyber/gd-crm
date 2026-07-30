import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  addStage, createPipeline, deleteStage, getBoard,
  listPipelines, updatePipeline, updateStage,
} from '../api/pipelines'
import { stageTint } from '../utils/stageColor'
import StageLabel from '../components/StageLabel.jsx'
import '../styles/dataTable.css'
import './PipelinesPage.css'

const TYPE_LABEL = { aberta: 'Aberta', ganho: 'Ganho', perdido: 'Perdido' }
const COLOR_MODES = [
  { key: 'sem_cor', label: 'Texto (sem cor)' },
  { key: 'ponto', label: 'Texto com ponto colorido' },
  { key: 'selo', label: 'Texto com selo colorido' },
]

function isTerminal(stage) {
  return stage.tipo === 'ganho' || stage.tipo === 'perdido'
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

export default function PipelinesPage() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState(null)
  const [showNewStage, setShowNewStage] = useState(false)
  const [showNewPipeline, setShowNewPipeline] = useState(false)
  const [blockedMsg, setBlockedMsg] = useState(null)
  const [confirmDeleteStage, setConfirmDeleteStage] = useState(null)
  const [helpOpen, setHelpOpen] = useState(false)

  const pipelinesQuery = useQuery({ queryKey: ['pipelines'], queryFn: () => listPipelines({ size: 100 }) })
  const pipelines = pipelinesQuery.data?.items ?? []
  const pipelineId = selectedId
  const pipeline = pipelines.find((p) => p.id === pipelineId)

  const boardQuery = useQuery({
    queryKey: ['pipelines', 'board', pipelineId],
    queryFn: () => getBoard(pipelineId),
    enabled: Boolean(pipelineId),
  })
  const openCountByStage = Object.fromEntries(
    (boardQuery.data?.columns ?? []).map((c) => [c.stage.id, c.deals.filter((d) => d.status === 'aberto').length]),
  )

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['pipelines'] })
  }

  const createPipelineMutation = useMutation({
    mutationFn: createPipeline,
    onSuccess: (created) => { setShowNewPipeline(false); setSelectedId(created.id); invalidate() },
  })
  const updatePipelineMutation = useMutation({ mutationFn: ({ id, data }) => updatePipeline(id, data), onSuccess: invalidate })
  const addStageMutation = useMutation({
    mutationFn: ({ pipelineId, data }) => addStage(pipelineId, data),
    onSuccess: () => { setShowNewStage(false); invalidate() },
  })
  const updateStageMutation = useMutation({ mutationFn: ({ pipelineId, stageId, data }) => updateStage(pipelineId, stageId, data), onSuccess: invalidate })
  const deleteStageMutation = useMutation({
    mutationFn: ({ pipelineId, stageId }) => deleteStage(pipelineId, stageId),
    onSuccess: () => { setConfirmDeleteStage(null); invalidate() },
    onError: (err) => {
      setConfirmDeleteStage(null)
      setBlockedMsg(err.response?.data?.error?.message ?? 'Não foi possível excluir a etapa.')
    },
  })

  if (pipelinesQuery.isLoading) return <div className="content"><p className="state-msg">Carregando…</p></div>

  if (pipelines.length === 0) {
    return (
      <>
        <header className="topbar">
          <div className="topbar-title"><h1>Pipeline</h1></div>
        </header>
        <div className="content">
          <div className="card empty-pipeline">
            <p>Nenhum pipeline configurado ainda. Crie o pipeline padrão para começar a usar Negócios.</p>
            <button
              className="btn-primary"
              disabled={createPipelineMutation.isPending}
              onClick={() => createPipelineMutation.mutate({
                nome: 'Vendas', is_default: true,
                stages: [
                  { nome: 'Novo lead', ordem: 0, tipo: 'aberta', probabilidade: 10 },
                  { nome: 'Contato feito', ordem: 1, tipo: 'aberta', probabilidade: 30 },
                  { nome: 'Proposta', ordem: 2, tipo: 'aberta', probabilidade: 60 },
                  { nome: 'Negociação', ordem: 3, tipo: 'aberta', probabilidade: 80 },
                  { nome: 'Fechado — Ganho', ordem: 98, tipo: 'ganho', probabilidade: 100 },
                  { nome: 'Fechado — Perdido', ordem: 99, tipo: 'perdido', probabilidade: 0 },
                ],
              })}
            >
              {createPipelineMutation.isPending ? 'Criando…' : 'Criar pipeline padrão'}
            </button>
          </div>
        </div>
      </>
    )
  }

  const openStages = [...(pipeline?.stages ?? [])].filter((s) => !isTerminal(s)).sort((a, b) => a.ordem - b.ordem)
  const terminalStages = [...(pipeline?.stages ?? [])].filter(isTerminal).sort((a, b) => a.tipo === 'ganho' ? -1 : 1)

  function commitStage(stage, patch) {
    updateStageMutation.mutate({
      pipelineId,
      stageId: stage.id,
      data: {
        nome: patch.nome ?? stage.nome,
        ordem: patch.ordem ?? stage.ordem,
        tipo: stage.tipo,
        sla_horas: patch.sla_horas !== undefined ? patch.sla_horas : stage.sla_horas,
        probabilidade: patch.probabilidade !== undefined ? patch.probabilidade : stage.probabilidade,
      },
    })
  }

  function handleReorder(fromId, toId) {
    const ids = openStages.map((s) => s.id)
    const fromIdx = ids.indexOf(fromId)
    const toIdx = ids.indexOf(toId)
    if (fromIdx === -1 || toIdx === -1 || fromIdx === toIdx) return
    const reordered = [...ids]
    const [moved] = reordered.splice(fromIdx, 1)
    reordered.splice(toIdx, 0, moved)
    reordered.forEach((id, i) => {
      const stage = openStages.find((s) => s.id === id)
      if (stage && stage.ordem !== i) commitStage(stage, { ordem: i })
    })
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Pipeline</h1>
          <p>Configure as etapas do funil de vendas usadas no board de Negócios</p>
        </div>
        <div className="page-actions">
          <button className="btn-primary" onClick={() => setShowNewPipeline(true)}>+ Novo pipeline</button>
        </div>
      </header>

      <div className="content">
        <div className="card pipeline-select-card">
          <div className="table-scroll">
            <table className="data">
              <thead>
                <tr>
                  <th>Pipeline</th>
                  <th>Etapas</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {pipelines.map((p) => (
                  <tr
                    key={p.id}
                    className={p.id === pipelineId ? 'row-selected' : ''}
                    onClick={() => setSelectedId(p.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <div className="row-title">{p.nome}</div>
                      {p.is_default && <div className="row-sub">Padrão</div>}
                    </td>
                    <td>{p.stages.length} etapa(s)</td>
                    <td>
                      <span className="status-pill" data-status={p.ativo ? 'ativo' : 'inativo'}>
                        <span className="d" />{p.ativo ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                      {p.id === pipelineId && <span className="selected-check">✓ Selecionado</span>}
                    </td>
                  </tr>
                ))}
                {pipelines.length === 0 && (
                  <tr><td colSpan={4} className="empty-cell">Nenhum pipeline cadastrado ainda.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {pipeline ? (
          <>
            <button className="info-trigger" onClick={() => setHelpOpen(true)}>
              <IconInfo /> Como funciona o SLA por etapa
            </button>

            <div className="card color-mode-card">
              <h3 className="section-title">Defina as cores de exibição do pipeline</h3>
              <div className="color-mode-options">
                {COLOR_MODES.map((mode) => (
                  <button
                    key={mode.key}
                    className={`color-mode-option${pipeline.cor_exibicao === mode.key ? ' active' : ''}`}
                    onClick={() => updatePipelineMutation.mutate({ id: pipelineId, data: { cor_exibicao: mode.key } })}
                  >
                    <StageLabel mode={mode.key} tint={stageTint(0)} nome={mode.label} />
                  </button>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="pipeline-head">
                <div className="pipeline-name-wrap">
                  <input
                    className="pipeline-name"
                    defaultValue={pipeline.nome}
                    key={pipeline.id}
                    onBlur={(e) => {
                      if (e.target.value.trim() && e.target.value !== pipeline.nome) {
                        updatePipelineMutation.mutate({ id: pipelineId, data: { nome: e.target.value.trim() } })
                      }
                    }}
                  />
                  {pipeline.is_default && <span className="badge-default">Padrão</span>}
                </div>
                <label className="pipeline-toggle-wrap">
                  <input
                    type="checkbox"
                    checked={pipeline.ativo}
                    onChange={(e) => updatePipelineMutation.mutate({ id: pipelineId, data: { ativo: e.target.checked } })}
                  />
                  Ativo
                </label>
                <div className="pipeline-head-actions">
                  <button className="btn-primary" onClick={() => setShowNewStage(true)}>+ Nova etapa</button>
                </div>
              </div>

              <div className="stage-list-cols">
                <span></span><span>Etapa</span><span>Tipo</span><span>SLA</span><span>Probabilidade</span><span>Abertos</span>
                <span>Regras de lógica condicional</span><span></span>
              </div>

              <div className="stage-list">
                {openStages.map((stage, i) => (
                  <StageRow
                    key={stage.id}
                    stage={stage}
                    openCount={openCountByStage[stage.id] ?? 0}
                    colorMode={pipeline.cor_exibicao}
                    tint={stageTint(i)}
                    draggable
                    onReorderDrop={handleReorder}
                    onCommit={(patch) => commitStage(stage, patch)}
                    onDelete={() => setConfirmDeleteStage(stage)}
                  />
                ))}
                <div className="terminal-divider">Etapas terminais</div>
                {terminalStages.map((stage) => (
                  <StageRow key={stage.id} stage={stage} openCount={openCountByStage[stage.id] ?? 0} terminal />
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="card empty-pipeline">
            <p>Selecione um pipeline na tabela acima para configurar as etapas.</p>
          </div>
        )}
      </div>

      {showNewStage && (
        <NewStageDrawer
          pipelineName={pipeline.nome}
          onClose={() => setShowNewStage(false)}
          submitting={addStageMutation.isPending}
          onSubmit={(data) => addStageMutation.mutate({
            pipelineId,
            data: { ...data, ordem: openStages.length, tipo: 'aberta' },
          })}
        />
      )}

      {showNewPipeline && (
        <NewPipelineModal
          onClose={() => setShowNewPipeline(false)}
          submitting={createPipelineMutation.isPending}
          onSubmit={(nome) => createPipelineMutation.mutate({
            nome, is_default: false,
            stages: [
              { nome: 'Novo lead', ordem: 0, tipo: 'aberta', probabilidade: 10 },
              { nome: 'Fechado — Ganho', ordem: 98, tipo: 'ganho', probabilidade: 100 },
              { nome: 'Fechado — Perdido', ordem: 99, tipo: 'perdido', probabilidade: 0 },
            ],
          })}
        />
      )}

      {blockedMsg && (
        <div className="scrim show" onClick={() => setBlockedMsg(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Não é possível excluir</h3>
            <p className="sub">{blockedMsg}</p>
            <div className="row"><button className="btn-ghost" onClick={() => setBlockedMsg(null)}>Entendi</button></div>
          </div>
        </div>
      )}

      {confirmDeleteStage && (
        <div className="scrim show" onClick={() => setConfirmDeleteStage(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Excluir etapa</h3>
            <p className="sub">Tem certeza que deseja excluir <strong>{confirmDeleteStage.nome}</strong>? Essa ação não pode ser desfeita.</p>
            <div className="row">
              <button className="btn-ghost" onClick={() => setConfirmDeleteStage(null)}>Cancelar</button>
              <button
                className="btn-danger"
                disabled={deleteStageMutation.isPending}
                onClick={() => deleteStageMutation.mutate({ pipelineId, stageId: confirmDeleteStage.id })}
              >
                Excluir
              </button>
            </div>
          </div>
        </div>
      )}

      {helpOpen && (
        <div className="scrim show" onClick={() => setHelpOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3><IconInfo />Como funciona o SLA por etapa</h3>
            <p className="sub">
              <strong>SLA por etapa</strong> define quanto tempo um negócio pode ficar parado antes de gerar um
              alerta de atenção. Arraste as etapas abertas para reordenar o funil — as etapas terminais
              (Ganho/Perdido) ficam sempre no fim.
            </p>
            <div className="row"><button className="btn-ghost" onClick={() => setHelpOpen(false)}>Fechar</button></div>
          </div>
        </div>
      )}
    </>
  )
}

function StageRow({ stage, openCount, terminal, colorMode = 'sem_cor', tint, draggable, onReorderDrop, onCommit, onDelete }) {
  const [dragOver, setDragOver] = useState(false)
  const showDot = !terminal && colorMode !== 'sem_cor'

  return (
    <div
      className={`stage-row${terminal ? ' terminal' : ''}${dragOver ? ' drag-target' : ''}`}
      draggable={draggable}
      onDragStart={(e) => e.dataTransfer.setData('text/stage-id', stage.id)}
      onDragOver={(e) => { if (draggable) { e.preventDefault(); setDragOver(true) } }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragOver(false)
        const fromId = e.dataTransfer.getData('text/stage-id')
        if (fromId && onReorderDrop) onReorderDrop(fromId, stage.id)
      }}
    >
      <span className="drag-handle" style={{ visibility: terminal ? 'hidden' : 'visible' }}>⠿</span>
      <div className="stage-name-cell">
        {showDot && <span className="stage-dot" style={{ background: tint }} />}
        {terminal ? (
          <span className="stage-name-input">{stage.nome}</span>
        ) : (
          <input
            className="stage-name-input"
            defaultValue={stage.nome}
            key={stage.id}
            onBlur={(e) => {
              if (e.target.value.trim() && e.target.value !== stage.nome) onCommit({ nome: e.target.value.trim() })
            }}
          />
        )}
      </div>
      <span className={`type-pill ${stage.tipo}`}>{TYPE_LABEL[stage.tipo]}</span>
      {terminal ? (
        <div className="num-field fixed">—</div>
      ) : (
        <div className="num-field">
          <input
            type="number" min="0" defaultValue={stage.sla_horas ?? ''} key={`sla-${stage.id}`}
            onBlur={(e) => {
              const v = e.target.value === '' ? null : parseInt(e.target.value, 10)
              if (v !== stage.sla_horas) onCommit({ sla_horas: v })
            }}
          />
          <span className="suffix">h</span>
        </div>
      )}
      {terminal ? (
        <div className="num-field fixed">{stage.probabilidade}%</div>
      ) : (
        <div className="num-field">
          <input
            type="number" min="0" max="100" defaultValue={stage.probabilidade ?? ''} key={`prob-${stage.id}`}
            onBlur={(e) => {
              const v = e.target.value === '' ? null : parseInt(e.target.value, 10)
              if (v !== stage.probabilidade) onCommit({ probabilidade: v })
            }}
          />
          <span className="suffix">%</span>
        </div>
      )}
      <span className={`stage-count${openCount === 0 ? ' zero' : ''}`}>{terminal ? '—' : openCount}</span>
      <div className="stage-logic-cell" title="Em breve — ver roadmap na especificação técnica">
        <button className="btn-ghost sm" disabled>+ Adicionar lógica</button>
      </div>
      <div className="stage-actions-cell">
        {!terminal && <button className="icon-btn danger" title="Excluir etapa" onClick={onDelete}>✕</button>}
      </div>
    </div>
  )
}


function NewStageDrawer({ pipelineName, onClose, onSubmit, submitting }) {
  const [nome, setNome] = useState('')
  const [sla, setSla] = useState('')
  const [prob, setProb] = useState('')

  function handleSave() {
    if (!nome.trim()) return
    onSubmit({
      nome: nome.trim(),
      sla_horas: sla === '' ? null : parseInt(sla, 10),
      probabilidade: prob === '' ? null : parseInt(prob, 10),
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div><h2>Nova etapa</h2><p>Adiciona uma etapa aberta ao funil "{pipelineName}"</p></div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          <div className="f-group">
            <label className="f-label">Nome da etapa <span className="req">*</span></label>
            <input className="f-input" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ex.: Follow-up pós-proposta" />
          </div>
          <div className="f-row">
            <div className="f-group">
              <label className="f-label">SLA (horas) <span className="opt">opcional</span></label>
              <input className="f-input" type="number" min="0" value={sla} onChange={(e) => setSla(e.target.value)} placeholder="Ex.: 72" />
            </div>
            <div className="f-group">
              <label className="f-label">Probabilidade padrão <span className="opt">opcional</span></label>
              <input className="f-input" type="number" min="0" max="100" value={prob} onChange={(e) => setProb(e.target.value)} placeholder="Ex.: 30" />
            </div>
          </div>
        </div>
        <div className="drawer-foot">
          <button className="btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn-primary" disabled={submitting} onClick={handleSave}>
            {submitting ? 'Criando…' : 'Criar etapa'}
          </button>
        </div>
      </div>
    </div>
  )
}

function NewPipelineModal({ onClose, onSubmit, submitting }) {
  const [nome, setNome] = useState('')
  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h3>Novo pipeline</h3>
        <p className="sub">Cria um pipeline com as etapas terminais Ganho/Perdido e uma etapa inicial "Novo lead" — depois é só ajustar.</p>
        <div className="f-group">
          <label className="f-label">Nome</label>
          <input className="f-input" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ex.: Vendas Enterprise" />
        </div>
        <div className="row">
          <button className="btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn-primary" disabled={submitting || !nome.trim()} onClick={() => onSubmit(nome.trim())}>
            {submitting ? 'Criando…' : 'Criar'}
          </button>
        </div>
      </div>
    </div>
  )
}
