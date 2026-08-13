import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createMessageTemplate, deleteMessageTemplate, listMessageTemplates, updateMessageTemplate,
} from '../api/messageTemplates'
import '../styles/dataTable.css'
import './ModelosMensagemPage.css'

const VARS = ['nome', 'empresa', 'cargo', 'responsavel', 'setor']
const PREVIEW_SAMPLE = { nome: 'Ana Beatriz Souza', empresa: 'Distribuidora Rio Verde', cargo: 'Gerente de Compras', responsavel: 'Felipe Nogueira', setor: 'Distribuição' }

const CANAL_LABEL = { whatsapp: 'WhatsApp', linkedin_conexao: 'LinkedIn (conexão)', linkedin_mensagem: 'LinkedIn (mensagem)' }
const CANAL_HINT = {
  whatsapp: 'Texto livre. Placeholders como [link] ficam pro vendedor completar na hora de colar.',
  linkedin_conexao: 'Nota enviada junto com o pedido de conexão — o LinkedIn limita a ~300 caracteres.',
  linkedin_mensagem: 'Mensagem enviada pelo chat do LinkedIn (após conexão aceita, ou reforço posterior) — sem limite curto.',
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

function IconInfo() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="10" r="7.3" />
      <path d="M10 9v4.2" strokeLinecap="round" />
      <circle cx="10" cy="6.8" r=".9" fill="currentColor" stroke="none" />
    </svg>
  )
}

