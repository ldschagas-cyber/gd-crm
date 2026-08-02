import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createCompany, deleteCompany, exportCompanies, getCompanyFilterOptions, getImportJob,
  importCompanies, listCompanies, setCompanyStatus, updateCompany,
} from '../api/companies'
import { listUsers } from '../api/users'
import EnrollModal from '../components/EnrollModal.jsx'
import '../styles/dataTable.css'
import './EmpresasPage.css'

const STATUS_LABEL = {
  lead: 'Lead',
  qualificado: 'Qualificado',
  cliente: 'Cliente',
  perdido: 'Perdido',
  inativo: 'Inativo',
}
const STATUS_ORDER = ['lead', 'qualificado', 'cliente', 'perdido', 'inativo']
const SETORES = ['Farma', 'Alimentos', 'Autopeças', 'Etiquetas', 'Plástico', 'Máquinas e Equipamentos',
  'Química', 'Cosmético', 'Serviços', 'Tecnologia', 'Varejo', 'Outro']

const COLUMN_DEFS = [
  { key: 'segmento', label: 'Segmento', default: true },
  { key: 'cidade_uf', label: 'Cidade/UF', default: true },
  { key: 'responsavel', label: 'Responsável', default: true },
  { key: 'status', label: 'Status', default: true },
  { key: 'telefone', label: 'Telefone', default: false },
  { key: 'email', label: 'E-mail', default: false },
  { key: 'porte', label: 'Porte', default: false },
  { key: 'num_funcionarios', label: 'Funcionários', default: false },
  { key: 'faturamento_estimado', label: 'Faturamento estimado', default: false },
  { key: 'origem', label: 'Origem', default: false },
]

const PAGE_SIZE = 20
const KANBAN_SIZE = 100 // teto de `PageParams.size` no backend (le=100)

