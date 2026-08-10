import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext.jsx'
import { getForecastResumo } from '../api/forecast'
import { updateDeal } from '../api/deals'
import { listUsers } from '../api/users'
import '../styles/dataTable.css'
import './PrevisaoComercialPage.css'

const GESTAO_PERFIS = new Set(['admin', 'gestor'])

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
                <div className="t">Commit</div>
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
              <span><i className="commit" />Commit</span>
            </div>

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
                      <tr><th>Vendedor</th><th>Negócios</th><th>Pipeline</th><th>Forecast</th><th>Commit</th></tr>
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
                            {v.commit === 0 && <span className="pc-chip-warn">sem commit</span>}
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
                  <p><b>Commit</b> — soma do valor previsto apenas dos negócios que o vendedor marcou manualmente como compromisso de fechamento. Único campo novo — os demais já existiam.</p>
                </div>
              </div>
            </section>

            <div className="card">
              <div className="card-head">
                <div>
                  <h3>Negócios previstos para {mesLabel}</h3>
                  <p>Marque Commit nos negócios que o vendedor confirma fechar neste mês</p>
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
                        <th style={{ textAlign: 'right' }}>Valor</th><th>Fechamento</th><th>Commit</th>
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
                              <span className="pc-txt">{d.commit ? 'Commit' : 'Marcar'}</span>
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
