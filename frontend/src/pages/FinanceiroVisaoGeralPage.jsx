import { useQuery } from '@tanstack/react-query'
import { getFinanceiroResumo } from '../api/financeiro'
import { formatCurrency, formatPct } from '../utils/format'
import '../styles/dataTable.css'
import '../styles/financeiro.css'

const PENDENCIA_LABEL = { vencida: 'Vencida', vigencia: 'Vigência', reajuste: 'Reajuste' }

export default function FinanceiroVisaoGeralPage() {
  const resumoQuery = useQuery({ queryKey: ['financeiro', 'resumo'], queryFn: getFinanceiroResumo })
  const r = resumoQuery.data

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Financeiro — Visão Geral</h1>
          <p>Indicadores de faturamento, recebíveis e margem</p>
        </div>
      </header>

      <div className="content">
        {resumoQuery.isLoading && <p className="state-msg">Carregando indicadores…</p>}
        {resumoQuery.isError && <p className="state-msg error">Não foi possível carregar os indicadores agora.</p>}

        {r && (
          <>
            <section className="stat-strip">
              <div className="stat-tile">
                <div className="t">MRR</div>
                <div className="v">{formatCurrency(r.mrr)}</div>
                <div className="sub">{r.contratos_ativos} contrato(s) ativo(s)</div>
              </div>
              <div className="stat-tile">
                <div className="t">A receber no mês</div>
                <div className="v ok">{formatCurrency(r.a_receber_mes)}</div>
              </div>
              <div className="stat-tile">
                <div className="t">Vencidos</div>
                <div className="v bad">{formatCurrency(r.vencidos)}</div>
                <div className="sub">{r.vencidos_qtd} cobrança(s)</div>
              </div>
              <div className="stat-tile">
                <div className="t">Margem cedida</div>
                <div className="v warn">{formatPct(r.margem_cedida_pct)}</div>
                <div className="sub">desconto médio no trimestre</div>
              </div>
            </section>

            <div className="card">
              <div className="card-head"><h2>Pendências</h2></div>
              <div className="table-scroll">
                <table className="data">
                  <tbody>
                    {r.pendencias.map((p, i) => (
                      <tr key={i}>
                        <td style={{ width: 110 }}>
                          <span className={`fin-pill p-${p.tipo}`}>{PENDENCIA_LABEL[p.tipo] ?? p.tipo}</span>
                        </td>
                        <td>{p.titulo}</td>
                        <td className="num">{p.valor != null ? formatCurrency(p.valor) : ''}</td>
                      </tr>
                    ))}
                    {r.pendencias.length === 0 && (
                      <tr><td className="empty-cell">Nenhuma pendência no momento.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card-head">
                <h2>Margem cedida por vendedor</h2>
                <p>Desconto médio das propostas no trimestre</p>
              </div>
              <div className="table-scroll">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Vendedor</th>
                      <th className="num">Propostas</th>
                      <th className="num">Desc. médio</th>
                      <th className="num">Máx. concedido</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.margem_por_vendedor.map((m) => (
                      <tr key={m.vendedor_id ?? 'sem'}>
                        <td><div className="row-title">{m.vendedor_nome}</div></td>
                        <td className="num">{m.propostas}</td>
                        <td className="num">{formatPct(m.desconto_medio_pct)}</td>
                        <td className="num">{formatPct(m.desconto_max_pct)}</td>
                      </tr>
                    ))}
                    {r.margem_por_vendedor.length === 0 && (
                      <tr><td colSpan={4} className="empty-cell">Sem propostas no período.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
