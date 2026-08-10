import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getFunilMetasResumo } from '../api/funilMetas'
import { getFunilMetasConfig, updateFunilMetasConfig } from '../api/tenant'
import '../styles/dataTable.css'
import './FunilMetasPage.css'

function formatCurrency(v) {
  return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}

// Ordem fixa das etapas (espelha app/schemas/funil_metas.py) — "pesquisadas" é a base,
// as demais têm % esperado da etapa anterior configurável.
const ETAPAS_CHAVES = ['decisores', 'contatos', 'reunioes', 'diagnosticos', 'propostas', 'fechados']
const NOMES = {
  decisores: 'Decisores identificados', contatos: 'Contatos realizados', reunioes: 'Reuniões marcadas',
  diagnosticos: 'Diagnósticos realizados', propostas: 'Propostas enviadas', fechados: 'Clientes fechados',
}
// Referência de mercado (Anexo 1) — só exibição, não vem da API (é texto fixo de contexto,
// não um número calculado). Ver docs/PLANO_METAS_FUNIL.md §2.
const REFERENCIAS = {
  pesquisadas: 'Base de prospecção (topo).',
  decisores: '30–50% é comum em prospecção ativa com ICP bem definido.',
  contatos: '40–60% dos decisores mapeados costumam ser efetivamente contatados.',
  reunioes: '17–31% é a média nacional contato→oportunidade (outbound: ~17%); meta interna está acima da média.',
  diagnosticos: 'Sem benchmark direto — etapa específica do modelo GD; alinhada à faixa saudável de 20–40% por etapa em B2B consultivo.',
  propostas: 'Alinhada à faixa saudável de 20–40% por etapa em B2B consultivo.',
  fechados: '6–10% é a média de fechamento (SQL→cliente) em consultorias e serviços profissionais; meta interna está bem acima.',
}
const STATUS_LABEL = { ok: 'ok', atencao: 'atenção', critico: 'crítico' }
const COLORS = ['var(--seq-1)', 'var(--seq-2)', 'var(--seq-3)', 'var(--seq-4)', 'var(--seq-5)', 'var(--seq-6)', 'var(--good)']

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
function fmt(n) { return Number(n ?? 0).toLocaleString('pt-BR') }
function pct1(n) {
  if (n == null) return '—'
  return (Math.round(n * 10) / 10).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

export default function FunilMetasPage() {
  const queryClient = useQueryClient()
  const options = useMemo(mesOptions, [])
  const [mes, setMes] = useState(options[0].value)
  const [modo, setModo] = useState('atividade')
  const [editOpen, setEditOpen] = useState(false)

  const resumoQuery = useQuery({
    queryKey: ['funil-metas', 'resumo', modo, mes],
    queryFn: () => getFunilMetasResumo(modo, mes),
    retry: false,
  })
  const configQuery = useQuery({ queryKey: ['funil-metas', 'config'], queryFn: getFunilMetasConfig, retry: false })

  const saveMutation = useMutation({
    mutationFn: updateFunilMetasConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['funil-metas'] })
      setEditOpen(false)
    },
  })

  if (resumoQuery.isError) {
    return (
      <>
        <header className="topbar"><div className="topbar-title"><h1>Metas do Funil</h1></div></header>
        <div className="content"><p className="state-msg error">Só administradores e gestores podem ver este controle.</p></div>
      </>
    )
  }

  const etapas = resumoQuery.data?.etapas ?? []
  const mesLabel = (options.find((o) => o.value === mes)?.label ?? mes).toLowerCase()
  const top = etapas[0]
  const bottom = etapas[etapas.length - 1]
  const pior = etapas.reduce((acc, e) => (
    e.diferenca_pp != null && (acc == null || e.diferenca_pp < acc.diferenca_pp) ? e : acc
  ), null)
  const maxScale = top ? Math.max(top.meta, top.real, 1) : 1

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Metas do Funil</h1>
          <p>Controle de mudança de fase por percentual — Empresas pesquisadas → Clientes fechados</p>
        </div>
        <div className="page-actions">
          <button className="btn-ghost" disabled={configQuery.isLoading} onClick={() => setEditOpen(true)}>
            ⚙ Editar metas
          </button>
        </div>
      </header>

      <div className="content">
        <div className="filters-bar">
          <div className="segmented">
            <button className={modo === 'atividade' ? 'active' : ''} onClick={() => setModo('atividade')}>Atividade do mês</button>
            <button className={modo === 'coorte' ? 'active' : ''} onClick={() => setModo('coorte')}>Coorte do período</button>
          </div>
          <select className="filter-select" value={mes} onChange={(e) => setMes(e.target.value)}>
            {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <span className="fm-modo-hint">
            {modo === 'coorte'
              ? 'Segue as mesmas empresas pesquisadas no período até hoje, mesmo que o marco tenha ocorrido depois.'
              : 'Conta eventos ocorridos no período, qualquer que seja a origem da empresa.'}
          </span>
        </div>

        {resumoQuery.isLoading ? (
          <p className="state-msg">Carregando…</p>
        ) : etapas.length === 0 ? (
          <p className="state-msg">Sem dados para este período.</p>
        ) : (
          <>
            <div className="stat-strip">
              <div className="stat-tile">
                <div className="t">Empresas pesquisadas</div>
                <div className="v">{fmt(top.real)} <small>/ {fmt(top.meta)}</small></div>
              </div>
              <div className="stat-tile">
                <div className="t">Clientes fechados</div>
                <div className="v">{fmt(bottom.real)} <small>/ {fmt(bottom.meta)}</small></div>
              </div>
              <div className="stat-tile">
                <div className="t">Conversão geral (topo → fechado)</div>
                <div className="v">{pct1((bottom.real / (top.real || 1)) * 100)}%</div>
                <div className="fm-sub">meta: {pct1((bottom.meta / (top.meta || 1)) * 100)}%</div>
              </div>
              <div className="stat-tile">
                <div className="t">Etapa mais crítica</div>
                <div className="v fm-tile-nome">{pior ? pior.nome : '—'}</div>
                {pior && pior.diferenca_pp != null && (
                  <div className={`fm-sub fm-status-${pior.status}`}>{pct1(Math.abs(pior.diferenca_pp))} p.p. vs. meta</div>
                )}
              </div>
            </div>

            {pior?.status === 'critico' && (
              <div className="fm-alert">
                <span className="fm-alert-dot" />
                <div>
                  <h3>Etapa crítica: {pior.nome}</h3>
                  <p>
                    Conversão real de <b>{pct1(pior.pct_real_etapa_anterior)}%</b> fica{' '}
                    <b>{pct1(Math.abs(pior.diferenca_pp))} p.p.</b> abaixo da meta interna ({pior.pct_meta_etapa_anterior}%).{' '}
                    {REFERENCIAS[pior.chave]} Sinal para revisar critério de qualificação ou execução da cadência nesta
                    etapa antes de abrir mais volume no topo do funil — não necessariamente de que a meta esteja errada.
                  </p>
                </div>
              </div>
            )}

            <div className="card">
              <div className="card-head">
                <div><h3>Funil de {mesLabel} — meta vs. real</h3><p>Barra clara = meta; barra colorida = realizado no período</p></div>
              </div>
              <div className="fm-funnel">
                {etapas.map((e, i) => {
                  const metaW = (e.meta / maxScale) * 100
                  const realW = (e.real / maxScale) * 100
                  return (
                    <div className="fm-row" key={e.chave}>
                      <div className="fm-name"><b>{e.nome}</b></div>
                      <div className="fm-track-wrap">
                        <div className="fm-track">
                          <div className="fm-meta-fill" style={{ width: `${metaW}%` }} />
                          <div className="fm-real-fill" style={{ width: `${realW}%`, background: COLORS[i] }} />
                        </div>
                      </div>
                      <div className="fm-nums">
                        <div className="real">{fmt(e.real)}</div><div className="of">meta {fmt(e.meta)}</div>
                        {e.chave === 'propostas' && resumoQuery.data?.propostas_valor_aberto != null && (
                          <Link to="/previsao-comercial" className="fm-revenue-chip" title="Ver detalhamento em Previsão Comercial">
                            {formatCurrency(resumoQuery.data.propostas_valor_aberto)} em aberto →
                          </Link>
                        )}
                        {e.chave === 'fechados' && resumoQuery.data?.fechados_valor_realizado != null && (
                          <Link to="/previsao-comercial" className="fm-revenue-chip" title="Ver detalhamento em Previsão Comercial">
                            {formatCurrency(resumoQuery.data.fechados_valor_realizado)} realizado →
                          </Link>
                        )}
                      </div>
                      <div className="fm-pct-cell">
                        {i === 0 ? <span className="fm-muted">topo</span> : (
                          <>
                            <span className={`fm-real-pct fm-status-${e.status}`}>{pct1(e.pct_real_etapa_anterior)}%</span>
                            <span className={`fm-diff fm-status-${e.status}`}>
                              {e.diferenca_pp >= 0 ? '+' : '−'}{pct1(Math.abs(e.diferenca_pp))} p.p. vs. meta {e.pct_meta_etapa_anterior}%
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {resumoQuery.data?.propostas_valor_aberto != null && (
              <div className="fm-revenue-callout">
                <div>
                  <h3>Quer ver isso em receita, não em contagem?</h3>
                  <p>
                    Previsão Comercial mostra a mesma etapa "Propostas enviadas" em R$, ponderada por probabilidade e
                    quebrada por vendedor — inclui o Commit que cada um confirmou pra este mês.
                  </p>
                </div>
                <Link to="/previsao-comercial" className="btn-primary">Ver por vendedor →</Link>
              </div>
            )}

            <div className="card">
              <div className="card-head">
                <div><h3>Anexo 1 — detalhamento dos percentuais</h3><p>Meta, % esperado da etapa anterior e referência de mercado (B2B consultivo, ticket alto)</p></div>
              </div>
              <div className="table-scroll">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Etapa</th><th>Meta</th><th>% etapa anterior</th><th>Real</th>
                      <th>% real da etapa anterior</th><th>Diferença</th><th>Status</th><th>Referência de mercado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {etapas.map((e, i) => (
                      <tr key={e.chave} className={i === 0 ? '' : `fm-row-${e.status}`}>
                        <td className="row-title">{e.nome}</td>
                        <td>{fmt(e.meta)}</td>
                        <td>{i === 0 ? '—' : `${e.pct_meta_etapa_anterior}%`}</td>
                        <td>{fmt(e.real)}</td>
                        <td>{i === 0 ? '—' : `${pct1(e.pct_real_etapa_anterior)}%`}</td>
                        <td className={i === 0 ? '' : `fm-status-${e.status}`}>
                          {i === 0 ? '—' : `${e.diferenca_pp >= 0 ? '+' : '−'}${pct1(Math.abs(e.diferenca_pp))} p.p.`}
                        </td>
                        <td>{i === 0 ? null : <span className={`status-pill fm-status-pill-${e.status}`}>{STATUS_LABEL[e.status]}</span>}</td>
                        <td className="fm-ref">{REFERENCIAS[e.chave]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>

      {editOpen && (
        <EditMetasDrawer
          config={configQuery.data}
          onClose={() => setEditOpen(false)}
          onSave={(data) => saveMutation.mutate(data)}
          submitting={saveMutation.isPending}
        />
      )}
    </>
  )
}

function EditMetasDrawer({ config, onClose, onSave, submitting }) {
  const [base, setBase] = useState(config?.empresas_pesquisadas_meta ?? 300)
  const [pcts, setPcts] = useState(() => {
    const map = {}
    ETAPAS_CHAVES.forEach((c) => {
      map[c] = config?.etapas?.find((e) => e.chave === c)?.pct_etapa_anterior ?? 0
    })
    return map
  })

  const metas = useMemo(() => {
    const m = { pesquisadas: Number(base) || 0 }
    let anterior = 'pesquisadas'
    ETAPAS_CHAVES.forEach((c) => {
      m[c] = Math.round((m[anterior] * (Number(pcts[c]) || 0)) / 100)
      anterior = c
    })
    return m
  }, [base, pcts])

  function handleSave() {
    onSave({
      empresas_pesquisadas_meta: Number(base) || 0,
      etapas: ETAPAS_CHAVES.map((c) => ({ chave: c, pct_etapa_anterior: Number(pcts[c]) || 0 })),
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>Editar metas do funil</h2>
            <p>Meta absoluta de cada etapa é sempre derivada a partir de "Empresas pesquisadas" e dos percentuais abaixo.</p>
          </div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <div className="drawer-body">
          <div className="f-group">
            <label className="f-label">Empresas pesquisadas (meta)</label>
            <input className="f-input" type="number" min="1" value={base} onChange={(e) => setBase(e.target.value)} />
          </div>
          {ETAPAS_CHAVES.map((c) => (
            <div className="f-group" key={c}>
              <label className="f-label">
                {NOMES[c]}
                <span className="fm-derived">meta recalculada: {fmt(metas[c])}</span>
              </label>
              <div className="fm-pct-input">
                <input
                  className="f-input" type="number" min="0" max="100" value={pcts[c]}
                  onChange={(e) => setPcts((p) => ({ ...p, [c]: e.target.value }))}
                />
                <span className="fm-suffix">%</span>
              </div>
            </div>
          ))}
          <p className="f-hint">
            A meta absoluta de cada etapa nunca é editada diretamente — evita os dois ficarem inconsistentes entre si.
          </p>
        </div>
        <div className="drawer-foot">
          <button className="btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn-primary" disabled={submitting} onClick={handleSave}>
            {submitting ? 'Salvando…' : 'Salvar metas'}
          </button>
        </div>
      </div>
    </div>
  )
}
