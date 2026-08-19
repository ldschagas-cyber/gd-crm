import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext.jsx'
import { getForecastResumo } from '../api/forecast'
import { updateDeal } from '../api/deals'
import { listUsers } from '../api/users'
import {
  createRevenueInvestment, deleteRevenueInvestment, getCacRoi, listRevenueInvestments,
} from '../api/revenueInvestments'
import '../styles/dataTable.css'
import './PrevisaoComercialPage.css'

const GESTAO_PERFIS = new Set(['admin', 'gestor'])
const CATEGORIA_LABEL = { marketing: 'Marketing', vendas: 'Vendas', ferramentas: 'Ferramentas', outros: 'Outros' }

function formatCurrency(v) {
  return (v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}
function pct(part, total) {
  return total ? Math.round((part / total) * 100) : 0
}
function mesOptions() {
  const options = []
  const now = new Date()
  for (let i = -2; i <= 3; i += 1) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1)
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const label = d.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
    options.push({ value, label: label.charAt(0).toUpperCase() + label.slice(1), isCurrent: i === 0 })
  }
  return options
}
function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}

export default function PrevisaoComercialPage() {
  const { user } = useAuth()
  const isGestao = GESTAO_PERFIS.has(user?.perfil)
  const queryClient = useQueryClient()
  const options = useMemo(mesOptions, [])
  const [mes, setMes] = useState(options.find((o) => o.isCurrent)?.value ?? options[0].value)
  const [responsavelId, setResponsavelId] = useState('')

  const usersQuery = useQuery({
    queryKey: ['users', 'for-forecast-filter'],
    queryFn: () => listUsers({ size: 100 }),
    enabled: isGestao,
    retry: false,
  })
  const users = usersQuery.data?.items ?? []

  const resumoQuery = useQuery({
    queryKey: ['forecast', 'resumo', mes, responsavelId],
    queryFn: () => getForecastResumo({ mes, responsavelId: responsavelId || undefined }),
    enabled: Boolean(user),
  })

  const commitMutation = useMutation({
    mutationFn: ({ id, commit }) => updateDeal(id, { commit }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['forecast'] }),
  })

  const data = resumoQuery.data
  const mesLabel = (options.find((o) => o.value === mes)?.label ?? mes).toLowerCase()

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Previsão Comercial</h1>
          <p>Pipeline, forecast ponderado e compromisso de fechamento por vendedor</p>
        </div>
        <select className="filter-select" value={mes} onChange={(e) => setMes(e.target.value)}>
          {options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}{o.isCurrent ? ' (atual)' : ''}</option>
          ))}
        </select>
      </header>

      <div className="content">
        {isGestao && (
          <div className="filters-bar">
            <select className="filter-select" value={responsavelId} onChange={(e) => setResponsavelId(e.target.value)}>
              <option value="">Todos os vendedores</option>
              {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
            </select>
          </div>
        )}

        {resumoQuery.isLoading && <p className="state-msg">Carregando…</p>}
        {resumoQuery.isError && <p className="state-msg error">Não foi possível carregar a previsão agora.</p>}

        {data && (
          <>
            <section className="stat-strip">
              <div className="stat-tile">
                <div className="t">Pipeline</div>
                <div className="v">{formatCurrency(data.pipeline_total)}</div>
                <div className="pc-sub">{data.negocios.length} negócio{data.negocios.length === 1 ? '' : 's'} em aberto</div>
              </div>
              <div className="stat-tile">
                <div className="t">Forecast</div>
                <div className="v">{formatCurrency(data.forecast_total)}</div>
                <div className="pc-sub">{pct(data.forecast_total, data.pipeline_total)}% do pipeline · ponderado por probabilidade</div>
              </div>
              <div className="stat-tile bonus">
                <div className="t">Compromisso</div>
                <div className="v" style={{ color: 'var(--amber-dark)' }}>{formatCurrency(data.commit_total)}</div>
                <div className="pc-sub">{pct(data.commit_total, data.pipeline_total)}% do pipeline · confirmado pelo vendedor</div>
              </div>
            </section>

            <div className="pc-cov-track">
              <div className="pc-cov-fill pipeline" style={{ width: '100%' }} />
              <div className="pc-cov-fill forecast" style={{ width: `${pct(data.forecast_total, data.pipeline_total)}%` }} />
              <div className="pc-cov-fill commit" style={{ width: `${pct(data.commit_total, data.pipeline_total)}%` }} />
            </div>
            <div className="pc-cov-legend">
              <span><i className="pipeline" />Pipeline</span>
              <span><i className="forecast" />Forecast</span>
              <span><i className="commit" />Compromisso</span>
            </div>

            {isGestao && <CacRoiCard mes={mes} mesLabel={mesLabel} />}

            <section className="pc-grid-2">
              <div className="card">
                <div className="card-head">
                  <div><h3>Pipeline por vendedor</h3><p>Negócios previstos para {mesLabel}, ponderados por probabilidade</p></div>
                </div>
                {data.por_vendedor.length === 0 ? (
                  <p className="state-msg" style={{ padding: '0 18px 18px' }}>Nenhum negócio previsto neste mês.</p>
                ) : (
                  <table className="pc-seller-tbl">
                    <thead>
                      <tr><th>Vendedor</th><th>Negócios</th><th>Pipeline</th><th>Forecast</th><th>Compromisso</th></tr>
                    </thead>
                    <tbody>
                      {data.por_vendedor.map((v) => (
                        <tr key={v.responsavel_id}>
                          <td>
                            <div className="pc-seller-name">
                              <span className="pc-seller-avatar">{initials(v.nome)}</span>{v.nome}
                            </div>
                          </td>
                          <td>{v.negocios}</td>
                          <td>{formatCurrency(v.pipeline)}</td>
                          <td>{formatCurrency(v.forecast)}</td>
                          <td className="pc-commit-cell">
                            {v.commit > 0 ? formatCurrency(v.commit) : '—'}
                            {v.commit === 0 && <span className="pc-chip-warn">sem compromisso</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td>Total</td>
                        <td>{data.negocios.length}</td>
                        <td>{formatCurrency(data.pipeline_total)}</td>
                        <td>{formatCurrency(data.forecast_total)}</td>
                        <td>{formatCurrency(data.commit_total)}</td>
                      </tr>
                    </tfoot>
                  </table>
                )}
              </div>

              <div className="card">
                <div className="card-head">
                  <div><h3>Como os números são calculados</h3><p>Mesma fórmula já usada hoje no board de Negócios</p></div>
                </div>
                <div className="pc-methodology">
                  <p><b>Pipeline</b> — soma do valor previsto dos negócios abertos com previsão de fechamento dentro do mês selecionado.</p>
                  <p><b>Forecast</b> — soma de valor previsto × probabilidade de cada negócio. É o mesmo cálculo que já aparece no rodapé de cada etapa do Kanban, agora agregado por mês e vendedor.</p>
                  <p><b>Compromisso</b> — soma do valor previsto apenas dos negócios que o vendedor marcou manualmente como compromisso de fechamento. Único campo novo — os demais já existiam.</p>
                </div>
              </div>
            </section>

            <div className="card">
              <div className="card-head">
                <div>
                  <h3>Negócios previstos para {mesLabel}</h3>
                  <p>Marque como Compromisso os negócios que o vendedor confirma fechar neste mês</p>
                </div>
              </div>
              {data.negocios.length === 0 ? (
                <p className="state-msg" style={{ padding: '0 18px 18px' }}>Nenhum negócio previsto para este recorte.</p>
              ) : (
                <div className="table-scroll">
                  <table className="pc-deals-tbl">
                    <thead>
                      <tr>
                        <th>Negócio</th><th>Vendedor</th><th>Etapa</th><th>Probabilidade</th>
                        <th style={{ textAlign: 'right' }}>Valor</th><th>Fechamento</th><th>Compromisso</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.negocios.map((d) => (
                        <tr key={d.id}>
                          <td>
                            <div className="pc-deal-name">{d.nome}</div>
                            <div className="pc-deal-company">{d.company_nome}</div>
                          </td>
                          <td>{d.responsavel_nome}</td>
                          <td><span className="pc-stage-badge">{d.stage_nome}</span></td>
                          <td className="pc-prob-cell">
                            <span className="pc-prob-bar"><i style={{ width: `${d.probabilidade ?? 0}%` }} /></span>
                            {d.probabilidade ?? 0}%
                          </td>
                          <td className="pc-money-cell">{formatCurrency(d.valor_previsto)}</td>
                          <td>{d.data_prev_fechamento ? new Date(`${d.data_prev_fechamento}T00:00:00`).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }) : '—'}</td>
                          <td>
                            <label className="pc-commit-toggle">
                              <input
                                type="checkbox"
                                checked={d.commit}
                                disabled={commitMutation.isPending}
                                onChange={(e) => commitMutation.mutate({ id: d.id, commit: e.target.checked })}
                              />
                              <span className="pc-box">
                                <svg viewBox="0 0 20 20"><path d="M4 10.5l4 4 8-9" strokeLinecap="round" strokeLinejoin="round" /></svg>
                              </span>
                              <span className="pc-txt">{d.commit ? 'Compromisso' : 'Marcar'}</span>
                            </label>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </>
  )
}

// CAC & ROI — extensão de Previsão Comercial (ver docs/PLANO_PREVISAO_COMERCIAL.md §8).
// `clientes_novos`/`receita_realizada` vêm de FunilMetasResumo (etapa "fechados") via o
// endpoint /revenue-investments/cac-roi — não recalculados aqui, só o investimento é dado
// novo. Só admin/gestor chega a montar (guard no pai) — o backend também exige o perfil.
function CacRoiCard({ mes, mesLabel }) {
  const queryClient = useQueryClient()
  const [novo, setNovo] = useState({ categoria: 'marketing', valor: '', observacao: '' })

  const cacRoiQuery = useQuery({
    queryKey: ['revenue-investments', 'cac-roi', mes],
    queryFn: () => getCacRoi({ mes }),
  })
  const investmentsQuery = useQuery({
    queryKey: ['revenue-investments', 'list', mes],
    queryFn: () => listRevenueInvestments({ mes }),
  })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['revenue-investments'] })
  }
  const createMutation = useMutation({
    mutationFn: (data) => createRevenueInvestment({ mes, ...data }),
    onSuccess: () => { invalidate(); setNovo({ categoria: 'marketing', valor: '', observacao: '' }) },
  })
  const deleteMutation = useMutation({
    mutationFn: (id) => deleteRevenueInvestment(id),
    onSuccess: invalidate,
  })

  function handleAdd(e) {
    e.preventDefault()
    const valor = Number(novo.valor)
    if (!valor || valor <= 0) return
    createMutation.mutate({ categoria: novo.categoria, valor, observacao: novo.observacao || undefined })
  }

  const data = cacRoiQuery.data
  const investimentos = investmentsQuery.data ?? []
  const roiColor = data?.roi == null ? 'var(--ink-faint)' : data.roi >= 0 ? 'var(--good)' : 'var(--danger)'

  return (
    <div className="card" style={{ marginBottom: 18 }}>
      <div className="card-head">
        <div><h3>CAC &amp; ROI comercial</h3><p>Custo de aquisição e retorno do investimento em {mesLabel}</p></div>
        <span className="pc-integration-pill">dado vem de Metas do Funil</span>
      </div>

      {cacRoiQuery.isLoading && <p className="state-msg">Carregando…</p>}
      {cacRoiQuery.isError && <p className="state-msg error">Não foi possível calcular CAC/ROI agora.</p>}

      {data && (
        <section className="stat-strip" style={{ padding: '2px 18px 16px' }}>
          <div className="stat-tile">
            <div className="t">Investimento</div>
            <div className="v">{formatCurrency(data.investimento_total)}</div>
            <div className="pc-sub">lançado manualmente abaixo</div>
          </div>
          <div className="stat-tile">
            <div className="t">CAC</div>
            <div className="v">{data.cac != null ? formatCurrency(data.cac) : '—'}</div>
            <div className="pc-sub">
              {data.clientes_novos} cliente{data.clientes_novos === 1 ? '' : 's'} fechado{data.clientes_novos === 1 ? '' : 's'} no mês
            </div>
          </div>
          <div className="stat-tile bonus">
            <div className="t">ROI</div>
            <div className="v" style={{ color: roiColor }}>
              {data.roi != null ? `${data.roi >= 0 ? '+' : ''}${Math.round(data.roi)}%` : '—'}
            </div>
            <div className="pc-sub">receita realizada {formatCurrency(data.receita_realizada)}</div>
          </div>
        </section>
      )}

      <div className="table-scroll">
        <table className="data pc-inv-tbl">
          <thead>
            <tr><th>Categoria</th><th>Observação</th><th style={{ textAlign: 'right' }}>Valor</th><th /></tr>
          </thead>
          <tbody>
            {investimentos.map((inv) => (
              <tr key={inv.id}>
                <td>
                  <span className="pc-inv-cat"><i className={inv.categoria} />{CATEGORIA_LABEL[inv.categoria] ?? inv.categoria}</span>
                </td>
                <td>{inv.observacao || '—'}</td>
                <td className="pc-money-cell">{formatCurrency(inv.valor)}</td>
                <td style={{ width: 34 }}>
                  <button
                    className="icon-btn danger"
                    title="Remover lançamento"
                    disabled={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate(inv.id)}
                  >
                    ×
                  </button>
                </td>
              </tr>
            ))}
            {investimentos.length === 0 && !investmentsQuery.isLoading && (
              <tr><td colSpan={4} className="state-msg">Nenhum lançamento em {mesLabel}.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <form className="pc-inv-add" onSubmit={handleAdd}>
        <select
          className="filter-select"
          value={novo.categoria}
          onChange={(e) => setNovo((n) => ({ ...n, categoria: e.target.value }))}
        >
          {Object.entries(CATEGORIA_LABEL).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <input
          type="text" placeholder="Observação (opcional)" value={novo.observacao}
          onChange={(e) => setNovo((n) => ({ ...n, observacao: e.target.value }))}
        />
        <input
          type="number" min="0" step="0.01" placeholder="Valor" required value={novo.valor}
          onChange={(e) => setNovo((n) => ({ ...n, valor: e.target.value }))}
        />
        <button type="submit" className="pc-inv-add-btn" disabled={createMutation.isPending}>
          + Adicionar lançamento
        </button>
      </form>
    </div>
  )
}
