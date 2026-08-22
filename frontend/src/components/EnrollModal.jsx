import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { createSequenceEnrollment, listSequences } from '../api/sequences'

// Modal compartilhado por Empresa/Negócio/Contato (individual ou em lote) para inscrever
// em uma Sequência já cadastrada (ver SequenciasPage).
// `alvos` é uma lista de { company_id } | { contact_id } | { deal_id } — um item pro caso
// de uma tela de detalhe, vários pro caso de seleção em lote numa lista.
// `defaultSequenceId` pré-seleciona uma sequência (ex.: sugestão do SDR Argos) — é só um
// preenchimento inicial editável, NUNCA uma inscrição automática: o clique em "Inscrever"
// continua sendo sempre do vendedor (decisão travada nº 6, ver docs/PLANO_SDR_AUTONOMO.md).
export default function EnrollModal({ alvos, alvoLabel, defaultSequenceId, sugestaoLabel, onClose, onEnrolled }) {
  const [selectedId, setSelectedId] = useState(defaultSequenceId ?? '')
  const [touched, setTouched] = useState(false)

  const sequencesQuery = useQuery({ queryKey: ['sequences', 'for-enroll'], queryFn: () => listSequences({ size: 100 }) })
  const sequences = (sequencesQuery.data?.items ?? []).filter((s) => s.ativo)
  const sugestaoAindaValida = defaultSequenceId && sequences.some((s) => s.id === defaultSequenceId)

  const enrollMutation = useMutation({
    mutationFn: () => Promise.all(alvos.map((alvo) => createSequenceEnrollment(selectedId, alvo))),
    onSuccess: () => { onEnrolled?.(); onClose() },
  })

  function handleConfirm() {
    setTouched(true)
    if (!selectedId) return
    enrollMutation.mutate()
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h3>Inscrever em automação</h3>
        <p className="sub">Inscrever <strong>{alvoLabel}</strong> em uma sequência de tarefas.</p>

        {sugestaoAindaValida && (
          <p className="sub" style={{ marginTop: -8 }}>
            ✦ Sequência pré-selecionada pela sugestão do SDR Argos{sugestaoLabel ? ` — ${sugestaoLabel}` : ''}. Pode trocar antes de confirmar.
          </p>
        )}

        <div className="f-group">
          <label className="f-label">Sequência</label>
          <select className={`f-select${touched && !selectedId ? ' err' : ''}`} value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
            <option value="">Selecione…</option>
            {sequences.map((o) => <option key={o.id} value={o.id}>{o.nome}</option>)}
          </select>
          {sequences.length === 0 && (
            <span className="f-hint">Nenhuma sequência ativa cadastrada ainda.</span>
          )}
          {touched && !selectedId && <span className="f-err show">Selecione uma sequência.</span>}
        </div>

        {enrollMutation.isError && (
          <p className="state-msg error">
            {enrollMutation.error?.response?.data?.error?.message ?? 'Não foi possível inscrever. Tente de novo.'}
          </p>
        )}

        <div className="row">
          <button className="btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn-primary" disabled={enrollMutation.isPending} onClick={handleConfirm}>
            {enrollMutation.isPending ? 'Inscrevendo…' : 'Inscrever'}
          </button>
        </div>
      </div>
    </div>
  )
}
