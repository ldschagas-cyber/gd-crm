import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createForm, getFormsKpis, listForms, listFormSubmissions, updateForm,
} from '../api/forms'
import {
  getDailySessions, getIdentifiedCompanies, getSiteVisitsKpis, getTopPages,
} from '../api/siteVisits'
import { getTenant } from '../api/tenant'
import '../styles/dataTable.css'
import '../styles/detailPage.css'
import './FormulariosRastreioPage.css'

const STATUS_LABEL = { ativo: 'Ativo', pausado: 'Pausado', rascunho: 'Rascunho' }
const FIELD_GROUPS = {
  Empresa: [
    ['empresa', 'Empresa'], ['cnpj', 'CNPJ'], ['site', 'Site'], ['cidade', 'Cidade'],
    ['uf', 'UF'], ['segmento', 'Segmento'], ['porte', 'Porte'],
  ],
  Contato: [
    ['telefone', 'Telefone'], ['whatsapp', 'WhatsApp'], ['linkedin', 'LinkedIn'],
    ['cargo', 'Cargo'], ['nascimento', 'Data de nascimento'],
  ],
  Outros: [['origem', 'Origem do lead'], ['ja_utiliza_tms', 'Já utiliza TMS?'], ['mensagem', 'Mensagem']],
}
// Campos cujo widget não é o <input type="text"> padrão — espelha FORM_FIELD_TYPES
// do backend (app/models/form.py). Campos personalizados são sempre texto livre.
const FIELD_TYPES = { mensagem: 'textarea', ja_utiliza_tms: 'boolean' }
const FIELD_FULL_WIDTH = new Set(['mensagem'])

function knownFieldLabel(key) {
  for (const grupo of Object.values(FIELD_GROUPS)) {
    const found = grupo.find(([k]) => k === key)
    if (found) return found[1]
  }
  return null
}
const CO_BADGE = {
  lead: { label: 'Já é lead', cls: 'lead' },
  qualificado: { label: 'Já é lead', cls: 'lead' },
  cliente: { label: 'Cliente', cls: 'client' },
  perdido: { label: 'Perdido', cls: 'lead' },
  inativo: { label: 'Inativo', cls: 'lead' },
}

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime()
  const days = Math.floor(diffMs / 86400000)
  if (days <= 0) return 'hoje'
  if (days === 1) return 'há 1 dia'
  return `há ${days} dias`
}
function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}