export default function ModelosMensagemPage() {
  const queryClient = useQueryClient()
  const [drawerTemplate, setDrawerTemplate] = useState(undefined) // undefined = fechado, null = novo, obj = editar
  const [helpOpen, setHelpOpen] = useState(false)
  const [canalFiltro, setCanalFiltro] = useState('')

  const listQuery = useQuery({
    queryKey: ['message-templates', 'list'],
    queryFn: () => listMessageTemplates({ size: 100 }),
  })
  const items = listQuery.data?.items ?? []
  const itemsFiltrados = canalFiltro ? items.filter((t) => t.canal === canalFiltro) : items

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['message-templates'] })
  }

  const createMutation = useMutation({ mutationFn: createMessageTemplate, onSuccess: () => { setDrawerTemplate(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateMessageTemplate(id, data), onSuccess: () => { setDrawerTemplate(undefined); invalidate() } })
  const deleteMutation = useMutation({ mutationFn: deleteMessageTemplate, onSuccess: invalidate })

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Modelos de mensagem</h1>
          <p>{items.length.toLocaleString('pt-BR')} modelo(s) · WhatsApp e LinkedIn</p>
        </div>
        <button className="btn-primary" onClick={() => setDrawerTemplate(null)}>+ Novo modelo</button>
      </header>

      <div className="content">
        <button className="info-trigger" onClick={() => setHelpOpen(true)}>
          <IconInfo /> Variáveis disponíveis
        </button>

        <div className="canal-filter">
          <button className={`canal-pill${canalFiltro === '' ? ' active' : ''}`} onClick={() => setCanalFiltro('')}>Todos</button>
          {Object.entries(CANAL_LABEL).map(([v, label]) => (
            <button key={v} className={`canal-pill${canalFiltro === v ? ' active' : ''}`} onClick={() => setCanalFiltro(v)}>{label}</button>
          ))}
        </div>

        <div className="card">
          {listQuery.isLoading && <p className="state-msg">Carregando modelos…</p>}
          {listQuery.isError && <p className="state-msg error">Não foi possível carregar os modelos agora.</p>}

          {listQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>Modelo</th>
                    <th>Canal</th>
                    <th>Variáveis</th>
                    <th className="actions-col"></th>
                  </tr>
                </thead>
                <tbody>
                  {itemsFiltrados.map((t) => (
                    <tr key={t.id}>
                      <td>
                        <div className="row-title" onClick={() => setDrawerTemplate(t)}>{t.nome}</div>
                        <div className="row-sub">{t.corpo}</div>
                      </td>
                      <td><span className={`canal-tag ${t.canal}`}>{CANAL_LABEL[t.canal] ?? t.canal}</span></td>
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
                  {itemsFiltrados.length === 0 && <tr><td colSpan={4} className="empty-cell">Nenhum modelo cadastrado.</td></tr>}
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
              <code>{'{{responsavel}}'}</code> <code>{'{{setor}}'}</code> — substituídas pelos dados reais do
              contato quando a tarefa é gerada por uma Sequência. Sem Sequência (ou sem contato pra mesclar), a
              tarefa mostra o texto com as variáveis sem substituir.
            </p>
            <div className="row"><button className="btn-ghost" onClick={() => setHelpOpen(false)}>Fechar</button></div>
          </div>
        </div>
      )}
    </>
  )
}

function TemplateDrawer({ template, onClose, onSubmit, submitting, error }) {
  const [canal, setCanal] = useState(template?.canal ?? 'whatsapp')
  const [nome, setNome] = useState(template?.nome ?? '')
  const [corpo, setCorpo] = useState(template?.corpo ?? '')
  const [whatsappContentSid, setWhatsappContentSid] = useState(template?.whatsapp_content_sid ?? '')
  const [touched, setTouched] = useState(false)
  const corpoRef = useRef(null)

  const previewCorpo = useMemo(() => mergeVarsSegments(corpo), [corpo])

  const okNome = nome.trim().length > 0
  const okCorpo = corpo.trim().length > 0

  function insertVar(v) {
    const el = corpoRef.current
    const token = `{{${v}}}`
    const start = el?.selectionStart ?? corpo.length
    const end = el?.selectionEnd ?? corpo.length
    const next = corpo.slice(0, start) + token + corpo.slice(end)
    setCorpo(next)
    requestAnimationFrame(() => {
      if (!el) return
      el.focus()
      el.selectionStart = el.selectionEnd = start + token.length
    })
  }

  function handleSubmit(e) {
    e.preventDefault()
    setTouched(true)
    if (!okNome || !okCorpo) return
    onSubmit({ canal, nome: nome.trim(), corpo: corpo.trim(), whatsapp_content_sid: whatsappContentSid.trim() || null })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>{template ? 'Editar modelo' : 'Novo modelo'}</h2>
            <p>Escolha o canal e escreva o texto, com variáveis dinâmicas</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-group">
              <label className="f-label">Canal <span className="req">*</span></label>
              <div className="canal-select">
                {Object.entries(CANAL_LABEL).map(([v, label]) => (
                  <label key={v} className={`canal-opt ${v}${canal === v ? ' sel' : ''}`}>
                    <input type="radio" name="canal" value={v} checked={canal === v} onChange={() => setCanal(v)} />
                    {label}
                  </label>
                ))}
              </div>
              <span className="f-hint">{CANAL_HINT[canal]}</span>
            </div>

            <div className="f-group">
              <label className="f-label">Nome do modelo <span className="req">*</span></label>
              <input
                className={`f-input${touched && !okNome ? ' err' : ''}`}
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Ex.: D9 — primeiro contato (Lead Frio)"
              />
              <span className={`f-err${touched && !okNome ? ' show' : ''}`}>Informe o nome do modelo.</span>
            </div>

            <div className="var-buttons">
              {VARS.map((v) => (
                <button type="button" className="var-btn" key={v} onClick={() => insertVar(v)}>{`{{${v}}}`}</button>
              ))}
            </div>

            <div className="f-group">
              <label className="f-label">{canal === 'linkedin_conexao' ? 'Nota de conexão' : 'Texto da mensagem'} <span className="req">*</span></label>
              <textarea
                ref={corpoRef}
                className={`f-textarea${touched && !okCorpo ? ' err' : ''}`}
                value={corpo}
                onChange={(e) => setCorpo(e.target.value)}
                placeholder="Escreva a mensagem — use os botões acima para inserir variáveis."
              />
              <span className={`f-err${touched && !okCorpo ? ' show' : ''}`}>Informe o texto da mensagem.</span>
            </div>

            {canal === 'whatsapp' && (
              <div className="f-group">
                <label className="f-label">SID do Content Template (Twilio) <span className="opt">opcional</span></label>
                <input
                  className="f-input"
                  value={whatsappContentSid}
                  onChange={(e) => setWhatsappContentSid(e.target.value)}
                  placeholder="Ex.: HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                />
                <span className="f-hint">
                  Só preencha depois que este texto for aprovado como template pelo Meta e cadastrado no Twilio
                  Content Template Builder. Sem isso, a etapa de Sequência continua virando Tarefa manual pro
                  vendedor copiar — enviar automaticamente um texto não aprovado viola a política do WhatsApp e
                  arrisca banir o número da empresa.
                </span>
              </div>
            )}

            <div className="preview-card">
              <div className="preview-label">Prévia com dados de exemplo</div>
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
