import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createContact, deleteContact, exportContacts, getContactFilterOptions, getContactImportJob,
  importContacts, listContacts, updateContact,
} from '../api/contacts'
import { listCompanies } from '../api/companies'
import EnrollModal from '../components/EnrollModal.jsx'
import '../styles/dataTable.css'
import './ContatosPage.css'

const COLUMN_DEFS = [
  { key: 'cargo', label: 'Cargo', default: true },
  { key: 'empresa', label: 'Empresa', default: true },
  { key: 'data_nascimento', label: 'Aniversário', default: true },
  { key: 'email', label: 'E-mail', default: false },
  { key: 'observacoes', label: 'Observações', default: false },
]

const PAGE_SIZE = 20

export default function ContatosPage() {
  const [searchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [companyId, setCompanyId] = useState(() => searchParams.get('empresa') ?? '')
  const [cargo, setCargo] = useState('')
  const [temWhatsapp, setTemWhatsapp] = useState(false)
  const [visibleColumns, setVisibleColumns] = useState(() =>
    Object.fromEntries(COLUMN_DEFS.map((c) => [c.key, c.default])),
  )
  const [showColumnsPopover, setShowColumnsPopover] = useState(false)
  const [selected, setSelected] = useState({})
  const [modalContact, setModalContact] = useState(undefined) // undefined = fechado, null = criar, obj = editar
  const [showImportDrawer, setShowImportDrawer] = useState(false)
  const [showBulkEnroll, setShowBulkEnroll] = useState(false)

  const queryClient = useQueryClient()
  const filters = {
    busca: busca || undefined, companyId: companyId || undefined,
    cargo: cargo || undefined, temWhatsapp: temWhatsapp || undefined,
  }

  const companiesQuery = useQuery({
    queryKey: ['companies', 'for-select'],
    queryFn: () => listCompanies({ size: 100 }),
  })
  const companies = companiesQuery.data?.items ?? []
  const companiesById = Object.fromEntries(companies.map((c) => [c.id, c.razao_social]))

  const filterOptionsQuery = useQuery({ queryKey: ['contacts', 'filter-options'], queryFn: getContactFilterOptions })
  const filterOptions = filterOptionsQuery.data ?? { cargo: [] }

  const listQuery = useQuery({
    queryKey: ['contacts', 'list', { page, ...filters }],
    queryFn: () => listContacts({ page, size: PAGE_SIZE, ...filters }),
    placeholderData: keepPreviousData,
  })

  function invalidateContacts() {
    queryClient.invalidateQueries({ queryKey: ['contacts'] })
  }

  const createMutation = useMutation({
    mutationFn: createContact,
    onSuccess: () => { setModalContact(undefined); invalidateContacts() },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updateContact(id, data),
    onSuccess: () => { setModalContact(undefined); invalidateContacts() },
  })
  const total = listQuery.data?.total ?? 0
  const items = listQuery.data?.items ?? []
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const selectedIds = Object.keys(selected).filter((id) => selected[id])

  function handleFilterChange(setter) {
    return (e) => { setter(e.target.value); setPage(1) }
  }

  function toggleSelect(id) {
    setSelected((s) => ({ ...s, [id]: !s[id] }))
  }

  function toggleSelectAll() {
    const allSelected = items.length > 0 && items.every((c) => selected[c.id])
    const next = {}
    if (!allSelected) items.forEach((c) => { next[c.id] = true })
    setSelected(next)
  }

  async function handleBulkDelete() {
    if (!confirm(`Excluir ${selectedIds.length} contato(s) selecionado(s)?`)) return
    await Promise.all(selectedIds.map((id) => deleteContact(id)))
    setSelected({})
    invalidateContacts()
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Contatos</h1>
          <p>{total.toLocaleString('pt-BR')} cadastrados neste tenant</p>
        </div>
        <div className="page-actions">
          <button className="btn-ghost" onClick={() => setShowImportDrawer(true)}>
            <IconImport /> Importar
          </button>
          <button className="btn-ghost" onClick={() => exportContacts(filters)}>
            <IconExport /> Exportar
          </button>
          <button className="btn-primary" onClick={() => setModalContact(null)}>
            <IconPlus /> Novo contato
          </button>
        </div>
      </header>

      <div className="content">
        <div className="filters-bar">
          <div className="search">
            <input
              type="text"
              placeholder="Nome, cargo ou e-mail"
              value={busca}
              onChange={handleFilterChange(setBusca)}
            />
          </div>
          <select className="filter-select" value={companyId} onChange={handleFilterChange(setCompanyId)}>
            <option value="">Todas as empresas</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>{c.razao_social}</option>
            ))}
          </select>
          <select className="filter-select" value={cargo} onChange={handleFilterChange(setCargo)}>
            <option value="">Todos os cargos</option>
            {filterOptions.cargo.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
          <label className="chip-toggle">
            <input type="checkbox" checked={temWhatsapp} onChange={(e) => { setTemWhatsapp(e.target.checked); setPage(1) }} />
            Tem WhatsApp
          </label>

          <div className="columns-btn-wrap">
            <button className="btn-ghost" onClick={() => setShowColumnsPopover((v) => !v)}>
              <IconColumns /> Colunas
            </button>
            {showColumnsPopover && (
              <div className="popover show">
                <div className="popover-head">Mostrar colunas</div>
                {COLUMN_DEFS.map((col) => (
                  <label className="col-option" key={col.key}>
                    <input
                      type="checkbox"
                      checked={visibleColumns[col.key]}
                      onChange={(e) => setVisibleColumns((v) => ({ ...v, [col.key]: e.target.checked }))}
                    />
                    {col.label}
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="card">
          {selectedIds.length > 0 && (
            <div className="bulk-bar show">
              <span><b>{selectedIds.length}</b> selecionados</span>
              <div className="link-btn">
                <a onClick={() => setShowBulkEnroll(true)}>Inscrever</a>
                <a onClick={() => exportContacts(filters)}>Exportar</a>
                <a onClick={handleBulkDelete}>Excluir</a>
              </div>
            </div>
          )}

          {listQuery.isLoading && <p className="state-msg">Carregando contatos…</p>}
          {listQuery.isError && <p className="state-msg error">Não foi possível carregar os contatos agora.</p>}

          {listQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th className="checkbox-col">
                      <input
                        type="checkbox"
                        checked={items.length > 0 && items.every((c) => selected[c.id])}
                        onChange={toggleSelectAll}
                      />
                    </th>
                    <th>Contato</th>
                    <th>Contato rápido</th>
                    {COLUMN_DEFS.filter((c) => visibleColumns[c.key]).map((c) => (
                      <th key={c.key}>{c.label}</th>
                    ))}
                    <th className="actions-col"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((c) => (
                    <tr key={c.id} className={selected[c.id] ? 'row-selected' : ''}>
                      <td className="checkbox-col">
                        <input type="checkbox" checked={!!selected[c.id]} onChange={() => toggleSelect(c.id)} />
                      </td>
                      <td>
                        <div className="row-title">{c.nome}</div>
                        {c.email && <div className="row-sub">{c.email}</div>}
                      </td>
                      <td><QuickContact contact={c} /></td>
                      {COLUMN_DEFS.filter((col) => visibleColumns[col.key]).map((col) => (
                        <td key={col.key}>{renderCell(c, col.key, companiesById)}</td>
                      ))}
                      <td className="actions-col">
                        <button className="row-action" title="Editar" onClick={() => setModalContact(c)}>✎</button>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr>
                      <td colSpan={COLUMN_DEFS.length + 4} className="empty-cell">Nenhum contato encontrado.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          <div className="pagination">
            <span className="info">
              {total > 0
                ? `mostrando ${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, total)} de ${total.toLocaleString('pt-BR')}`
                : 'sem resultados'}
            </span>
            <div className="controls">
              <button className="page-btn" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>‹</button>
              <button className="page-btn" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>›</button>
            </div>
          </div>
        </div>
      </div>

      {modalContact !== undefined && (
        <ContactModal
          contact={modalContact}
          companies={companies}
          onClose={() => setModalContact(undefined)}
          onSubmit={(data) => {
            if (modalContact) updateMutation.mutate({ id: modalContact.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {showImportDrawer && <ImportDrawer onClose={() => setShowImportDrawer(false)} onDone={invalidateContacts} />}

      {showBulkEnroll && (
        <EnrollModal
          alvos={selectedIds.map((id) => ({ contact_id: id }))}
          alvoLabel={`${selectedIds.length} contato(s) selecionado(s)`}
          onClose={() => setShowBulkEnroll(false)}
          onEnrolled={() => setSelected({})}
        />
      )}
    </>
  )
}

function renderCell(c, key, companiesById) {
  switch (key) {
    case 'empresa':
      return companiesById[c.company_id] ?? '—'
    case 'data_nascimento':
      return c.data_nascimento ? new Date(c.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR') : '—'
    default:
      return c[key] ?? '—'
  }
}

function onlyDigits(v) {
  return (v || '').replace(/\D/g, '')
}

function QuickContact({ contact }) {
  return (
    <div className="quick-contact">
      {contact.telefone ? (
        <a href={`tel:${onlyDigits(contact.telefone)}`} title={`Ligar: ${contact.telefone}`} onClick={(e) => e.stopPropagation()}>
          <IconPhone />
        </a>
      ) : <span className="qc-empty"><IconPhone /></span>}
      {contact.whatsapp ? (
        <a href={`https://wa.me/55${onlyDigits(contact.whatsapp)}`} target="_blank" rel="noopener noreferrer"
           title={`WhatsApp: ${contact.whatsapp}`} onClick={(e) => e.stopPropagation()}>
          <IconWhatsapp />
        </a>
      ) : <span className="qc-empty"><IconWhatsapp /></span>}
      {contact.linkedin ? (
        <a href={contact.linkedin.startsWith('http') ? contact.linkedin : `https://${contact.linkedin}`}
           target="_blank" rel="noopener noreferrer" title="Abrir LinkedIn" onClick={(e) => e.stopPropagation()}>
          <IconLinkedin />
        </a>
      ) : <span className="qc-empty"><IconLinkedin /></span>}
    </div>
  )
}

export function ContactModal({ contact, companies, onClose, onSubmit, submitting, error }) {
  const isEdit = Boolean(contact?.id)
  const [form, setForm] = useState({
    company_id: contact?.company_id ?? '',
    nome: contact?.nome ?? '',
    cargo: contact?.cargo ?? '',
    email: contact?.email ?? '',
    telefone: contact?.telefone ?? '',
    whatsapp: contact?.whatsapp ?? '',
    linkedin: contact?.linkedin ?? '',
    data_nascimento: contact?.data_nascimento ?? '',
    observacoes: contact?.observacoes ?? '',
  })

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    const payload = Object.fromEntries(
      Object.entries(form).map(([k, v]) => [k, typeof v === 'string' && v.trim() === '' ? null : v]),
    )
    if (isEdit) delete payload.company_id
    onSubmit(payload)
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{isEdit ? 'Editar contato' : 'Novo contato'}</h2>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="company_id">Empresa *</label>
            <select id="company_id" required value={form.company_id} onChange={set('company_id')} disabled={isEdit}>
              <option value="" disabled>Selecione a empresa</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{c.razao_social}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="nome">Nome completo *</label>
            <input id="nome" required value={form.nome} onChange={set('nome')} />
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="cargo">Cargo</label>
              <input id="cargo" value={form.cargo} onChange={set('cargo')} />
            </div>
            <div className="field">
              <label htmlFor="email">E-mail</label>
              <input id="email" type="email" value={form.email} onChange={set('email')} />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="telefone">Telefone</label>
              <input id="telefone" value={form.telefone} onChange={set('telefone')} />
            </div>
            <div className="field">
              <label htmlFor="whatsapp">WhatsApp</label>
              <input id="whatsapp" value={form.whatsapp} onChange={set('whatsapp')} />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="linkedin">LinkedIn</label>
              <input id="linkedin" value={form.linkedin} onChange={set('linkedin')} placeholder="linkedin.com/in/…" />
            </div>
            <div className="field">
              <label htmlFor="data_nascimento">Aniversário</label>
              <input id="data_nascimento" type="date" value={form.data_nascimento ?? ''} onChange={set('data_nascimento')} />
            </div>
          </div>
          <div className="field">
            <label htmlFor="observacoes">Observações</label>
            <textarea id="observacoes" rows={3} value={form.observacoes} onChange={set('observacoes')} />
          </div>

          {error && <p className="state-msg error">Não foi possível salvar. Confira os dados e tente de novo.</p>}

          <div className="modal-actions">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? 'Salvando…' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ImportDrawer({ onClose, onDone }) {
  const [file, setFile] = useState(null)
  const [job, setJob] = useState(null)
  const [error, setError] = useState(null)

  const uploadMutation = useMutation({
    mutationFn: importContacts,
    onSuccess: (data) => setJob(data),
    onError: () => setError('Não foi possível enviar o arquivo.'),
  })

  const pollQuery = useQuery({
    queryKey: ['contact-import-job', job?.id],
    queryFn: () => getContactImportJob(job.id),
    enabled: Boolean(job) && job.status !== 'concluido' && job.status !== 'erro',
    refetchInterval: 1200,
  })

  useEffect(() => {
    if (!pollQuery.data) return
    setJob(pollQuery.data)
    if (pollQuery.data.status === 'concluido') onDone()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollQuery.data])

  function handleFileChange(e) {
    const f = e.target.files?.[0]
    setFile(f ?? null)
    setJob(null)
    setError(null)
  }

  function handleConfirm() {
    if (file) uploadMutation.mutate(file)
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>Importar contatos</h2>
            <p>A coluna "empresa" deve trazer o CNPJ (já cadastrado) — processado em segundo plano</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          <div className="import-cols">
            Colunas esperadas: <code>nome*</code> <code>empresa*</code> <code>cargo</code>{' '}
            <code>email</code> <code>telefone</code> <code>whatsapp</code> <code>linkedin</code>{' '}
            <code>data_nascimento</code> <code>observacoes</code>
          </div>

          <label className="drop-zone">
            <div className="dz-title">{file ? file.name : 'Clique para escolher um arquivo'}</div>
            <div className="dz-sub">.csv ou .xlsx</div>
            <input type="file" accept=".csv,.xlsx" onChange={handleFileChange} />
          </label>

          {error && <p className="state-msg error">{error}</p>}

          {job && (
            <div className="import-summary">
              <div className="summary-tile"><div className="v">{job.status}</div><div className="t">Status</div></div>
              <div className="summary-tile"><div className="v">{job.total_linhas ?? '—'}</div><div className="t">Linhas</div></div>
              <div className="summary-tile ok"><div className="v">{job.importadas ?? '—'}</div><div className="t">Importados</div></div>
              <div className="summary-tile erro"><div className="v">{job.erros?.length ?? 0}</div><div className="t">Com erro</div></div>
            </div>
          )}
          {job?.erros?.length > 0 && (
            <div className="import-results">
              {job.erros.map((e, i) => (
                <div className="import-row" key={i}>
                  <span className="ln">L{e.linha ?? '?'}</span>
                  <span className="motivo">{e.motivo}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="drawer-foot">
          <button className="btn-ghost" onClick={onClose}>Fechar</button>
          <button
            className="btn-primary"
            disabled={!file || uploadMutation.isPending || (job && job.status !== 'concluido' && job.status !== 'erro')}
            onClick={handleConfirm}
          >
            {uploadMutation.isPending ? 'Enviando…' : 'Enviar'}
          </button>
        </div>
      </div>
    </div>
  )
}

function IconImport() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7">
      <path d="M10 13.5V4M6.3 7.7L10 4l3.7 3.7" />
      <path d="M4 15.5h12" />
    </svg>
  )
}
function IconExport() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7">
      <path d="M10 4v9.5M6.3 10.2L10 13.9l3.7-3.7" />
      <path d="M4 15.5h12" />
    </svg>
  )
}
function IconPlus() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10 4v12M4 10h12" />
    </svg>
  )
}
function IconColumns() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7">
      <rect x="2.5" y="3.5" width="15" height="13" rx="1.8" />
      <path d="M8.2 3.5v13M13 3.5v13" />
    </svg>
  )
}
function IconPhone() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M5.5 3.5c.6 0 1.1.4 1.3 1l.7 1.9c.2.5 0 1-.3 1.3l-1 .9c.6 1.6 1.9 2.9 3.5 3.5l.9-1c.3-.3.9-.5 1.3-.3l1.9.7c.6.2 1 .7 1 1.3v1.7c0 .8-.7 1.4-1.5 1.3-6-.6-9.6-4.2-10.2-10.2-.1-.8.5-1.5 1.3-1.5z" />
    </svg>
  )
}
function IconWhatsapp() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2a10 10 0 00-8.6 15.1L2 22l5.1-1.3A10 10 0 1012 2zm0 18.2a8.1 8.1 0 01-4.1-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8.1 8.1 0 1112 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1s-.6.8-.8 1c-.1.2-.3.2-.5.1a6.6 6.6 0 01-2-1.2 7.4 7.4 0 01-1.4-1.7c-.1-.2 0-.4.1-.5l.4-.4c.1-.1.2-.3.2-.4a.5.5 0 000-.5c-.1-.1-.6-1.5-.9-2-.2-.5-.5-.4-.6-.4h-.5a1 1 0 00-.7.3 3 3 0 00-.9 2.2c0 1.3.9 2.6 1.1 2.8.1.2 2 3 4.8 4.2.7.3 1.2.5 1.6.6a3.9 3.9 0 001.8.1c.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2-.1-.1-.2-.2-.4-.3z" />
    </svg>
  )
}
function IconLinkedin() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M6.94 5a1.94 1.94 0 11-3.88 0 1.94 1.94 0 013.88 0zM3.34 8.75h3.2V21h-3.2zM9.9 8.75h3.07v1.68h.04c.43-.8 1.47-1.65 3.02-1.65 3.23 0 3.83 2.13 3.83 4.9V21h-3.2v-5.62c0-1.34-.02-3.06-1.87-3.06-1.87 0-2.15 1.46-2.15 2.97V21H9.9z" />
    </svg>
  )
}
