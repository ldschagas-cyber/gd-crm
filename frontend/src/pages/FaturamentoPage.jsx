import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { gerarFaturamento, getFaturamento, reenviarNf } from '../api/faturamento'
import { listCompanies } from '../api/companies'
import { formatCurrency, formatDate, competenciaLabel } from '../utils/format'
import '../styles/dataTable.css'
import '../styles/financeiro.css'

const STATUS = {
  aberta: { label: 'Aberta', cls: 'p-neu' },
  paga: { label: 'Paga', cls: 'p-ok' },
  vencida: { label: 'Vencida', cls: 'p-bad' },
  cancelada: { label: 'Cancelada', cls: 'p-off' },
}

function competenciaAtual() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

export default function FaturamentoPage() {
  const queryClient = useQueryClient()
  const [competencia, setCompetencia] = useState(competenciaAtual())
  const [banner, setBanner] = useState(null) // {kind:'ok'|'warn', text}

  const fatQuery = useQuery({ queryKey: ['faturamento', competencia], queryFn: () => getFaturamento(competencia) })
  const companiesQuery = useQuery({ queryKey: ['companies', 'for-select'], queryFn: () => listCompanies({ size: 200 }) })
  const companiesById = useMemo(() => Object.fromEntries((companiesQuery.data?.items ?? []).map((c) => [c.id, c.razao_social])), [companiesQuery.data])

  const cobrancas = fatQuery.data?.cobrancas ?? []
  const totais = useMemo(() => {
    const total = cobrancas.reduce((s, c) => s + (c.status !== 'cancelada' ? c.valor : 0), 0)
    const semNf = cobrancas.filter((c) => !c.nf_numero && !c.nf_solicitada_em && c.status !== 'cancelada').length
    return { total, semNf, qtd: cobrancas.length }
  }, [cobrancas])

  function aplicarResultado(res) {
    if (res.nf_email_enviado) {
      setBanner({ kind: 'ok', text: `${res.geradas} cobrança(s) gerada(s), ${res.ja_existentes} já existiam. Pedido de NF enviado ao contador (${res.nf_solicitadas} cobrança(s)).` })
    } else if (res.nf_aviso) {
      setBanner({ kind: 'warn', text: `${res.geradas} cobrança(s) gerada(s), ${res.ja_existentes} já existiam. NF não enviada: ${res.nf_aviso}` })
    } else {
      setBanner({ kind: 'ok', text: `${res.geradas} cobrança(s) gerada(s), ${res.ja_existentes} já existiam.` })
    }
  }

  const gerarMutation = useMutation({
    mutationFn: () => gerarFaturamento(competencia),
    onSuccess: (res) => {
      aplicarResultado(res)
      queryClient.invalidateQueries({ queryKey: ['faturamento'] })
      queryClient.invalidateQueries({ queryKey: ['financeiro'] })
    },
  })
  const reenviarMutation = useMutation({
    mutationFn: () => reenviarNf(competencia),
    onSuccess: (res) => {
      setBanner(res.nf_email_enviado
        ? { kind: 'ok', text: `Pedido de NF reenviado ao contador (${res.nf_solicitadas} cobrança(s)).` }
        : { kind: 'warn', text: `NF não enviada: ${res.nf_aviso ?? 'nada pendente'}.` })
      queryClient.invalidateQueries({ queryKey: ['faturamento'] })
    },
  })

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Faturamento — {competenciaLabel(competencia)}</h1>
          <p>Geração recorrente e pedido de NF ao contador</p>
        </div>
        <div className="page-actions">
          <input type="month" className="f-input" value={competencia} onChange={(e) => { setCompetencia(e.target.value); setBanner(null) }} style={{ width: 150 }} />
          <button className="btn-ghost" disabled={reenviarMutation.isPending || totais.semNf === 0} onClick={() => reenviarMutation.mutate()}>Reenviar NF ao contador</button>
          <button className="btn-primary" disabled={gerarMutation.isPending} onClick={() => gerarMutation.mutate()}>{gerarMutation.isPending ? 'Gerando…' : 'Gerar faturamento do mês'}</button>
        </div>
      </header>

      <div className="content">
        {banner && <div className={`fin-banner ${banner.kind}`}>{banner.text}</div>}

        <section className="stat-strip">
          <div className="stat-tile"><div className="t">Total da competência</div><div className="v">{formatCurrency(totais.total)}</div><div className="sub">{totais.qtd} cobrança(s)</div></div>
          <div className="stat-tile"><div className="t">Sem NF</div><div className="v warn">{totais.semNf}</div><div className="sub">aguardando emissão</div></div>
        </section>

        <div className="card">
          <div className="card-head"><h2>Cobranças da competência {competenciaLabel(competencia)}</h2></div>
          {fatQuery.isLoading && <p className="state-msg">Carregando cobranças…</p>}
          {fatQuery.isError && <p className="state-msg error">Não foi possível carregar as cobranças.</p>}
          {fatQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr><th>Cliente</th><th>Tipo</th><th>Venc.</th><th className="num">Valor</th><th>NF</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {cobrancas.map((c) => (
                    <tr key={c.id}>
                      <td>{companiesById[c.company_id] ?? '—'}<div className="row-sub">{c.descricao}</div></td>
                      <td><span className={`fin-pill ${c.tipo === 'recorrente' ? 'p-blue' : 'p-neu'}`}>{c.tipo === 'recorrente' ? 'Recorrente' : 'Pontual'}</span></td>
                      <td>{formatDate(c.vencimento)}</td>
                      <td className="num">{formatCurrency(c.valor, { cents: true })}</td>
                      <td><NfCell cobranca={c} /></td>
                      <td><span className={`fin-pill ${STATUS[c.status]?.cls ?? 'p-neu'}`}>{STATUS[c.status]?.label ?? c.status}</span></td>
                    </tr>
                  ))}
                  {cobrancas.length === 0 && <tr><td colSpan={6} className="empty-cell">Nenhuma cobrança nesta competência. Clique em “Gerar faturamento do mês”.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
          <p className="fin-note"><b>RN-F02:</b> a geração é idempotente (uma cobrança por contrato + competência) — reprocessar não duplica. O sistema não emite NFS-e: no faturamento, dispara um e-mail ao contador com as cobranças que precisam de NF (o contador emite). Configure o e-mail do contador em Configurações.</p>
        </div>
      </div>
    </>
  )
}

function NfCell({ cobranca }) {
  if (cobranca.nf_numero) return <span className="fin-pill p-ok">NF {cobranca.nf_numero}</span>
  if (cobranca.nf_solicitada_em) return <span className="fin-pill p-gold">NF solicitada</span>
  return <span style={{ color: '#6b7086' }}>sem NF</span>
}