export default function FormulariosRastreioPage() {
  const [tab, setTab] = useState('formularios')
  const queryClient = useQueryClient()
  const [drawerForm, setDrawerForm] = useState(undefined)

  const companiesQuery = useQuery({ queryKey: ['site-visits', 'companies'], queryFn: () => getIdentifiedCompanies(30, 20) })

  function invalidateForms() {
    queryClient.invalidateQueries({ queryKey: ['forms'] })
  }
  const createMutation = useMutation({ mutationFn: createForm, onSuccess: () => { setDrawerForm(undefined); invalidateForms() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateForm(id, data), onSuccess: () => { setDrawerForm(undefined); invalidateForms() } })

  function handleExportCsv() {
    const rows = companiesQuery.data ?? []
    const headers = ['empresa', 'pagina', 'origem', 'ultima_visita']
    const lines = [headers.join(',')]
    rows.forEach((r) => lines.push([r.empresa, r.path, r.origem ?? '', r.ultima_visita].join(',')))
    const blob = new Blob([`﻿${lines.join('\r\n')}`], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'rastreio-site.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>{tab === 'formularios' ? 'Formulários' : 'Rastreio do site'}</h1>
          <p>{tab === 'formularios'
            ? 'Capture leads direto do site institucional'
            : 'Visitantes identificados no site institucional'}</p>
        </div>
        <div className="page-actions">
          {tab === 'formularios' ? (
            <button className="btn-primary" onClick={() => setDrawerForm(null)}>+ Novo formulário</button>
          ) : (
            <>
              <span className="period-pill">Últimos 30 dias</span>
              <button className="btn-ghost" onClick={handleExportCsv}>Exportar CSV</button>
            </>
          )}
        </div>
      </header>

      <div className="content">
        <div className="tabs-row">
          <div className="segmented">
            <button className={tab === 'formularios' ? 'active' : ''} onClick={() => setTab('formularios')}>Formulários</button>
            <button className={tab === 'rastreio' ? 'active' : ''} onClick={() => setTab('rastreio')}>Rastreio do site</button>
          </div>
        </div>

        {tab === 'formularios'
          ? <FormulariosTab drawerForm={drawerForm} setDrawerForm={setDrawerForm} createMutation={createMutation} updateMutation={updateMutation} />
          : <RastreioTab companiesQuery={companiesQuery} />}
      </div>
    </>
  )
}

function FormulariosTab({ drawerForm, setDrawerForm, createMutation, updateMutation }) {
  const [embedForm, setEmbedForm] = useState(null)
  const [previewFormId, setPreviewFormId] = useState(null)

  const kpisQuery = useQuery({ queryKey: ['forms', 'kpis'], queryFn: getFormsKpis })
  const formsQuery = useQuery({ queryKey: ['forms', 'list'], queryFn: listForms })
  const forms = formsQuery.data ?? []

  const activeForm = forms.find((f) => f.id === previewFormId) ?? forms.find((f) => f.status === 'ativo') ?? forms[0]
  const submissionsQuery = useQuery({
    queryKey: ['forms', 'submissions', activeForm?.id],
    queryFn: () => listFormSubmissions(activeForm.id, { size: 6 }),
    enabled: Boolean(activeForm),
  })

  const k = kpisQuery.data

  return (
    <div className="tab-content-stack">
      {k && (
        <div className="kpi-row">
          <div className="kpi-card"><div className="label">Formulários ativos</div><div className="value">{k.formularios_ativos}</div><div className="note">de {k.formularios_total} cadastrados</div></div>
          <div className="kpi-card"><div className="label">Envios (30 dias)</div><div className="value">{k.envios_30d}</div></div>
          <div className="kpi-card"><div className="label">Taxa de conversão média</div><div className="value">{k.taxa_conversao_media != null ? `${k.taxa_conversao_media}%` : '—'}</div><div className="note">visitas → envio</div></div>
          <div className="kpi-card"><div className="label">Leads gerados (30d)</div><div className="value">{k.leads_gerados_30d}</div><div className="note">criados automaticamente</div></div>
        </div>
      )}

      <div className="card">
        <div className="card-head"><div><h3>Todos os formulários</h3><p>Publicados no site institucional e no blog</p></div></div>
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr><th>Formulário</th><th className="num">Envios (30d)</th><th className="num">Conversão</th><th>Status</th><th>Atualizado</th><th></th></tr>
            </thead>
            <tbody>
              {forms.map((f) => (
                <tr key={f.id} onClick={() => setPreviewFormId(f.id)} style={{ cursor: 'pointer' }}>
                  <td><div className="row-title">{f.nome}</div>{f.pagina && <div className="row-sub">{f.pagina}</div>}</td>
                  <td className="num">{f.envios_30d || '—'}</td>
                  <td className="num">{f.conversao_pct != null ? `${f.conversao_pct}%` : '—'}</td>
                  <td><span className="status-pill" data-status={f.status}><span className="d" />{STATUS_LABEL[f.status]}</span></td>
                  <td>{timeAgo(f.updated_at)}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <div className="row-actions">
                      {f.status === 'ativo' && (
                        <button className="icon-action" title="Código de incorporação" onClick={() => setEmbedForm(f)}>{'</>'}</button>
                      )}
                      <button className="icon-action" title="Editar" onClick={() => setDrawerForm(f)}>✎</button>
                    </div>
                  </td>
                </tr>
              ))}
              {formsQuery.data && forms.length === 0 && (
                <tr><td colSpan={6}><p className="state-msg">Nenhum formulário cadastrado ainda.</p></td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {activeForm && (
        <div className="card">
          <div className="card-head"><div><h3>Últimos envios</h3><p>Formulário &quot;{activeForm.nome}&quot;</p></div></div>
          <div className="subm-list">
            {(submissionsQuery.data?.items ?? []).map((s) => (
              <div className="subm-item" key={s.id}>
                <div className="subm-avatar">{initials(s.valores?.empresa || s.nome)}</div>
                <div className="subm-text">
                  <b>{s.valores?.empresa || s.nome}</b> · {s.email}
                  <div className="subm-meta">{new Date(s.created_at).toLocaleString('pt-BR')}</div>
                </div>
                {s.company_id ? (
                  <span className={s.duplicado ? 'tag-dup' : 'tag-lead'}>{s.duplicado ? 'empresa já existente' : 'novo lead criado'}</span>
                ) : (
                  <span className="tag-dup">só registrado</span>
                )}
              </div>
            ))}
            {submissionsQuery.data && submissionsQuery.data.items.length === 0 && (
              <p className="state-msg">Nenhum envio ainda.</p>
            )}
          </div>
        </div>
      )}

      {drawerForm !== undefined && (
        <FormBuilderDrawer
          form={drawerForm}
          onClose={() => setDrawerForm(undefined)}
          onSubmit={(data) => (drawerForm ? updateMutation.mutate({ id: drawerForm.id, data }) : createMutation.mutate(data))}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {embedForm && <EmbedModal form={embedForm} onClose={() => setEmbedForm(null)} />}
    </div>
  )
}

function FormBuilderDrawer({ form, onClose, onSubmit, submitting, error }) {
  const [nome, setNome] = useState(form?.nome ?? '')
  const [pagina, setPagina] = useState(form?.pagina ?? '')
  const [status, setStatus] = useState(form?.status ?? 'rascunho')
  const [postSubmit, setPostSubmit] = useState(form?.post_submit_action ?? 'criar_lead')
  const [campos, setCampos] = useState(form?.campos ?? [])
  const [camposPersonalizados, setCamposPersonalizados] = useState(form?.campos_personalizados ?? {})
  const [customFieldInput, setCustomFieldInput] = useState('')
  const [dragOverId, setDragOverId] = useState(null)
  const [dragOverEnd, setDragOverEnd] = useState(false)

  function fieldLabel(key) {
    return knownFieldLabel(key) ?? camposPersonalizados[key] ?? key
  }
  function fieldType(key) {
    return FIELD_TYPES[key] ?? 'text'
  }

  function insertField(id, beforeId) {
    setCampos((prev) => {
      const next = prev.filter((x) => x !== id)
      const idx = beforeId ? next.indexOf(beforeId) : -1
      next.splice(idx < 0 ? next.length : idx, 0, id)
      return next
    })
  }
  function removeField(id) {
    setCampos((prev) => prev.filter((x) => x !== id))
  }
  function addCustomField() {
    const val = customFieldInput.trim()
    if (!val) return
    const id = `custom_${Date.now()}`
    setCamposPersonalizados((prev) => ({ ...prev, [id]: val }))
    insertField(id, null)
    setCustomFieldInput('')
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!nome.trim()) return
    onSubmit({
      nome: nome.trim(), pagina: pagina.trim() || null, status, post_submit_action: postSubmit,
      campos, campos_personalizados: camposPersonalizados,
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" style={{ width: 'min(920px, 100vw)' }} onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div><h2>{form ? 'Editar formulário' : 'Novo formulário'}</h2><p>Escolha os campos que este formulário vai capturar</p></div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Nome interno <span className="req">*</span></label>
                <input className="f-input" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ex.: Solicitar cotação de frete" required />
              </div>
              <div className="f-group">
                <label className="f-label">Página de publicação <span className="opt">opcional</span></label>
                <input className="f-input" value={pagina} onChange={(e) => setPagina(e.target.value)} placeholder="/diagnostico" />
              </div>
            </div>

            <div className="f-group">
              <label className="f-label">Campos do formulário</label>
              <p className="hint-text">Nome e e-mail são sempre capturados. Arraste um campo da lista à esquerda pro formulário (ou clique pra adicionar ao final); passe o mouse sobre um campo adicionado pra reordenar ou remover.</p>
              <div className="builder-grid">
                <div className="palette-col">
                  {Object.entries(FIELD_GROUPS).map(([grupo, camposGrupo]) => (
                    <div key={grupo}>
                      <div className="palette-group-label">{grupo}</div>
                      {camposGrupo.map(([key, label]) => {
                        const added = campos.includes(key)
                        return (
                          <div
                            key={key}
                            className={`palette-chip${added ? ' added' : ''}`}
                            draggable={!added}
                            onDragStart={(e) => {
                              e.dataTransfer.setData('text/plain', key)
                              e.dataTransfer.effectAllowed = 'copy'
                            }}
                            onClick={() => { if (!added) insertField(key, null) }}
                          >
                            <span>{label}</span>
                            {added && <span className="added-check">✓</span>}
                          </div>
                        )
                      })}
                    </div>
                  ))}
                  <p className="palette-hint">Não achou o campo? Crie um personalizado (sempre texto livre):</p>
                  <div className="palette-add-row">
                    <input
                      type="text"
                      value={customFieldInput}
                      onChange={(e) => setCustomFieldInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCustomField() } }}
                      placeholder="Nome do campo"
                    />
                    <button type="button" className="palette-add-btn" onClick={addCustomField} aria-label="Adicionar campo">+</button>
                  </div>
                </div>

                <div className="canvas-col">
                  <p className="canvas-intro">Queremos ouvir sua opinião! Preencha o formulário que entraremos em contato assim que for possível.</p>
                  <div className="canvas-grid">
                    <CanvasField field={{ label: 'Nome' }} locked type="text" />
                    <CanvasField field={{ label: 'E-mail' }} locked type="email" fullWidth />
                    {campos.map((key) => (
                      <CanvasField
                        key={key}
                        field={{ label: fieldLabel(key) }}
                        type={fieldType(key)}
                        fullWidth={FIELD_FULL_WIDTH.has(key)}
                        dragOver={dragOverId === key}
                        onDragStart={(e) => {
                          e.dataTransfer.setData('text/plain', key)
                          e.dataTransfer.effectAllowed = 'move'
                        }}
                        onDragOver={(e) => { e.preventDefault(); setDragOverId(key) }}
                        onDragLeave={() => setDragOverId((cur) => (cur === key ? null : cur))}
                        onDrop={(e) => {
                          e.preventDefault()
                          setDragOverId(null)
                          const id = e.dataTransfer.getData('text/plain')
                          if (id && id !== key) insertField(id, key)
                        }}
                        onRemove={() => removeField(key)}
                      />
                    ))}
                    <div
                      className={`canvas-dropzone${dragOverEnd ? ' drag-over' : ''}`}
                      onDragOver={(e) => { e.preventDefault(); setDragOverEnd(true) }}
                      onDragLeave={() => setDragOverEnd(false)}
                      onDrop={(e) => {
                        e.preventDefault()
                        setDragOverEnd(false)
                        const id = e.dataTransfer.getData('text/plain')
                        if (id) insertField(id, null)
                      }}
                    >
                      {campos.length ? 'Solte aqui para adicionar ao final' : 'Arraste campos da lista à esquerda para adicionar ao formulário'}
                    </div>
                  </div>
                  <div className="canvas-actions"><button type="button" className="preview-submit">Enviar</button></div>
                </div>
              </div>
            </div>

            <div className="f-group">
              <label className="f-label">Ao receber uma resposta</label>
              <div className="radio-row">
                <label className="radio-item">
                  <input type="radio" checked={postSubmit === 'criar_lead'} onChange={() => setPostSubmit('criar_lead')} />
                  <div><div className="t">Criar empresa/lead automaticamente</div><div className="d">Só funciona se o campo &quot;Empresa&quot; estiver selecionado acima.</div></div>
                </label>
                <label className="radio-item">
                  <input type="radio" checked={postSubmit === 'so_registrar'} onChange={() => setPostSubmit('so_registrar')} />
                  <div><div className="t">Só registrar a resposta</div><div className="d">Fica disponível para revisão manual, sem criar nada no CRM.</div></div>
                </label>
              </div>
            </div>

            <div className="f-group">
              <label className="f-label">Status</label>
              <select className="f-select" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="rascunho">Rascunho</option>
                <option value="ativo">Ativo</option>
                <option value="pausado">Pausado</option>
              </select>
            </div>

            {error && <p className="state-msg error">Não foi possível salvar. Confira os dados e tente de novo.</p>}
          </div>
          <div className="drawer-foot">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar formulário'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function CanvasField({ field, locked, type, fullWidth, dragOver, onDragStart, onDragOver, onDragLeave, onDrop, onRemove }) {
  return (
    <div
      className={`canvas-field${fullWidth ? ' full' : ''}${dragOver ? ' drag-over' : ''}`}
      draggable={!locked}
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <label>
        {field.label}
        {locked && <span className="lock-icon" title="Sempre presente e obrigatório">🔒</span>}
      </label>
      {type === 'textarea' ? (
        <textarea disabled />
      ) : type === 'boolean' ? (
        <select disabled><option>Selecione</option><option>Sim</option><option>Não</option></select>
      ) : (
        <input type={type === 'email' ? 'email' : 'text'} disabled />
      )}
      {!locked && (
        <div className="field-tools">
          <span className="drag-handle" title="Arrastar para reordenar">⠿</span>
          <span className="remove-btn" title="Remover campo" onClick={onRemove}>✕</span>
        </div>
      )}
    </div>
  )
}

function EmbedModal({ form, onClose }) {
  const apiRoot = window.location.origin.replace(/:\d+$/, ':8001') + '/api/v1'
  const snippet = `<script src="${apiRoot}/embed/form.js?form_id=${form.id}"></script>`

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()} style={{ width: 'min(520px, calc(100vw - 32px))' }}>
        <h3>Código de incorporação</h3>
        <p className="sub">Cole este trecho na página &quot;{form.pagina || form.nome}&quot; do site institucional.</p>
        <pre className="embed-code">{snippet}</pre>
        <div className="row">
          <button className="btn-ghost" onClick={onClose}>Fechar</button>
          <button className="btn-primary" onClick={() => navigator.clipboard.writeText(snippet)}>Copiar</button>
        </div>
      </div>
    </div>
  )
}

function RastreioTab({ companiesQuery }) {
  const tenantQuery = useQuery({ queryKey: ['tenant'], queryFn: getTenant, staleTime: Infinity })
  const kpisQuery = useQuery({ queryKey: ['site-visits', 'kpis'], queryFn: getSiteVisitsKpis })
  const dailyQuery = useQuery({ queryKey: ['site-visits', 'daily'], queryFn: () => getDailySessions(14) })
  const pagesQuery = useQuery({ queryKey: ['site-visits', 'pages'], queryFn: () => getTopPages(30, 10) })

  const k = kpisQuery.data
  const daily = dailyQuery.data ?? []
  const maxSessoes = Math.max(1, ...daily.map((d) => d.sessoes))

  return (
    <div className="tab-content-stack">
      {tenantQuery.data && (
        <div className="card tracking-snippet-card">
          <div className="card-head"><div><h3>Snippet de rastreio</h3><p>Cole antes do <code>&lt;/body&gt;</code> de todas as páginas do site institucional</p></div></div>
          <div style={{ padding: '0 18px 16px' }}>
            <pre className="embed-code">{`<script src="${window.location.origin.replace(/:\d+$/, ':8001')}/api/v1/embed/track.js" data-tenant-id="${tenantQuery.data.id}"></script>`}</pre>
          </div>
        </div>
      )}

      {k && (
        <div className="kpi-row">
          <div className="kpi-card">
            <div className="label">Visitas (30 dias)</div><div className="value">{k.visitas_30d}</div>
            {k.visitas_delta_pct != null && (
              <div className={`delta ${k.visitas_delta_pct >= 0 ? 'up' : 'down'}`}>{k.visitas_delta_pct >= 0 ? '+' : ''}{k.visitas_delta_pct}% <span className="vs">vs. período anterior</span></div>
            )}
          </div>
          <div className="kpi-card"><div className="label">Empresas identificadas</div><div className="value">{k.empresas_identificadas}</div><div className="note">com pelo menos 1 visita</div></div>
          <div className="kpi-card"><div className="label">Taxa de identificação</div><div className="value">{k.taxa_identificacao_pct}%</div><div className="note">das sessões, por rede corporativa</div></div>
          <div className="kpi-card"><div className="label">Negócios abertos do site</div><div className="value">{k.negocios_abertos_30d}</div><div className="note">nos últimos 30 dias</div></div>
        </div>
      )}

      <div className="card">
        <div className="card-head"><div><h3>Sessões por dia</h3><p>Últimos 14 dias</p></div></div>
        <div className="chart-wrap">
          {daily.length === 0 ? (
            <p className="state-msg">Sem dados de tráfego ainda — instale o snippet acima no site.</p>
          ) : (
            <div className="bar-chart">
              {daily.map((d) => (
                <div className="bar-chart-col" key={d.dia} title={`${d.dia}: ${d.sessoes} sessões`}>
                  <div className="bar-chart-bar" style={{ height: `${(d.sessoes / maxSessoes) * 100}%` }} />
                  <div className="bar-chart-label">{d.dia.slice(8, 10)}/{d.dia.slice(5, 7)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid-main">
        <div className="card">
          <div className="card-head"><div><h3>Empresas identificadas recentemente</h3><p>Correspondência por rede/IP corporativo</p></div></div>
          <div className="table-scroll">
            <table className="data">
              <thead><tr><th>Empresa</th><th>Página</th><th>Origem</th><th>Última visita</th><th>No CRM</th></tr></thead>
              <tbody>
                {(companiesQuery.data ?? []).map((c, i) => {
                  const badge = c.company_status ? CO_BADGE[c.company_status] : { label: 'Não cadastrada', cls: 'new' }
                  return (
                    <tr key={i}>
                      <td><div className="row-title">{c.empresa}</div></td>
                      <td className="row-sub">{c.path}</td>
                      <td className="source-cell">{c.origem}</td>
                      <td className="row-sub">{timeAgo(c.ultima_visita)}</td>
                      <td><span className={`co-badge ${badge.cls}`}>{badge.label}</span></td>
                    </tr>
                  )
                })}
                {companiesQuery.data && companiesQuery.data.length === 0 && (
                  <tr><td colSpan={5}><p className="state-msg">Nenhuma empresa identificada ainda.</p></td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div style={{ padding: '12px 18px 18px' }}>
            <div className="caveat">
              Só é possível identificar a empresa quando a visita parte de uma rede corporativa com IP conhecido. A maior parte das visitas
              (redes residenciais e móveis) permanece anônima — por isso a taxa de identificação é baixa mesmo com bom volume de tráfego.
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-head"><div><h3>Páginas mais visitadas</h3><p>Últimos 30 dias</p></div></div>
          <div className="page-list">
            {(pagesQuery.data ?? []).map((p) => (
              <div className="page-row" key={p.path}>
                <span className="path">{p.path}</span>
                <span className="views">{p.visualizacoes}</span>
              </div>
            ))}
            {pagesQuery.data && pagesQuery.data.length === 0 && <p className="state-msg">Sem dados ainda.</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
