import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { createTask } from '../api/tasks'
import { listUsers } from '../api/users'
import { TIPO_LABEL } from './TaskTypeIcon'

const PRIO_LABEL = { alta: 'Alta', media: 'Média', baixa: 'Baixa' }

// Modal compartilhado por Empresas/Contatos/Negócios (seleção em lote na grade) pra
// criar uma tarefa de uma vez só, igual ao EnrollModal — ver `alvos`. Cada item de
// `alvos` já traz os vínculos derivados (empresa/contato/negócio) pra tarefa nascer
// ligada aos três quando fizer sentido (ex.: selecionar contatos já herda a empresa).
export default function BulkTaskModal({ alvos, alvoLabel, onClose, onCreated }) {
  const [form, setForm] = useState({
    titulo: '',
    descricao: '',
    tipo: 'ligacao',
    prioridade: 'media',
    data: new Date().toISOString().slice(0, 10),
    hora: '',
    responsavel_id: '',
  })
  const [touched, setTouched] = useState(false)

  const usersQuery = useQuery({ queryKey: ['users', 'for-assign'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const users = usersQuery.data?.items ?? []

  const createMutation = useMutation({
    mutationFn: () => Promise.all(alvos.map((alvo) => createTask({
      titulo: form.titulo.trim(),
      descricao: form.descricao.trim() || null,
      tipo: form.tipo,
      prioridade: form.prioridade,
      data: form.data,
      hora: form.hora || null,
      responsavel_id: form.responsavel_id,
      company_id: alvo.company_id ?? null,
      contact_id: alvo.contact_id ?? null,
      deal_id: alvo.deal_id ?? null,
    }))),
    onSuccess: () => { onCreated?.(); onClose() },
  })

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleConfirm() {
    setTouched(true)
    if (!form.titulo.trim() || !form.responsavel_id || !form.data) return
    createMutation.mutate()
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h3>Nova tarefa</h3>
        <p className="sub">Criar tarefa para <strong>{alvoLabel}</strong>.</p>

        <div className="f-group">
          <label className="f-label">Título <span className="req">*</span></label>
          <input
            className={`f-input${touched && !form.titulo.trim() ? ' err' : ''}`}
            value={form.titulo}
            onChange={set('titulo')}
            placeholder="Ex.: Ligar para confirmar reunião"
          />
          {touched && !form.titulo.trim() && <span className="f-err show">Informe um título.</span>}
        </div>
        <div className="f-row">
          <div className="f-group">
            <label className="f-label">Tipo</label>
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
            <input className="f-input" type="date" value={form.data} onChange={set('data')} />
          </div>
          <div className="f-group">
            <label className="f-label">Hora <span className="opt">opcional</span></label>
            <input className="f-input" type="time" value={form.hora} onChange={set('hora')} />
          </div>
        </div>
        <div className="f-group">
          <label className="f-label">Responsável <span className="req">*</span></label>
          <select className={`f-select${touched && !form.responsavel_id ? ' err' : ''}`} value={form.responsavel_id} onChange={set('responsavel_id')}>
            <option value="">Selecione…</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
          {touched && !form.responsavel_id && <span className="f-err show">Selecione um responsável.</span>}
        </div>

        {createMutation.isError && (
          <p className="state-msg error">
            {createMutation.error?.response?.data?.error?.message ?? 'Não foi possível criar a(s) tarefa(s). Tente de novo.'}
          </p>
        )}

        <div className="row">
          <button className="btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn-primary" disabled={createMutation.isPending} onClick={handleConfirm}>
            {createMutation.isPending ? 'Criando…' : 'Criar tarefa'}
          </button>
        </div>
      </div>
    </div>
  )
}
