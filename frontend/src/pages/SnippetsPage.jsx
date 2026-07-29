import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createSnippet, deleteSnippet, listSnippets, updateSnippet } from '../api/snippets'
import '../styles/dataTable.css'
import './SnippetsPage.css'

const VARS = ['nome', 'empresa', 'cargo', 'responsavel']
const PREVIEW_SAMPLE = { nome: 'Ana Beatriz Souza', empresa: 'Distribuidora Rio Verde', cargo: 'Gerente de Compras', responsavel: 'Felipe Nogueira' }

function mergeVars(text) {
  return (text ?? '').replace(/\{\{(\w+)\}\}/g, (m, key) => PREVIEW_SAMPLE[key] ?? m)
}

// Divide o texto em partes normais e partes substituídas (variável), pra destacar
// só o valor mesclado na prévia sem recorrer a dangerouslySetInnerHTML.
function mergeVarsSegments(text) {
  const parts = []
  let lastIndex = 0
  const re = /\{\{(\w+)\}\}/g
  let m
  while ((m = re.exec(text ?? '')) !== null) {
    if (m.index > lastIndex) parts.push({ text: text.slice(lastIndex, m.index), isVar: false })
    parts.push({ text: PREVIEW_SAMPLE[m[1]] ?? m[0], isVar: Boolean(PREVIEW_SAMPLE[m[1]]) })
    lastIndex = re.lastIndex
  }
  if (lastIndex < (text ?? '').length) parts.push({ text: (text ?? '').slice(lastIndex), isVar: false })
  return parts
}

