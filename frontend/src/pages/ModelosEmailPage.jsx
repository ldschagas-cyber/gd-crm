import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createEmailTemplate, deleteEmailTemplate, listEmailTemplates, updateEmailTemplate } from '../api/emailTemplates'
import '../styles/dataTable.css'
import './ModelosEmailPage.css'

const VARS = ['nome', 'empresa', 'cargo', 'responsavel']
const PREVIEW_SAMPLE = { nome: 'Ana Beatriz Souza', empresa: 'Distribuidora Rio Verde', cargo: 'Gerente de Compras', responsavel: 'Felipe Nogueira' }

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

function IconInfo() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="10" r="7.3" />
      <path d="M10 9v4.2" strokeLinecap="round" />
      <circle cx="10" cy="6.8" r=".9" fill="currentColor" stroke="none" />
    </svg>
  )
}

export default function ModelosEmailPage() {
  const queryClient = useQueryClient()
  const [drawerTemplate, setDrawerTemplate] = useState(undefined) // undefined = fechado, null = novo, obj = editar
  const [helpOpen, setHelpOpen] = useState(false)

  const listQuery = useQuery({
    queryKey: ['email-templates', 'list'],
    queryFn: () => listEmailTemplates({ size: 100 }),
  })
  const items = listQuery.data?.items ?? []

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['email-templates'] })
  }

  const createMutation = useMutation({ mutationFn: createEmailTemplate, onSuccess: () => { setDrawerTemplate(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateEmailTemplate(id, data), onSuccess: () => { setDrawerTemplate(undefined); invalidate() } })
  const deleteMutation = useMutation({ mutationFn: deleteEmailTemplate, onSuccess: invalidate })

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Modelos de e-mail</h1>
          <p>{items.length.toLocaleString('pt-BR')} modelo(s)</p>
        </div>
        <button className="btn-primary" onClick={() => setDrawerTemplate(null)}>+ Novo modelo</button>
      </header>

      <div className="content">
        <button className="info-trigger" onClick={() => setHelpOpen(true)}>
          <IconInfo /> Variáveis disponíveis
        </button>

        <div className="card">
          {listQuery.isLoading && <p className="state-msg">Carregando modelos…</p>}
          {listQuery.isError && <p className="state-msg error">Não foi possível carregar os modelos agora.</p>}

          {listQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>Modelo</th>
                    <th>Variáveis</th>
                    <th className="actions-col"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((t) => (
                    <tr key={t.id}>
                      <td>
                        <div className="row-title">{t.nome}</div>
                        <div className="row-sub">{t.assunto}</div>
                      </td>
                      <td>
                        {t.variaveis_disponiveis.map((v) => <span className="var-chip" key={v}>{`{{${v}}}`}</span>)}
                      </td>
                      <td className="actions-col">
                        <button className="icon-btn" title="Editar" onClick={() => setDrawerTemplate(t)}>✎</button>
                        <button
                          className="icon-btn danger"
                          title="Excluir"
                          onClick={() => { if (confirm(`Excluir "${t.nome}"?`)) deleteMutation.mutate(t.id) }}
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && <tr><td colSpan={3} className="empty-cell">Nenhum modelo cadastrado.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {drawerTemplate !== undefined && (
        <TemplateDrawer
          template={drawerTemplate}
          onClose={() => setDrawerTemplate(undefined)}
          onSubmit={(data) => {
            if (drawerTemplate) updateMutation.mutate({ id: drawerTemplate.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {helpOpen && (
        <div className="scrim show" onClick={() => setHelpOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3><IconInfo />Variáveis disponíveis</h3>
            <p className="sub">
              <code>{'{{nome}}'}</code> <code>{'{{empresa}}'}</code> <code>{'{{cargo}}'}</code>{' '}
              <code>{'{{responsavel}}'}</code> — substituídas pelos dados reais no momento do envio, dentro de
              Sequências e Cadências.
            </p>
            <div className="row"><button className="btn-ghost" onClick={() => setHelpOpen(false)}>Fechar</button></div>
          </div>
        </div>
      )}
    </>
  )
}

function TemplateDrawer({ template, onClose, onSubmit, submitting, error }) {
  const [nome, setNome] = useState(template?.nome ?? '')
  const [assunto, setAssunto] = useState(template?.assunto ?? '')
  const [corpo, setCorpo] = useState(template?.corpo ?? '')
  const [touched, setTouched] = useState(false)
  const lastFocusedRef = useRef(null)
  const assuntoRef = useRef(null)
  const corpoRef = useRef(null)

  const previewAssunto = useMemo(() => mergeVarsSegments(assunto), [assunto])
  const previewCorpo = useMemo(() => mergeVarsSegments(corpo), [corpo])

  const okNome = nome.trim().length > 0
  const okAssunto = assunto.trim().length > 0
  const okCorpo = corpo.trim().length > 0

  function insertVar(v) {
    const el = lastFocusedRef.current ?? corpoRef.current
    const setValue = el === assuntoRef.current ? setAssunto : setCorpo
    const current = el === assuntoRef.current ? assunto : corpo
    const token = `{{${v}}}`
    const start = el?.selectionStart ?? current.length
    const end = el?.selectionEnd ?? current.length
    const next = current.slice(0, start) + token + current.slice(end)
    setValue(next)
    requestAnimationFrame(() => {
      if (!el) return
      el.focus()
      el.selectionStart = el.selectionEnd = start + token.length
    })
  }

  function handleSubmit(e) {
    e.preventDefault()
    setTouched(true)
    if (!okNome || !okAssunto || !okCorpo) return
    onSubmit({ nome: nome.trim(), assunto: assunto.trim(), corpo: corpo.trim() })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>{template ? 'Editar modelo' : 'Novo modelo'}</h2>
            <p>Assunto e corpo, com variáveis dinâmicas</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-group">
              <label className="f-label">Nome do modelo <span className="req">*</span></label>
              <input
                className={`f-input${touched && !okNome ? ' err' : ''}`}
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Ex.: Apresentação institucional"
              />
              <span className={`f-err${touched && !okNome ? ' show' : ''}`}>Informe o nome do modelo.</span>
            </div>

            <div className="var-buttons">
              {VARS.map((v) => (
                <button type="button" className="var-btn" key={v} onClick={() => insertVar(v)}>{`{{${v}}}`}</button>
              ))}
            </div>

            <div className="f-group">
              <label className="f-label">Assunto <span className="req">*</span></label>
              <input
                ref={assuntoRef}
                className={`f-input${touched && !okAssunto ? ' err' : ''}`}
                value={assunto}
                onChange={(e) => setAssunto(e.target.value)}
                onFocus={() => { lastFocusedRef.current = assuntoRef.current }}
                placeholder="Ex.: Olá {{nome}}, tudo bem?"
              />
              <span className={`f-err${touched && !okAssunto ? ' show' : ''}`}>Informe o assunto do e-mail.</span>
            </div>

            <div className="f-group">
              <label className="f-label">Corpo <span className="req">*</span></label>
              <textarea
                ref={corpoRef}
                className={`f-textarea${touched && !okCorpo ? ' err' : ''}`}
                value={corpo}
                onChange={(e) => setCorpo(e.target.value)}
                onFocus={() => { lastFocusedRef.current = corpoRef.current }}
                placeholder="Escreva o corpo do e-mail — use os botões acima para inserir variáveis."
              />
              <span className={`f-err${touched && !okCorpo ? ' show' : ''}`}>Informe o corpo do e-mail.</span>
            </div>

            <div className="preview-card">
              <div className="preview-label">Prévia com dados de exemplo</div>
              <div className="preview-subject">
                {previewAssunto.map((p, i) => (p.isVar ? <span className="var-fill" key={i}>{p.text}</span> : <span key={i}>{p.text}</span>))}
              </div>
              <div className="preview-body">
                {previewCorpo.map((p, i) => (p.isVar ? <span className="var-fill" key={i}>{p.text}</span> : <span key={i}>{p.text}</span>))}
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
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar modelo'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
