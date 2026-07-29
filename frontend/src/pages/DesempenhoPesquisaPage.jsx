import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getPerformanceReport } from '../api/leadProspects'
import '../styles/dataTable.css'
import './DesempenhoPesquisaPage.css'

const BAR_COLORS = ['var(--seq-1)', 'var(--seq-2)', 'var(--seq-3)', 'var(--seq-4)', 'var(--seq-5)', 'var(--seq-6)']

function money(n) {
  return `R$ ${Number(n ?? 0).toFixed(2).replace('.', ',')}`
}
function qualClass(pct) {
  if (pct >= 70) return 'high'
  if (pct >= 40) return 'mid'
  return 'low'
}
function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}

function mesOptions() {
  const options = []
  const now = new Date()
  for (let i = 0; i < 12; i += 1) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const label = d.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
    options.push({ value, label: label.charAt(0).toUpperCase() + label.slice(1) })
  }
  return options
}

function exportCsv(mes, rows) {
  const headers = ['pesquisador', 'pesquisas', 'icp_a', 'icp_b', 'icp_c', 'sem_perfil_nao_avaliado', 'taxa_qualificacao', 'promovidos', 'bonus_valido']
  const lines = [headers.join(',')]
  rows.forEach((r) => {
    lines.push([r.pesquisador_nome, r.total, r.icp_a, r.icp_b, r.icp_c, r.sem_perfil, `${r.taxa_qualificacao}%`, r.promovidos, r.bonus_valido.toFixed(2)].join(','))
  })
  const blob = new Blob([`﻿${lines.join('\r\n')}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `desempenho-pesquisa-${mes}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function DesempenhoPesquisaPage() {
  const options = useMemo(mesOptions, [])
  const [mes, setMes] = useState(options[0].value)

  const reportQuery = useQuery({
    queryKey: ['lead-prospects', 'performance-report', mes],
    queryFn: () => getPerformanceReport(mes),
    retry: false,
  })

  if (reportQuery.isError) {
    return (
      <>
        <header className="topbar"><div className="topbar-title"><h1>Desempenho de Pesquisa</h1></div></header>
        <div className="content">
          <p className="state-msg error">Só administradores e gestores podem ver este relatório.</p>
        </div>
      </>
    )
  }

  const rows = reportQuery.data?.rows ?? []
  const summary = rows.reduce((acc, r) => ({
    total: acc.total + r.total,
    promovidos: acc.promovidos + r.promovidos,
    bonus: acc.bonus + r.bonus_valido,
    aeb: acc.aeb + r.icp_a + r.icp_b,
  }), { total: 0, promovidos: 0, bonus: 0, aeb: 0 })
  const qualifGeral = summary.total ? Math.round((summary.aeb / summary.total) * 100) : 0

  const ranking = [...rows].sort((a, b) => b.taxa_qualificacao - a.taxa_qualificacao || b.promovidos - a.promovidos)
  const maxTotal = Math.max(1, ...rows.map((r) => r.total))

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Desempenho de Pesquisa</h1>
          <p>Gamificação e bônus por pesquisador — a tela de consumo do que é calculado em Pesquisa de Leads</p>
        </div>
        <div className="page-actions">
          <button className="btn-ghost" disabled={rows.length === 0} onClick={() => exportCsv(mes, rows)}>Exportar .csv</button>
        </div>
      </header>

      <div className="content">
        <div className="filters-bar">
          <select className="filter-select" value={mes} onChange={(e) => setMes(e.target.value)}>
            {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div className="help-card">
          Bônus só é <strong>válido</strong> quando a pesquisa vira empresa de verdade (status &quot;Promovido&quot; em Pesquisa de Leads) —
          completar os campos não basta. Esse relatório é só consulta; não existe módulo de folha de pagamento aqui.
        </div>

        {reportQuery.isLoading && <p className="state-msg">Carregando relatório…</p>}

        {reportQuery.data && (
          <>
            <div className="stat-strip">
              <div className="stat-tile"><div className="t">Pesquisas no mês</div><div className="v">{summary.total}</div></div>
              <div className="stat-tile"><div className="t">Promovidos</div><div className="v">{summary.promovidos}</div></div>
              <div className="stat-tile"><div className="t">Taxa de qualificação</div><div className="v">{qualifGeral}%</div></div>
              <div className="stat-tile bonus"><div className="t">Bônus total do mês</div><div className="v">{money(summary.bonus)}</div></div>
            </div>

            {rows.length === 0 ? (
              <div className="card"><p className="state-msg">Nenhuma pesquisa registrada neste mês.</p></div>
            ) : (
              <>
                <div className="grid-main">
                  <div className="card">
                    <div className="card-head"><h2>Ranking do mês</h2><p>Por taxa de qualificação (ICP A + B)</p></div>
                    <div className="card-body">
                      {ranking.map((r, i) => (
                        <div className="rank-row" key={r.pesquisador_id}>
                          <span className={`rank-medal ${i === 0 ? 'p1' : i === 1 ? 'p2' : 'p3'}`}>{i + 1}º</span>
                          <div className="rank-body">
                            <div className="rank-name">{r.pesquisador_nome}</div>
                            <div className="rank-meta">{r.total} pesquisas · {r.promovidos} promovido{r.promovidos === 1 ? '' : 's'}</div>
                          </div>
                          <div className="rank-value"><div className="v">{r.taxa_qualificacao}%</div><div className="t">qualificação</div></div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="card">
                    <div className="card-head"><h2>Pesquisas realizadas</h2><p>Volume por pesquisador no mês selecionado</p></div>
                    <div className="card-body">
                      {rows.map((r, i) => (
                        <div className="bar-row" key={r.pesquisador_id}>
                          <span className="bar-name">{r.pesquisador_nome}</span>
                          <div className="bar-track">
                            <div className="bar-fill" style={{ width: `${(r.total / maxTotal) * 100}%`, background: BAR_COLORS[i % BAR_COLORS.length] }} />
                          </div>
                          <span className="bar-value">{r.total}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="card">
                  <div className="table-scroll">
                    <table className="data">
                      <thead>
                        <tr>
                          <th>Pesquisador</th>
                          <th className="cell-num">Pesquisas</th>
                          <th className="cell-num">ICP A</th>
                          <th className="cell-num">ICP B</th>
                          <th className="cell-num">ICP C</th>
                          <th className="cell-num">Sem perfil/Não aval.</th>
                          <th style={{ textAlign: 'right' }}>Taxa qualif.</th>
                          <th className="cell-num">Promovidos</th>
                          <th style={{ textAlign: 'right' }}>Bônus válido</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((r) => (
                          <tr key={r.pesquisador_id}>
                            <td>
                              <div className="row-resp">
                                <span className="avatar">{initials(r.pesquisador_nome)}</span>
                                <span className="row-resp-name">{r.pesquisador_nome}</span>
                              </div>
                            </td>
                            <td className="cell-num">{r.total}</td>
                            <td className="cell-num">{r.icp_a}</td>
                            <td className="cell-num">{r.icp_b}</td>
                            <td className="cell-num">{r.icp_c}</td>
                            <td className="cell-num">{r.sem_perfil}</td>
                            <td style={{ textAlign: 'right' }}><span className={`qual-pill ${qualClass(r.taxa_qualificacao)}`}>{r.taxa_qualificacao}%</span></td>
                            <td className="cell-num">{r.promovidos}</td>
                            <td className="bonus-cell">{money(r.bonus_valido)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </>
  )
}