export default function EmpresasPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [status, setStatus] = useState('')
  const [uf, setUf] = useState('')
  const [responsavelId, setResponsavelId] = useState('')
  const [segmento, setSegmento] = useState('')
  const [porte, setPorte] = useState('')
  const [origem, setOrigem] = useState('')
  const [view, setView] = useState('list')
  const [visibleColumns, setVisibleColumns] = useState(() =>
    Object.fromEntries(COLUMN_DEFS.map((c) => [c.key, c.default])),
  )
  const [showColumnsPopover, setShowColumnsPopover] = useState(false)
  const [selected, setSelected] = useState({})
  const [modalCompany, setModalCompany] = useState(undefined) // undefined = fechado, null = criar, obj = editar
  const [showImportDrawer, setShowImportDrawer] = useState(false)
  const [showBulkEnroll, setShowBulkEnroll] = useState(false)

  const queryClient = useQueryClient()
  const filters = {
    busca: busca || undefined, status: status || undefined, uf: uf || undefined,
    responsavelId: responsavelId || undefined, segmento: segmento || undefined,
    porte: porte || undefined, origem: origem || undefined,
  }

  const usersQuery = useQuery({
    queryKey: ['users', 'for-assign'],
    queryFn: () => listUsers({ size: 100 }),
    retry: false,
  })
  const usersById = Object.fromEntries((usersQuery.data?.items ?? []).map((u) => [u.id, u.nome]))

  const filterOptionsQuery = useQuery({ queryKey: ['companies', 'filter-options'], queryFn: getCompanyFilterOptions })
  const filterOptions = filterOptionsQuery.data ?? { segmento: [], porte: [], origem: [], uf: [] }

  const listQuery = useQuery({
    queryKey: ['companies', 'list', { page, ...filters }],
    queryFn: () => listCompanies({ page, size: PAGE_SIZE, ...filters }),
    enabled: view === 'list',
    placeholderData: keepPreviousData,
  })

  const kanbanQuery = useQuery({
    queryKey: ['companies', 'kanban', filters],
    queryFn: () => listCompanies({ page: 1, size: KANBAN_SIZE, ...filters }),
    enabled: view === 'kanban',
  })

  function invalidateCompanies() {
    queryClient.invalidateQueries({ queryKey: ['companies'] })
  }

  const createMutation = useMutation({
    mutationFn: createCompany,
    onSuccess: () => { setModalCompany(undefined); invalidateCompanies() },
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updateCompany(id, data),
    onSuccess: () => { setModalCompany(undefined); invalidateCompanies() },
  })
  const statusMutation = useMutation({
    mutationFn: ({ id, status: s }) => setCompanyStatus(id, s),
    onSuccess: invalidateCompanies,
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
    if (!confirm(`Excluir ${selectedIds.length} empresa(s) selecionada(s)?`)) return
    await Promise.all(selectedIds.map((id) => deleteCompany(id)))
    setSelected({})
    invalidateCompanies()
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Empresas</h1>
          <p>{total.toLocaleString('pt-BR')} cadastradas neste tenant</p>
        </div>
        <div className="page-actions">
          <button className="btn-ghost" onClick={() => setShowImportDrawer(true)}>
            <IconImport /> Importar
          </button>
          <button className="btn-ghost" onClick={() => exportCompanies(filters)}>
            <IconExport /> Exportar
          </button>
          <button className="btn-primary" onClick={() => setModalCompany(null)}>
            <IconPlus /> Nova empresa
          </button>
        </div>
      </header>

      <div className="content">
        <div className="filters-bar">
          <div className="search">
            <input
              type="text"
              placeholder="Buscar por razão social ou CNPJ"
              value={busca}
              onChange={handleFilterChange(setBusca)}
            />
          </div>
          <select className="filter-select" value={status} onChange={handleFilterChange(setStatus)}>
            <option value="">Todos os status</option>
            {Object.entries(STATUS_LABEL).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <select className="filter-select uf-input" value={uf} onChange={handleFilterChange(setUf)}>
            <option value="">Todas as UFs</option>
            {filterOptions.uf.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
          <select className="filter-select" value={responsavelId} onChange={handleFilterChange(setResponsavelId)}>
            <option value="">Todos os responsáveis</option>
            {(usersQuery.data?.items ?? []).map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
          <select className="filter-select" value={segmento} onChange={handleFilterChange(setSegmento)}>
            <option value="">Todos os segmentos</option>
            {filterOptions.segmento.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
          <select className="filter-select" value={porte} onChange={handleFilterChange(setPorte)}>
            <option value="">Todos os portes</option>
            {filterOptions.porte.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
          <select className="filter-select" value={origem} onChange={handleFilterChange(setOrigem)}>
            <option value="">Todas as origens</option>
            {filterOptions.origem.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>

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

          <div className="segmented">
            <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')}>
              <IconList /> Lista
            </button>
            <button className={view === 'kanban' ? 'active' : ''} onClick={() => setView('kanban')}>
              <IconKanban /> Kanban
            </button>
          </div>
        </div>

        {view === 'list' && (
          <div className="card">
            {selectedIds.length > 0 && (
              <div className="bulk-bar show">
                <span><b>{selectedIds.length}</b> selecionadas</span>
                <div className="link-btn">
                  <a onClick={() => setShowBulkEnroll(true)}>Inscrever</a>
                  <a onClick={() => exportCompanies(filters)}>Exportar</a>
                  <a onClick={handleBulkDelete}>Excluir</a>
                </div>
              </div>
            )}

            {listQuery.isLoading && <p className="state-msg">Carregando empresas…</p>}
            {listQuery.isError && <p className="state-msg error">Não foi possível carregar as empresas agora.</p>}

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
                      <th>Empresa</th>
                      {COLUMN_DEFS.filter((c) => visibleColumns[c.key]).map((c) => (
                        <th key={c.key}>{c.label}</th>
                      ))}
                      <th className="actions-col"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((c) => (
                      <tr
                        key={c.id}
                        className={selected[c.id] ? 'row-selected' : ''}
                        onClick={() => navigate(`/empresas/${c.id}`)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td className="checkbox-col" onClick={(e) => e.stopPropagation()}>
                          <input type="checkbox" checked={!!selected[c.id]} onChange={() => toggleSelect(c.id)} />
                        </td>
                        <td>
                          <div className="row-title">{c.razao_social}</div>
                          {c.cnpj && <div className="row-sub">{c.cnpj}</div>}
                        </td>
                        {COLUMN_DEFS.filter((col) => visibleColumns[col.key]).map((col) => (
                          <td key={col.key}>{renderCell(c, col.key, usersById)}</td>
                        ))}
                        <td className="actions-col" onClick={(e) => e.stopPropagation()}>
                          <button className="row-action" title="Editar" onClick={() => setModalCompany(c)}>✎</button>
                        </td>
                      </tr>
                    ))}
                    {items.length === 0 && (
                      <tr>
                        <td colSpan={COLUMN_DEFS.length + 3} className="empty-cell">Nenhuma empresa encontrada.</td>
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
        )}

        {view === 'kanban' && (
          <KanbanBoard
            query={kanbanQuery}
            onDropStatus={(id, s) => statusMutation.mutate({ id, status: s })}
            onOpen={(c) => navigate(`/empresas/${c.id}`)}
          />
        )}
      </div>

      {modalCompany !== undefined && (
        <CompanyModal
          company={modalCompany}
          users={usersQuery.data?.items ?? []}
          usersError={usersQuery.isError}
          onClose={() => setModalCompany(undefined)}
          onSubmit={(data) => {
            if (modalCompany) updateMutation.mutate({ id: modalCompany.id, data })
            else createMutation.mutate(data)
          }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {showImportDrawer && <ImportDrawer onClose={() => setShowImportDrawer(false)} onDone={invalidateCompanies} />}

      {showBulkEnroll && (
        <EnrollModal
          alvos={selectedIds.map((id) => ({ company_id: id }))}
          alvoLabel={`${selectedIds.length} empresa(s) selecionada(s)`}
          onClose={() => setShowBulkEnroll(false)}
          onEnrolled={() => setSelected({})}
        />
      )}
    </>
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
function IconList() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7">
      <path d="M3.5 5.5h13M3.5 10h13M3.5 14.5h13" />
    </svg>
  )
}
function IconKanban() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7">
      <rect x="2.5" y="3" width="4.4" height="14" rx="1" />
      <rect x="7.8" y="3" width="4.4" height="9.5" rx="1" />
      <rect x="13.1" y="3" width="4.4" height="6" rx="1" />
    </svg>
  )
}

function renderCell(c, key, usersById) {
  switch (key) {
    case 'cidade_uf':
      return c.cidade ? `${c.cidade}/${c.uf ?? ''}` : '—'
    case 'status':
      return (
        <span className="co-status-pill" data-status={c.status}>
          <span className="d" />
          {STATUS_LABEL[c.status] ?? c.status}
        </span>
      )
    case 'responsavel':
      return c.responsavel_id ? (usersById[c.responsavel_id] ?? c.responsavel_id.slice(0, 8)) : '—'
    case 'num_funcionarios':
      return c.num_funcionarios != null ? c.num_funcionarios.toLocaleString('pt-BR') : '—'
    case 'faturamento_estimado':
      return c.faturamento_estimado != null
        ? c.faturamento_estimado.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
        : '—'
    default:
      return c[key] ?? '—'
  }
}

function KanbanBoard({ query, onDropStatus, onOpen }) {
  const items = query.data?.items ?? []
  const [dragOverStatus, setDragOverStatus] = useState(null)

  if (query.isLoading) return <p className="state-msg">Carregando…</p>
  if (query.isError) return <p className="state-msg error">Não foi possível carregar o kanban agora.</p>

  return (
    <div className="kanban-scroll">
      <div className="kanban">
        {STATUS_ORDER.map((s) => {
          const inCol = items.filter((c) => c.status === s)
          return (
            <div className="kb-col" key={s}>
              <div className="kb-col-head">
                <div className="kb-col-title">
                  <span className="d" data-status={s} />
                  <span className="name">{STATUS_LABEL[s]}</span>
                </div>
                <span className="kb-col-count">{inCol.length}</span>
              </div>
              <div
                className={`kb-col-body${dragOverStatus === s ? ' drag-over' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragOverStatus(s) }}
                onDragLeave={() => setDragOverStatus(null)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragOverStatus(null)
                  const id = e.dataTransfer.getData('text/company-id')
                  if (id) onDropStatus(id, s)
                }}
              >
                {inCol.map((c) => (
                  <div
                    key={c.id}
                    className="kb-card"
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData('text/company-id', c.id)}
                    onClick={() => onOpen(c)}
                  >
                    <div className="kb-card-name">{c.razao_social}</div>
                    <div className="kb-card-sub">{c.cidade ? `${c.cidade}/${c.uf ?? ''}` : c.segmento ?? ''}</div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function CompanyModal({ company, users, usersError, onClose, onSubmit, submitting, error }) {
  const isEdit = Boolean(company)
  const [form, setForm] = useState({
    razao_social: company?.razao_social ?? '',
    cnpj: company?.cnpj ?? '',
    cidade: company?.cidade ?? '',
    uf: company?.uf ?? '',
    segmento: company?.segmento ?? '',
    setor: company?.setor ?? '',
    site: company?.site ?? '',
    num_funcionarios: company?.num_funcionarios ?? '',
    faturamento_estimado: company?.faturamento_estimado ?? '',
    telefone: company?.telefone ?? '',
    email: company?.email ?? '',
    responsavel_id: company?.responsavel_id ?? '',
  })

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    const payload = Object.fromEntries(
      Object.entries(form).map(([k, v]) => [k, typeof v === 'string' && v.trim() === '' ? null : v]),
    )
    if (payload.num_funcionarios != null) payload.num_funcionarios = parseInt(payload.num_funcionarios, 10)
    if (payload.faturamento_estimado != null) payload.faturamento_estimado = Number(payload.faturamento_estimado)
    if (isEdit) delete payload.status
    else payload.status = company === null ? 'lead' : undefined
    onSubmit(payload)
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{isEdit ? 'Editar empresa' : 'Nova empresa'}</h2>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="razao_social">Razão social *</label>
            <input id="razao_social" required value={form.razao_social} onChange={set('razao_social')} />
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="cnpj">CNPJ</label>
              <input id="cnpj" value={form.cnpj} onChange={set('cnpj')} disabled={isEdit} />
            </div>
            <div className="field">
              <label htmlFor="segmento">Segmento</label>
              <input id="segmento" value={form.segmento} onChange={set('segmento')} />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="setor">Setor <span className="hint-text">(define o Score ICP)</span></label>
              <select id="setor" value={form.setor} onChange={set('setor')}>
                <option value="">Selecione…</option>
                {SETORES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="site">Site</label>
              <input id="site" value={form.site} onChange={set('site')} placeholder="https://..." />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="cidade">Cidade</label>
              <input id="cidade" value={form.cidade} onChange={set('cidade')} />
            </div>
            <div className="field field-small">
              <label htmlFor="uf">UF</label>
              <input id="uf" maxLength={2} value={form.uf} onChange={(e) => setForm((f) => ({ ...f, uf: e.target.value.toUpperCase() }))} />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="num_funcionarios">Funcionários</label>
              <input id="num_funcionarios" type="number" min="0" value={form.num_funcionarios} onChange={set('num_funcionarios')} />
            </div>
            <div className="field">
              <label htmlFor="faturamento_estimado">Faturamento estimado</label>
              <input id="faturamento_estimado" type="number" min="0" step="0.01" value={form.faturamento_estimado} onChange={set('faturamento_estimado')} />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="telefone">Telefone</label>
              <input id="telefone" value={form.telefone} onChange={set('telefone')} />
            </div>
            <div className="field">
              <label htmlFor="email">E-mail</label>
              <input id="email" type="email" value={form.email} onChange={set('email')} />
            </div>
          </div>
          <div className="field">
            <label htmlFor="responsavel_id">Responsável</label>
            {usersError ? (
              <p className="hint-text">Só administradores podem ver a lista de usuários.</p>
            ) : (
              <select id="responsavel_id" value={form.responsavel_id ?? ''} onChange={set('responsavel_id')}>
                <option value="">Sem responsável</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.nome}</option>
                ))}
              </select>
            )}
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
    mutationFn: importCompanies,
    onSuccess: (data) => setJob(data),
    onError: () => setError('Não foi possível enviar o arquivo.'),
  })

  const pollQuery = useQuery({
    queryKey: ['import-job', job?.id],
    queryFn: () => getImportJob(job.id),
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
            <h2>Importar empresas</h2>
            <p>Envie um .csv ou .xlsx — processado em segundo plano pelo worker</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          <div className="import-cols">
            Colunas esperadas: <code>razao_social*</code> <code>cnpj*</code> <code>cidade*</code> <code>uf*</code>{' '}
            <code>segmento</code> <code>telefone</code> <code>email</code> <code>porte</code>{' '}
            <code>funcionarios</code> <code>faturamento</code> <code>origem</code>
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
              <div className="summary-tile ok"><div className="v">{job.importadas ?? '—'}</div><div className="t">Importadas</div></div>
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
