import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMetasProgress, getPerformanceReport } from '../api/leadProspects'
import { listUsers } from '../api/users'
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
function metaPct(atual, meta) {
  if (!meta) return null
  return Math.round((atual / meta) * 100)
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

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
}

// Relatório visual, standalone (cores fixas — não herda tema claro/escuro do app,
// é um documento aberto em aba própria pra visualizar/imprimir/salvar em PDF).
function abrirRelatorioHtml({ mesLabel, pesquisadorNome, rows, summary, qualifGeral, ranking, metaRows }) {
  const geradoEm = new Date().toLocaleString('pt-BR', { dateStyle: 'long', timeStyle: 'short' })
  const qualCor = (pct) => (pct >= 70 ? '#2E7D5B' : pct >= 40 ? '#B36A21' : '#B4453C')

  const linhasRanking = ranking.map((r, i) => `
    <div class="rank-row">
      <span class="medal">${i + 1}º</span>
      <div class="rank-body">
        <div class="rank-name">${escapeHtml(r.pesquisador_nome)}</div>
        <div class="rank-meta">${r.total} pesquisa${r.total === 1 ? '' : 's'} · ${r.promovidos} promovido${r.promovidos === 1 ? '' : 's'}</div>
      </div>
      <div class="rank-value" style="color:${qualCor(r.taxa_qualificacao)}">${r.taxa_qualificacao}%</div>
    </div>`).join('') || '<p class="muted">Sem pesquisas no período.</p>'

  const linhasTabela = rows.map((r) => `
    <tr>
      <td>${escapeHtml(r.pesquisador_nome)}</td>
      <td class="num">${r.total}</td>
      <td class="num">${r.icp_a}</td>
      <td class="num">${r.icp_b}</td>
      <td class="num">${r.icp_c}</td>
      <td class="num">${r.sem_perfil}</td>
      <td class="num"><span class="pill" style="background:${qualCor(r.taxa_qualificacao)}1a;color:${qualCor(r.taxa_qualificacao)}">${r.taxa_qualificacao}%</span></td>
      <td class="num">${r.promovidos}</td>
      <td class="num">${money(r.bonus_valido)}</td>
    </tr>`).join('')

  const linhasMetas = metaRows.map((r) => {
    const pctSemana = r.meta_semanal ? Math.round((r.pesquisas_semana / r.meta_semanal) * 100) : null
    const pctMes = r.meta_mensal ? Math.round((r.pesquisas_mes / r.meta_mensal) * 100) : null
    return `
    <tr>
      <td>${escapeHtml(r.pesquisador_nome)}</td>
      <td class="num">${r.pesquisas_semana}${r.meta_semanal ? ` / ${r.meta_semanal}` : ''}${pctSemana != null ? ` <span class="pill" style="background:${qualCor(pctSemana)}1a;color:${qualCor(pctSemana)}">${pctSemana}%</span>` : ' <span class="muted">sem meta</span>'}</td>
      <td class="num">${r.pesquisas_mes}${r.meta_mensal ? ` / ${r.meta_mensal}` : ''}${pctMes != null ? ` <span class="pill" style="background:${qualCor(pctMes)}1a;color:${qualCor(pctMes)}">${pctMes}%</span>` : ' <span class="muted">sem meta</span>'}</td>
    </tr>`
  }).join('')

  const html = `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório de Desempenho — ${escapeHtml(mesLabel)}</title>
<style>
  :root { --indigo:#2B2F5E; --azul:#2F6BA8; --amber:#D9B654; --good:#2E7D5B; --warning:#B36A21; --critical:#B4453C;
          --ink:#1B1D33; --ink-dim:#5C5F74; --ink-faint:#8A8D9C; --border:#EAEAE6; --paper:#F4F4F2; }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 40px 48px 60px; background: #fff; color: var(--ink);
         font-family: 'IBM Plex Sans', 'Segoe UI', Helvetica, Arial, sans-serif; }
  .mono { font-family: 'IBM Plex Mono', 'Consolas', monospace; }
  header.doc-head { display: flex; justify-content: space-between; align-items: flex-end;
                     border-bottom: 2px solid var(--indigo); padding-bottom: 16px; margin-bottom: 24px; }
  h1 { font-family: 'Space Grotesk', 'IBM Plex Sans', sans-serif; font-weight: 700; font-size: 22px; margin: 0 0 4px; letter-spacing: -0.01em; }
  .doc-sub { color: var(--ink-dim); font-size: 13px; margin: 0; }
  .brand { text-align: right; font-size: 12px; color: var(--ink-faint); }
  .brand b { font-family: 'Space Grotesk', 'IBM Plex Sans', sans-serif; color: var(--indigo); font-size: 14px; }
  .stat-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 28px; }
  .stat-tile { border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; background: var(--paper); }
  .stat-tile .t { font-size: 11px; color: var(--ink-faint); text-transform: uppercase; letter-spacing: .04em; }
  .stat-tile .v { font-size: 22px; font-weight: 700; margin-top: 4px; }
  .stat-tile.bonus .v { color: var(--good); }
  section { margin-bottom: 30px; }
  h2 { font-size: 15px; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
  .rank-row { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--border); }
  .rank-row:last-child { border-bottom: none; }
  .medal { width: 24px; height: 24px; border-radius: 50%; background: var(--paper); border: 1px solid var(--border);
           display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex: none; }
  .rank-body { flex: 1; }
  .rank-name { font-weight: 600; font-size: 13.5px; }
  .rank-meta { font-size: 11.5px; color: var(--ink-faint); }
  .rank-value { font-weight: 700; font-family: 'IBM Plex Mono', monospace; font-size: 15px; }
  table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }
  th { font-size: 10.5px; text-transform: uppercase; letter-spacing: .03em; color: var(--ink-faint); font-weight: 600; }
  td.num, th.num { text-align: right; font-family: 'IBM Plex Mono', monospace; }
  .pill { padding: 2px 8px; border-radius: 100px; font-weight: 700; font-size: 11.5px; white-space: nowrap; }
  .muted { color: var(--ink-faint); font-size: 12px; }
  .no-print { position: fixed; top: 20px; right: 20px; }
  .no-print button { background: var(--azul); color: #fff; border: none; padding: 10px 18px; border-radius: 8px;
                      font-weight: 600; cursor: pointer; font-size: 13px; }
  footer { margin-top: 40px; padding-top: 14px; border-top: 1px solid var(--border); font-size: 11px; color: var(--ink-faint); }
  @media print { .no-print { display: none; } body { padding: 0 12px; } }
</style>
</head>
<body>
  <div class="no-print"><button onclick="window.print()">🖨️ Imprimir / Salvar PDF</button></div>

  <header class="doc-head">
    <div>
      <h1>Relatório de Desempenho de Pesquisa</h1>
      <p class="doc-sub">${escapeHtml(mesLabel)}${pesquisadorNome ? ` · Pesquisador: ${escapeHtml(pesquisadorNome)}` : ' · Todos os pesquisadores'}</p>
    </div>
    <div class="brand"><b>Argos CRM</b><br>Gerado em ${geradoEm}</div>
  </header>

  <div class="stat-strip">
    <div class="stat-tile"><div class="t">Pesquisas no mês</div><div class="v">${summary.total}</div></div>
    <div class="stat-tile"><div class="t">Promovidos</div><div class="v">${summary.promovidos}</div></div>
    <div class="stat-tile"><div class="t">Taxa de qualificação</div><div class="v">${qualifGeral}%</div></div>
    <div class="stat-tile bonus"><div class="t">Bônus total do mês</div><div class="v">${money(summary.bonus)}</div></div>
  </div>

  <section>
    <h2>Ranking do mês — por taxa de qualificação (ICP A + B)</h2>
    ${linhasRanking}
  </section>

  <section>
    <h2>Detalhamento por pesquisador</h2>
    <table>
      <thead>
        <tr>
          <th>Pesquisador</th><th class="num">Pesquisas</th><th class="num">ICP A</th><th class="num">ICP B</th>
          <th class="num">ICP C</th><th class="num">Sem perfil/Não aval.</th><th class="num">Taxa qualif.</th>
          <th class="num">Promovidos</th><th class="num">Bônus válido</th>
        </tr>
      </thead>
      <tbody>${linhasTabela || '<tr><td colspan="9" class="muted">Nenhuma pesquisa registrada neste mês.</td></tr>'}</tbody>
    </table>
  </section>

  ${metaRows.length > 0 ? `
  <section>
    <h2>Metas de pesquisa — semana e mês correntes</h2>
    <table>
      <thead><tr><th>Pesquisador</th><th class="num">Semana</th><th class="num">Mês</th></tr></thead>
      <tbody>${linhasMetas}</tbody>
    </table>
  </section>` : ''}

  <footer>Bônus só é válido quando a pesquisa vira empresa de verdade (status "Promovido" em Pesquisa de Leads) — este relatório é só consulta, não substitui a folha de pagamento.</footer>
</body>
</html>`

  const win = window.open('', '_blank')
  if (!win) return
  win.document.write(html)
  win.document.close()
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

function MetaBar({ label, atual, meta }) {
  const pct = metaPct(atual, meta)
  return (
    <div className="meta-bar">
      <span className="meta-bar-label">{label}</span>
      {meta ? (
        <>
          <div className="bar-track">
            <div className={`bar-fill meta-fill ${qualClass(pct)}`} style={{ width: `${Math.min(100, pct)}%` }} />
          </div>
          <span className={`qual-pill ${qualClass(pct)}`}>{atual}/{meta}</span>
        </>
      ) : (
        <span className="meta-no-goal">{atual} pesquisa{atual === 1 ? '' : 's'} · sem meta definida</span>
      )}
    </div>
  )
}

function MetaRow({ row }) {
  return (
    <div className="meta-row">
      <div className="row-resp"><span className="avatar">{initials(row.pesquisador_nome)}</span>{row.pesquisador_nome}</div>
      <div className="meta-bars">
        <MetaBar label="Semana" atual={row.pesquisas_semana} meta={row.meta_semanal} />
        <MetaBar label="Mês" atual={row.pesquisas_mes} meta={row.meta_mensal} />
      </div>
    </div>
  )
}

export default function DesempenhoPesquisaTab({ setTab }) {
  const [helpOpen, setHelpOpen] = useState(false)
  const options = useMemo(mesOptions, [])
  const [mes, setMes] = useState(options[0].value)
  const [pesquisadorFiltro, setPesquisadorFiltro] = useState('')

  const usersQuery = useQuery({ queryKey: ['users', 'for-desempenho'], queryFn: () => listUsers({ size: 100 }), retry: false })
  const users = usersQuery.data?.items ?? []

  const reportQuery = useQuery({
    queryKey: ['lead-prospects', 'performance-report', mes],
    queryFn: () => getPerformanceReport(mes),
    retry: false,
  })

  const metasQuery = useQuery({
    queryKey: ['lead-prospects', 'metas'],
    queryFn: getMetasProgress,
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

  const allRows = reportQuery.data?.rows ?? []
  const rows = pesquisadorFiltro ? allRows.filter((r) => r.pesquisador_id === pesquisadorFiltro) : allRows
  const summary = rows.reduce((acc, r) => ({
    total: acc.total + r.total,
    promovidos: acc.promovidos + r.promovidos,
    bonus: acc.bonus + r.bonus_valido,
    aeb: acc.aeb + r.icp_a + r.icp_b,
  }), { total: 0, promovidos: 0, bonus: 0, aeb: 0 })
  const qualifGeral = summary.total ? Math.round((summary.aeb / summary.total) * 100) : 0

  const ranking = [...rows].sort((a, b) => b.taxa_qualificacao - a.taxa_qualificacao || b.promovidos - a.promovidos)
  const maxTotal = Math.max(1, ...rows.map((r) => r.total))
  const metaRows = metasQuery.data?.rows ?? []
  const mesLabel = options.find((o) => o.value === mes)?.label ?? mes
  const pesquisadorNome = pesquisadorFiltro ? users.find((u) => u.id === pesquisadorFiltro)?.nome : null

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Desempenho de Pesquisa</h1>
          <p>Gamificação e bônus por pesquisador — a tela de consumo do que é calculado em Pesquisa de Leads</p>
        </div>
        <div className="page-actions">
          <button
            className="btn-ghost"
            disabled={rows.length === 0}
            onClick={() => abrirRelatorioHtml({ mesLabel, pesquisadorNome, rows, summary, qualifGeral, ranking, metaRows })}
          >
            📄 Ver relatório
          </button>
        </div>
      </header>

      <div className="content">
        <div className="tabs-row">
          <div className="segmented">
            <button onClick={() => setTab('leads')}>Pesquisa de Leads</button>
            <button className="active">Desempenho</button>
          </div>
        </div>

        <div className="filters-bar">
          <select className="filter-select" value={mes} onChange={(e) => setMes(e.target.value)}>
            {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select className="filter-select" value={pesquisadorFiltro} onChange={(e) => setPesquisadorFiltro(e.target.value)}>
            <option value="">Todos os pesquisadores</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
        </div>

        <button className="info-trigger" onClick={() => setHelpOpen(true)}>
          <IconInfo /> Como funciona o bônus
        </button>

        {metaRows.length > 0 && (
          <div className="card meta-card">
            <div className="card-head">
              <h2>Metas de pesquisa</h2>
              <p>Semana e mês correntes — sempre "hoje", independente do mês filtrado acima</p>
            </div>
            <div className="card-body">
              {metaRows.map((r) => <MetaRow key={r.pesquisador_id} row={r} />)}
            </div>
          </div>
        )}

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
                          <th style={{ textAlign: 'right' }}>Pesquisas</th>
                          <th style={{ textAlign: 'right' }}>ICP A</th>
                          <th style={{ textAlign: 'right' }}>ICP B</th>
                          <th style={{ textAlign: 'right' }}>ICP C</th>
                          <th style={{ textAlign: 'right' }}>Sem perfil/Não aval.</th>
                          <th style={{ textAlign: 'right' }}>Taxa qualif.</th>
                          <th style={{ textAlign: 'right' }}>Promovidos</th>
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

      {helpOpen && (
        <div className="scrim show" onClick={() => setHelpOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3><IconInfo />Como funciona o bônus</h3>
            <p className="sub">
              Bônus só é <strong>válido</strong> quando a pesquisa vira empresa de verdade (status
              &quot;Promovido&quot; em Pesquisa de Leads) — completar os campos não basta. Esse relatório é só
              consulta; não existe módulo de folha de pagamento aqui.
            </p>
            <div className="row"><button className="btn-ghost" onClick={() => setHelpOpen(false)}>Fechar</button></div>
          </div>
        </div>
      )}
    </>
  )
}
