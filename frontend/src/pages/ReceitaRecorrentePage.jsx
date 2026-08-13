import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext.jsx'
import { listCompanies } from '../api/companies'
import { listUsers } from '../api/users'
import { getRevenueResumo, getRevenueWaterfall } from '../api/revenue'
import {
  atualizarValorAssinatura, cancelarAssinatura, createAssinatura, listAssinaturas,
  listEventosAssinatura, reativarAssinatura,
} from '../api/subscriptions'
import '../styles/dataTable.css'
import './ReceitaRecorrentePage.css'

const GESTAO_PERFIS = new Set(['admin', 'gestor'])
const STATUS_LABEL = { ativa: 'Ativa', pausada: 'Pausada', cancelada: 'Cancelada' }
const CICLO_LABEL = { mensal: 'Mensal', anual: 'Anual' }
const EVENTO_LABEL = {
  nova: 'Nova assinatura', expansao: 'Expansão', contracao: 'Contração',
  cancelamento: 'Cancelamento', reativacao: 'Reativação',
}
const PLANOS_SUGERIDOS = ['Governança Premium', 'Governança Essencial', 'Auditoria de Fretes']

function formatCurrency(v) {
  return (v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}
function formatDateBR(d) {
  return d ? new Date(`${d}T00:00:00`).toLocaleDateString('pt-BR') : '—'
}
function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}
function apiErrorMessage(error, fallback) {
  return error?.response?.data?.error?.message ?? fallback
}

