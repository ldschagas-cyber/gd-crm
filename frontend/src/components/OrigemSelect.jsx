import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createOrigemOption, listOrigemOptions } from '../api/origemOptions'

const NOVA_OPCAO = '__nova_origem__'

// Select de Origem compartilhado por EmpresasPage e PesquisaLeadsPage: além da lista
// cadastrada (opções de fábrica + as que o próprio tenant já criou — ver
// app/services/origem_option.py), sempre mostra "+ Criar nova opção…" no final, que abre
// um mini-formulário pra cadastrar uma opção nova sem sair da tela.
// `value`/`onChange` seguem o contrato de um <select> nativo (onChange recebe o evento),
// pra encaixar sem mudanças nos `set(field)` já usados nos formulários de Empresa/Lead.
export default function OrigemSelect({ id, className, value, onChange, placeholder = 'Selecione…' }) {
  const [criando, setCriando] = useState(false)
  const queryClient = useQueryClient()

  const optionsQuery = useQuery({ queryKey: ['origem-options'], queryFn: listOrigemOptions, staleTime: 60_000 })
  const opcoes = optionsQuery.data ?? []
  // Registro pode já ter uma origem gravada fora da lista (importação, dado legado) —
  // mantém ela selecionável em vez de "sumir" o valor atual do formulário.
  const opcoesExibidas = value && !opcoes.includes(value) ? [value, ...opcoes] : opcoes

  function handleChange(e) {
    if (e.target.value === NOVA_OPCAO) {
      setCriando(true)
      return
    }
    onChange(e)
  }

  function handleCriada(nome) {
    queryClient.setQueryData(['origem-options'], (old) => (old && !old.includes(nome) ? [...old, nome] : old ?? [nome]))
    setCriando(false)
    onChange({ target: { value: nome } })
  }

  return (
    <>
      <select id={id} className={className} value={value} onChange={handleChange}>
        <option value="">{placeholder}</option>
        {opcoesExibidas.map((o) => <option key={o} value={o}>{o}</option>)}
        <option value={NOVA_OPCAO}>+ Criar nova opção…</option>
      </select>
      {criando && <NovaOrigemModal onClose={() => setCriando(false)} onCriada={handleCriada} />}
    </>
  )
}

function NovaOrigemModal({ onClose, onCriada }) {
  const [nome, setNome] = useState('')
  const [touched, setTouched] = useState(false)
  const okNome = nome.trim().length > 0

  const createMutation = useMutation({
    mutationFn: () => createOrigemOption(nome.trim()),
    onSuccess: (created) => onCriada(created.nome),
  })

  function handleConfirm() {
    setTouched(true)
    if (!okNome) return
    createMutation.mutate()
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h3>Nova opção de Origem</h3>
        <p className="sub">Cadastre uma opção nova para o campo Origem — ela passa a aparecer na lista para todo o time.</p>

        <div className="f-group">
          <label className="f-label">Nome</label>
          <input
            className={`f-input${touched && !okNome ? ' err' : ''}`}
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Ex.: Evento setorial"
            autoFocus
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleConfirm() } }}
          />
          {touched && !okNome && <span className="f-err show">Informe um nome.</span>}
        </div>

        {createMutation.isError && (
          <p className="state-msg error">
            {createMutation.error?.response?.data?.error?.message ?? 'Não foi possível cadastrar. Tente de novo.'}
          </p>
        )}

        <div className="row">
          <button className="btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn-primary" disabled={createMutation.isPending} onClick={handleConfirm}>
            {createMutation.isPending ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  )
}