export default function SnippetsPage() {
  const queryClient = useQueryClient()
  const [drawerSnippet, setDrawerSnippet] = useState(undefined) // undefined = fechado, null = novo, obj = editar
  const demoRef = useRef(null)

  const listQuery = useQuery({
    queryKey: ['snippets', 'list'],
    queryFn: () => listSnippets({ size: 100 }),
  })
  const items = listQuery.data?.items ?? []

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['snippets'] })
  }

  const createMutation = useMutation({ mutationFn: createSnippet, onSuccess: () => { setDrawerSnippet(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateSnippet(id, data), onSuccess: () => { setDrawerSnippet(undefined); invalidate() } })
  const deleteMutation = useMutation({ mutationFn: deleteSnippet, onSuccess: invalidate })

  function handleDemoInput(e) {
    if (e.nativeEvent.data !== ' ') return
    const el = demoRef.current
    const pos = el.selectionStart
    const before = el.value.slice(0, pos)
    const m = before.match(/#([a-z0-9]+) $/i)
    if (!m) return
    const atalho = m[1].toLowerCase()
    const snip = items.find((s) => s.atalho === atalho)
    if (!snip) return
    const start = pos - m[0].length
    const replacement = mergeVars(snip.conteudo) + ' '
    el.value = el.value.slice(0, start) + replacement + el.value.slice(pos)
    const newPos = start + replacement.length
    el.selectionStart = el.selectionEnd = newPos
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Snippets</h1>
          <p>{items.length.toLocaleString('pt-BR')} bloco(s) de texto reutilizáveis</p>
        </div>
        <button className="btn-primary" onClick={() => setDrawerSnippet(null)}>+ Novo snippet</button>
      </header>

      <div className="content">
        <div className="help-card">
          Snippet é um texto curto que você digita uma vez e reusa com um atalho — diferente de Modelos de e-mail
          (e-mails inteiros usados por Sequências/Cadências), um snippet serve pra inserir rápido em <b>notas,
          tarefas ou qualquer campo de texto</b> do CRM. Digite <code>#atalho</code> seguido de espaço para expandir.
        </div>

        <div className="card">
          <div className="card-head">
            <h2>Experimente</h2>
            <p>Digite um dos atalhos abaixo e um espaço para ver o snippet se expandir</p>
          </div>
          <div className="demo-body">
            <textarea
              ref={demoRef}
              className="demo-textarea"
              placeholder="Escreva aqui — ou digite #atalho e um espaço para ver o snippet se expandir…"
              onInput={handleDemoInput}
            />
            <div className="demo-shortcuts">
              {items.map((s) => <span className="demo-shortcut" key={s.id}>#{s.atalho}</span>)}
              {items.length === 0 && <span className="demo-hint">Nenhum snippet cadastrado ainda.</span>}
            </div>
          </div>
        </div>

        <div className="card">
          {listQuery.isLoading && <p className="state-msg">Carregando snippets…</p>}
          {listQuery.isError && <p className="state-msg error">Não foi possível carregar os snippets agora.</p>}

          {listQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Atalho</th>
                    <th>Conteúdo</th>
                    <th className="actions-col"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((s) => (
                    <tr key={s.id}>
                      <td><div className="row-title">{s.nome}</div></td>
                      <td><span className="shortcut-pill">#{s.atalho}</span></td>
                      <td><div className="snippet-content-cell">{s.conteudo}</div></td>
                      <td className="actions-col">
                        <button className="icon-btn" title="Editar" onClick={() => setDrawerSnippet(s)}>✎</button>
                        <button
                          className="icon-btn danger"
                          title="Excluir"
                          onClick={() => { if (confirm(`Excluir "${s.nome}"?`)) deleteMutation.mutate(s.id) }}
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && <tr><td colSpan={4} className="empty-cell">Nenhum snippet cadastrado.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {drawerSnippet !== undefined && (
        <SnippetDrawer
          snippet={drawerSnippet}
          existing={items}
          onClose={() => setDrawerSnippet(undefined)}
          onSubmit={(data) => {
            if (drawerSnippet) updateMutation.mutate({ id: drawerSnippet.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}
    </>
  )
}

function SnippetDrawer({ snippet, existing, onClose, onSubmit, submitting, error }) {
  const [nome, setNome] = useState(snippet?.nome ?? '')
  const [atalho, setAtalho] = useState(snippet?.atalho ?? '')
  const [conteudo, setConteudo] = useState(snippet?.conteudo ?? '')
  const [touched, setTouched] = useState(false)
  const conteudoRef = useRef(null)

  const previewSegments = useMemo(() => mergeVarsSegments(conteudo), [conteudo])

  const okNome = nome.trim().length > 0
  const dup = existing.find((s) => s.atalho === atalho && s.id !== snippet?.id)
  const okAtalho = atalho.length > 0 && !dup
  const okConteudo = conteudo.trim().length > 0

  function handleAtalhoChange(e) {
    setAtalho(e.target.value.toLowerCase().replace(/[^a-z0-9]/g, ''))
  }

  function insertVar(v) {
    const el = conteudoRef.current
    const token = `{{${v}}}`
    const start = el?.selectionStart ?? conteudo.length
    const end = el?.selectionEnd ?? conteudo.length
    const next = conteudo.slice(0, start) + token + conteudo.slice(end)
    setConteudo(next)
    requestAnimationFrame(() => {
      if (!el) return
      el.focus()
      el.selectionStart = el.selectionEnd = start + token.length
    })
  }

  function handleSubmit(e) {
    e.preventDefault()
    setTouched(true)
    if (!okNome || !okAtalho || !okConteudo) return
    onSubmit({ nome: nome.trim(), atalho, conteudo: conteudo.trim() })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>{snippet ? 'Editar snippet' : 'Novo snippet'}</h2>
            <p>Um atalho curto pra inserir esse texto em qualquer lugar</p>
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
                placeholder="Ex.: Modelo de preço padrão"
              />
              <span className={`f-err${touched && !okNome ? ' show' : ''}`}>Informe o nome do snippet.</span>
            </div>

            <div className="f-group">
              <label className="f-label">Atalho <span className="req">*</span></label>
              <div className="atalho-row">
                <span className="atalho-prefix">#</span>
                <input
                  className={`f-input${touched && !okAtalho ? ' err' : ''}`}
                  value={atalho}
                  onChange={handleAtalhoChange}
                  placeholder="preco"
                />
              </div>
              <span className="f-hint">Só letras minúsculas e números, sem espaço — digitado como <code>#atalho</code> em qualquer campo de texto.</span>
              <span className={`f-err${touched && !okAtalho ? ' show' : ''}`}>
                {dup ? `Esse atalho já é usado por "${dup.nome}".` : 'Informe um atalho único (só letras/números).'}
              </span>
            </div>

            <div className="var-buttons">
              {VARS.map((v) => (
                <button type="button" className="var-btn" key={v} onClick={() => insertVar(v)}>{`{{${v}}}`}</button>
              ))}
            </div>

            <div className="f-group">
              <label className="f-label">Conteúdo <span className="req">*</span></label>
              <textarea
                ref={conteudoRef}
                className={`f-textarea${touched && !okConteudo ? ' err' : ''}`}
                value={conteudo}
                onChange={(e) => setConteudo(e.target.value)}
                placeholder="Escreva o texto que será inserido…"
              />
              <span className={`f-err${touched && !okConteudo ? ' show' : ''}`}>Informe o conteúdo do snippet.</span>
            </div>

            <div className="preview-card">
              <div className="preview-label">Prévia com dados de exemplo</div>
              <div className="preview-body">
                {conteudo
                  ? previewSegments.map((p, i) => (p.isVar ? <span className="var-fill" key={i}>{p.text}</span> : <span key={i}>{p.text}</span>))
                  : '—'}
              </div>
            </div>

            {error && (
              <p className="state-msg error">
                {error.response?.data?.error?.message ?? 'Não foi possível salvar. Confira os dados e tente de novo.'}
              </p>
            )}
          </div>
          <div className="drawer-foot">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar snippet'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