export default function ReceitaRecorrentePage() {
  const { user } = useAuth()
  const isGestao = GESTAO_PERFIS.has(user?.perfil)
  const queryClient = useQueryClient()
  const [periodo, setPeriodo] = useState('mes')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [respFilter, setRespFilter] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [openId, setOpenId] = useState(null)

  // Indicadores agregados (MRR/ARR/Churn/NRR) são dado de carteira, restrito a admin/gestor
  // no backend — mesmo guard de /dashboards/commercial (ver app/api/v1/revenue.py). A tabela
  // de assinaturas abaixo continua aberta a todo mundo, como Negócios.
  const resumoQuery = useQuery({
    queryKey: ['receita-recorrente', 'resumo', periodo],
    queryFn: () => getRevenueResumo(periodo),
    enabled: isGestao,
  })
  const waterfallQuery = useQuery({
    queryKey: ['receita-recorrente', 'waterfall'],
    queryFn: () => getRevenueWaterfall(6),
    enabled: isGestao,
  })
  const assinaturasQuery = useQuery({ queryKey: ['assinaturas', 'list'], queryFn: () => listAssinaturas() })
  const companiesQuery = useQuery({ queryKey: ['companies', 'for-select'], queryFn: () => listCompanies({ size: 100 }) })
  const usersQuery = useQuery({ queryKey: ['users', 'for-assign'], queryFn: () => listUsers({ size: 100 }), retry: false })

  const companies = companiesQuery.data?.items ?? []
  const companiesById = Object.fromEntries(companies.map((c) => [c.id, c.razao_social]))
  const users = usersQuery.data?.items ?? []
  const usersById = Object.fromEntries(users.map((u) => [u.id, u.nome]))

  function invalidateAll() {
    queryClient.invalidateQueries({ queryKey: ['receita-recorrente'] })
    queryClient.invalidateQueries({ queryKey: ['assinaturas'] })
  }

  const createMutation = useMutation({
    mutationFn: createAssinatura,
    onSuccess: () => { setShowNew(false); invalidateAll() },
  })

  const assinaturas = assinaturasQuery.data ?? []
  const filtered = assinaturas
    .filter((a) => {
      if (statusFilter && a.status !== statusFilter) return false
      if (respFilter && a.responsavel_id !== respFilter) return false
      if (search) {
        const hay = `${companiesById[a.company_id] ?? ''} ${a.nome_plano}`.toLowerCase()
        if (!hay.includes(search.toLowerCase())) return false
      }
      return true
    })
    .sort((a, b) => {
      if (a.status !== b.status) return a.status === 'ativa' ? -1 : 1
      return b.valor_mensal - a.valor_mensal
    })

  const resumo = resumoQuery.data
  const openAssinatura = assinaturas.find((a) => a.id === openId) ?? null

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Receita Recorrente</h1>
          <p>MRR, ARR, churn e expansão da carteira de clientes com mensalidade</p>
        </div>
        <div className="page-actions">
          {isGestao && (
            <div className="segmented">
              <button className={periodo === 'mes' ? 'active' : ''} onClick={() => setPeriodo('mes')}>Este mês</button>
              <button className={periodo === 'ano' ? 'active' : ''} onClick={() => setPeriodo('ano')}>Últimos 12 meses</button>
            </div>
          )}
          <button className="btn-primary" onClick={() => setShowNew(true)}>+ Nova assinatura</button>
        </div>
      </header>

      <div className="content">
        {isGestao && resumoQuery.isLoading && <p className="state-msg">Carregando indicadores…</p>}
        {isGestao && resumoQuery.isError && <p className="state-msg error">Não foi possível carregar os indicadores agora.</p>}

        {isGestao && resumo && (
          <section className="stat-strip">
            <div className="stat-tile">
              <div className="t">MRR atual</div>
              <div className="v">{formatCurrency(resumo.mrr)}</div>
            </div>
            <div className="stat-tile">
              <div className="t">ARR</div>
              <div className="v">{formatCurrency(resumo.arr)}</div>
            </div>
            <div className="stat-tile">
              <div className="t">Assinaturas ativas</div>
              <div className="v">{resumo.assinaturas_ativas}</div>
            </div>
            <div className="stat-tile bonus">
              <div className="t">Novo MRR</div>
              <div className="v">{formatCurrency(resumo.novo_mrr)}</div>
            </div>
            <div className="stat-tile bonus">
              <div className="t">Expansão</div>
              <div className="v">{formatCurrency(resumo.expansao_mrr)}</div>
            </div>
            <div className="stat-tile">
              <div className="t">Contração + Churn</div>
              <div className="v" style={{ color: (resumo.contracao_mrr + resumo.churn_mrr) < 0 ? 'var(--critical)' : 'var(--ink)' }}>
                {formatCurrency(resumo.contracao_mrr + resumo.churn_mrr)}
              </div>
            </div>
            <div className="stat-tile">
              <div className="t">Churn de receita</div>
              <div className="v" style={{ color: resumo.churn_receita_pct > 3 ? 'var(--critical)' : 'var(--ink)' }}>
                {resumo.churn_receita_pct.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%
              </div>
            </div>
            <div className="stat-tile">
              <div className="t">NRR</div>
              <div className="v" style={{ color: resumo.nrr_pct >= 100 ? 'var(--good)' : 'var(--critical)' }}>
                {Math.round(resumo.nrr_pct)}%
              </div>
            </div>
            <div className="stat-tile bonus">
              <div className="t">LTV médio</div>
              <div className="v">{resumo.ltv == null ? '—' : formatCurrency(resumo.ltv)}</div>
            </div>
          </section>
        )}

        {isGestao && (
          <div className="card">
            <div className="card-head">
              <div><h3>Movimentação de MRR</h3><p>Novo, expansão, contração e churn — últimos 6 meses</p></div>
            </div>
            <div className="rr-waterfall-body">
              {waterfallQuery.isLoading && <p className="state-msg">Carregando…</p>}
              {waterfallQuery.data && <Waterfall meses={waterfallQuery.data.meses} />}
            </div>
            <div className="rr-legend">
              <span><i className="novo" />Novo MRR</span>
              <span><i className="expansao" />Expansão</span>
              <span><i className="contracao" />Contração</span>
              <span><i className="churn" />Churn</span>
            </div>
          </div>
        )}

        <div className="filters-bar">
          <div className="search">
            <input
              type="text" placeholder="Buscar empresa ou plano" value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select className="filter-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">Todos os status</option>
            <option value="ativa">Ativa</option>
            <option value="pausada">Pausada</option>
            <option value="cancelada">Cancelada</option>
          </select>
          <select className="filter-select" value={respFilter} onChange={(e) => setRespFilter(e.target.value)}>
            <option value="">Todos os responsáveis</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
          <span className="result-count">{filtered.length} de {assinaturas.length} assinaturas</span>
        </div>

        <div className="card">
          <div className="table-scroll">
            <table className="data">
              <thead>
                <tr>
                  <th>Empresa</th><th>Plano</th><th>MRR</th><th>Início</th>
                  <th>Responsável</th><th>Status</th><th />
                </tr>
              </thead>
              <tbody>
                {assinaturasQuery.isLoading && (
                  <tr><td colSpan={7} className="empty-cell">Carregando…</td></tr>
                )}
                {filtered.map((a) => (
                  <tr key={a.id} onClick={() => setOpenId(a.id)}>
                    <td className="row-title">{companiesById[a.company_id] ?? '—'}</td>
                    <td>{a.nome_plano}</td>
                    <td className="rr-mrr-cell">
                      {formatCurrency(a.valor_mensal)}
                      <span className="rr-cycle">{a.ciclo_cobranca === 'anual' ? '/mês (anual)' : '/mês'}</span>
                    </td>
                    <td className="updated">{formatDateBR(a.data_inicio)}</td>
                    <td>
                      <div className="row-resp">
                        <span className="avatar">{a.responsavel_id ? initials(usersById[a.responsavel_id]) : '—'}</span>
                        {a.responsavel_id ? (usersById[a.responsavel_id] ?? '—') : '—'}
                      </div>
                    </td>
                    <td>
                      <span className="status-pill" data-status={a.status}>
                        <span className="d" />{STATUS_LABEL[a.status]}
                      </span>
                    </td>
                    <td className="actions-col">
                      <button className="row-action" onClick={(e) => { e.stopPropagation(); setOpenId(a.id) }}>›</button>
                    </td>
                  </tr>
                ))}
                {assinaturasQuery.data && filtered.length === 0 && (
                  <tr><td colSpan={7} className="empty-cell">Nenhuma assinatura encontrada.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showNew && (
        <NewSubscriptionModal
          companies={companies}
          users={users}
          onClose={() => setShowNew(false)}
          onSubmit={(data) => createMutation.mutate(data)}
          submitting={createMutation.isPending}
          error={createMutation.error}
        />
      )}

      {openAssinatura && (
        <SubscriptionDrawer
          assinatura={openAssinatura}
          companyNome={companiesById[openAssinatura.company_id] ?? '—'}
          onClose={() => setOpenId(null)}
          onChanged={invalidateAll}
        />
      )}
    </>
  )
}

// Barras divergentes por mês (Novo+Expansão acima do eixo, Contração+Churn abaixo) — mesmo
// approach 100% CSS já usado no projeto, sem lib de gráfico nova.
function Waterfall({ meses }) {
  const maxAbs = Math.max(
    1,
    ...meses.map((m) => Math.max(m.novo_mrr + m.expansao_mrr, Math.abs(m.contracao_mrr) + Math.abs(m.churn_mrr))),
  )
  const maxHalfHeight = 76

  return (
    <div className="rr-waterfall">
      {meses.map((m) => {
        const novoH = (m.novo_mrr / maxAbs) * maxHalfHeight
        const expH = (m.expansao_mrr / maxAbs) * maxHalfHeight
        const contH = (Math.abs(m.contracao_mrr) / maxAbs) * maxHalfHeight
        const churnH = (Math.abs(m.churn_mrr) / maxAbs) * maxHalfHeight
        const [ano, mesNum] = m.mes.split('-')
        const label = new Date(Number(ano), Number(mesNum) - 1, 1)
          .toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' })
          .replace('.', '')
        return (
          <div className="rr-wf-col" key={m.mes}>
            <div className="rr-wf-bars">
              <div className="rr-wf-up">
                {m.novo_mrr > 0 && (
                  <div className="rr-wf-seg novo" style={{ height: `${novoH}px` }} title={`Novo: ${formatCurrency(m.novo_mrr)}`} />
                )}
                {m.expansao_mrr > 0 && (
                  <div className="rr-wf-seg expansao" style={{ height: `${expH}px` }} title={`Expansão: ${formatCurrency(m.expansao_mrr)}`} />
                )}
              </div>
              <div className="rr-wf-axis" />
              <div className="rr-wf-down">
                {m.contracao_mrr < 0 && (
                  <div className="rr-wf-seg contracao" style={{ height: `${contH}px` }} title={`Contração: ${formatCurrency(m.contracao_mrr)}`} />
                )}
                {m.churn_mrr < 0 && (
                  <div className="rr-wf-seg churn" style={{ height: `${churnH}px` }} title={`Churn: ${formatCurrency(m.churn_mrr)}`} />
                )}
              </div>
            </div>
            <div className={`rr-wf-net ${m.net_mrr >= 0 ? 'pos' : 'neg'}`}>
              {m.net_mrr > 0 ? '+' : ''}{formatCurrency(m.net_mrr)}
            </div>
            <div className="rr-wf-label">{label}</div>
          </div>
        )
      })}
    </div>
  )
}

// Exportado — reaproveitado em CompanyDetailPage.jsx pro card "Assinatura" (mesmo padrão de
// DealDrawer/CompanyModal/TaskModal, que também moram na página principal e são importados
// onde precisar). `presetCompanyId` pré-seleciona a empresa quando aberto a partir do
// detalhe dela — companies normalmente vem restrito a `[company]` nesse caso.
export function NewSubscriptionModal({ companies, users, presetCompanyId, onClose, onSubmit, submitting, error }) {
  const [form, setForm] = useState({
    company_id: presetCompanyId ?? '', nome_plano: PLANOS_SUGERIDOS[0], valor_mensal: '', ciclo_cobranca: 'mensal',
    data_inicio: new Date().toISOString().slice(0, 10), responsavel_id: '',
  })

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!form.company_id || !form.nome_plano.trim() || !form.valor_mensal || !form.data_inicio) return
    onSubmit({
      company_id: form.company_id,
      nome_plano: form.nome_plano.trim(),
      valor_mensal: Number(form.valor_mensal),
      ciclo_cobranca: form.ciclo_cobranca,
      data_inicio: form.data_inicio,
      responsavel_id: form.responsavel_id || null,
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Nova assinatura</h2>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="rr-company">Empresa (cliente) *</label>
            <select id="rr-company" required value={form.company_id} onChange={set('company_id')}>
              <option value="">Selecione…</option>
              {companies.map((c) => <option key={c.id} value={c.id}>{c.razao_social}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="rr-plano">Plano *</label>
            <input id="rr-plano" list="rr-planos-sugeridos" required value={form.nome_plano} onChange={set('nome_plano')} />
            <datalist id="rr-planos-sugeridos">
              {PLANOS_SUGERIDOS.map((p) => <option key={p} value={p} />)}
            </datalist>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="rr-valor">Valor mensal (R$) *</label>
              <input id="rr-valor" type="number" min="1" step="50" required value={form.valor_mensal} onChange={set('valor_mensal')} />
            </div>
            <div className="field">
              <label htmlFor="rr-ciclo">Ciclo de cobrança</label>
              <select id="rr-ciclo" value={form.ciclo_cobranca} onChange={set('ciclo_cobranca')}>
                <option value="mensal">Mensal</option>
                <option value="anual">Anual (valor já normalizado por mês)</option>
              </select>
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label htmlFor="rr-inicio">Data de início *</label>
              <input id="rr-inicio" type="date" required value={form.data_inicio} onChange={set('data_inicio')} />
            </div>
            <div className="field">
              <label htmlFor="rr-resp">Responsável</label>
              <select id="rr-resp" value={form.responsavel_id} onChange={set('responsavel_id')}>
                <option value="">Sem responsável</option>
                {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
              </select>
            </div>
          </div>
          {error && <p className="f-err show">{apiErrorMessage(error, 'Não foi possível criar a assinatura.')}</p>}
          <div className="modal-actions">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? 'Criando…' : 'Criar assinatura'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Exportado — mesmo motivo de NewSubscriptionModal acima.
export function SubscriptionDrawer({ assinatura, companyNome, onClose, onChanged }) {
  const queryClient = useQueryClient()
  const [showAdjust, setShowAdjust] = useState(false)
  const [showCancel, setShowCancel] = useState(false)
  const [adjustValor, setAdjustValor] = useState(String(assinatura.valor_mensal))
  const [adjustObs, setAdjustObs] = useState('')
  const [cancelMotivo, setCancelMotivo] = useState('')

  const eventosQuery = useQuery({
    queryKey: ['assinaturas', 'eventos', assinatura.id],
    queryFn: () => listEventosAssinatura(assinatura.id),
  })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['assinaturas'] })
    onChanged()
  }

  const adjustMutation = useMutation({
    mutationFn: (data) => atualizarValorAssinatura(assinatura.id, data),
    onSuccess: () => { setShowAdjust(false); invalidate() },
  })
  const cancelMutation = useMutation({
    mutationFn: (data) => cancelarAssinatura(assinatura.id, data),
    onSuccess: () => { setShowCancel(false); invalidate() },
  })
  const reactivateMutation = useMutation({
    mutationFn: () => reativarAssinatura(assinatura.id, {}),
    onSuccess: invalidate,
  })

  function submitAdjust(e) {
    e.preventDefault()
    const valor = Number(adjustValor)
    if (!valor || valor === assinatura.valor_mensal) return
    adjustMutation.mutate({ valor_mensal: valor, observacao: adjustObs.trim() || undefined })
  }
  function submitCancel(e) {
    e.preventDefault()
    cancelMutation.mutate({ motivo_cancelamento: cancelMotivo.trim() || undefined })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div><h2>{companyNome}</h2><p>{assinatura.nome_plano} · início em {formatDateBR(assinatura.data_inicio)}</p></div>
          <button className="drawer-close" onClick={onClose}>×</button>
        </div>
        <div className="drawer-body">
          <div className="rr-hero">
            <div>
              <div className="rr-hero-lbl">MRR desta assinatura</div>
              <div className="rr-hero-big">{formatCurrency(assinatura.valor_mensal)}</div>
              <div className="rr-hero-sub">
                {formatCurrency(assinatura.valor_mensal * 12)} de ARR · {CICLO_LABEL[assinatura.ciclo_cobranca]}
              </div>
            </div>
            <span className="status-pill" data-status={assinatura.status}>
              <span className="d" />{STATUS_LABEL[assinatura.status]}
            </span>
          </div>

          {assinatura.status === 'cancelada' && assinatura.motivo_cancelamento && (
            <p className="state-msg">
              Motivo do cancelamento ({formatDateBR(assinatura.data_cancelamento)}): {assinatura.motivo_cancelamento}
            </p>
          )}

          {assinatura.status === 'ativa' && !showAdjust && !showCancel && (
            <div className="rr-actions">
              <button className="btn-ghost sm" onClick={() => setShowAdjust(true)}>Registrar reajuste</button>
              <button className="btn-danger" onClick={() => setShowCancel(true)}>Cancelar assinatura</button>
            </div>
          )}
          {assinatura.status === 'cancelada' && (
            <div className="rr-actions">
              <button className="btn-primary" disabled={reactivateMutation.isPending} onClick={() => reactivateMutation.mutate()}>
                {reactivateMutation.isPending ? 'Reativando…' : 'Reativar assinatura'}
              </button>
            </div>
          )}
          {assinatura.status === 'pausada' && (
            <p className="state-msg">Assinatura pausada — sem ação de reajuste até normalizar.</p>
          )}

          {showAdjust && (
            <form className="rr-inline-form" onSubmit={submitAdjust}>
              <div className="f-group">
                <label className="f-label">Novo valor mensal (R$)</label>
                <input
                  className="f-input" type="number" min="1" step="50" value={adjustValor}
                  onChange={(e) => setAdjustValor(e.target.value)}
                />
              </div>
              <div className="f-group">
                <label className="f-label">Observação <span className="opt">(opcional)</span></label>
                <input className="f-input" type="text" value={adjustObs} onChange={(e) => setAdjustObs(e.target.value)} />
              </div>
              {adjustMutation.isError && (
                <p className="f-err show">{apiErrorMessage(adjustMutation.error, 'Não foi possível registrar o reajuste.')}</p>
              )}
              <div className="rr-inline-foot">
                <button type="button" className="btn-ghost sm" onClick={() => setShowAdjust(false)}>Cancelar</button>
                <button type="submit" className="btn-primary" disabled={adjustMutation.isPending}>
                  {adjustMutation.isPending ? 'Salvando…' : 'Salvar'}
                </button>
              </div>
            </form>
          )}

          {showCancel && (
            <form className="rr-inline-form" onSubmit={submitCancel}>
              <div className="f-group">
                <label className="f-label">Motivo</label>
                <input
                  className="f-input" type="text" placeholder="Ex.: reduziu operação, trocou de fornecedor…"
                  value={cancelMotivo} onChange={(e) => setCancelMotivo(e.target.value)}
                />
              </div>
              {cancelMutation.isError && (
                <p className="f-err show">{apiErrorMessage(cancelMutation.error, 'Não foi possível cancelar.')}</p>
              )}
              <div className="rr-inline-foot">
                <button type="button" className="btn-ghost sm" onClick={() => setShowCancel(false)}>Voltar</button>
                <button type="submit" className="btn-danger" disabled={cancelMutation.isPending}>
                  {cancelMutation.isPending ? 'Cancelando…' : 'Confirmar cancelamento'}
                </button>
              </div>
            </form>
          )}

          <div>
            <div className="rr-section-title">Histórico de eventos</div>
            {eventosQuery.isLoading && <p className="state-msg">Carregando…</p>}
            <div className="rr-timeline">
              {(eventosQuery.data ?? []).map((e) => (
                <div className="rr-tl-item" key={e.id}>
                  <div className={`rr-tl-dot ${e.tipo}`} />
                  <div>
                    <div className="rr-tl-title">
                      {EVENTO_LABEL[e.tipo] ?? e.tipo}
                      <span className={`rr-tl-delta ${e.delta_mrr >= 0 ? 'pos' : 'neg'}`}>
                        {e.delta_mrr > 0 ? '+' : ''}{formatCurrency(e.delta_mrr)}
                      </span>
                    </div>
                    <div className="rr-tl-date">
                      {formatDateBR(e.data_evento)}{e.observacao ? ` · ${e.observacao}` : ''}
                    </div>
                  </div>
                </div>
              ))}
              {eventosQuery.data && eventosQuery.data.length === 0 && (
                <p className="state-msg">Nenhum evento registrado.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
