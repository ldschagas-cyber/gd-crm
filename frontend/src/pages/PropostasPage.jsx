import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createProposta, listPropostas, mudarStatusProposta } from '../api/propostas'
import { listProdutos } from '../api/produtos'
import { listCompanies } from '../api/companies'
import { listUsers } from '../api/users'
import { formatCurrency, formatPct } from '../utils/format'
import '../styles/dataTable.css'
import '../styles/financeiro.css'

const STATUS = {
  rascunho: { label: 'Rascunho', cls: 'p-neu' },
  enviada: { label: 'Enviada', cls: 'p-blue' },
  em_negociacao: { label: 'Em negociação', cls: 'p-neu' },
  aceita: { label: 'Aceita ✓', cls: 'p-ok' },
  recusada: { label: 'Recusada', cls: 'p-bad' },
  expirada: { label: 'Expirada', cls: 'p-off' },
}
// Próximas transições oferecidas como ação (espelha o backend PropostaService._TRANSICOES).
const ACOES = {
  rascunho: [['enviada', 'Enviar']],
  enviada: [['aceita', 'Aceitar'], ['em_negociacao', 'Negociar'], ['recusada', 'Recusar']],
  em_negociacao: [['aceita', 'Aceitar'], ['recusada', 'Recusar']],
}

function descontoPct(tabela, proposto) {
  const t = parseFloat(tabela) || 0
  if (t <= 0) return 0
  return (1 - (parseFloat(proposto) || 0) / t) * 100
}

export default function PropostasPage() {
  const queryClient = useQueryClient()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const listQuery = useQuery({ queryKey: ['propostas', 'list'], queryFn: () => listPropostas({ size: 100 }) })
  const companiesQuery = useQuery({ queryKey: ['companies', 'for-select'], queryFn: () => listCompanies({ size: 200 }) })
  const usersQuery = useQuery({ queryKey: ['users', 'for-select'], queryFn: () => listUsers({ size: 200 }) })
  const produtosQuery = useQuery({ queryKey: ['produtos', 'ativos'], queryFn: () => listProdutos({ size: 200, ativo: true }) })

  const items = listQuery.data?.items ?? []
  const companiesById = useMemo(() => Object.fromEntries((companiesQuery.data?.items ?? []).map((c) => [c.id, c.razao_social])), [companiesQuery.data])
  const usersById = useMemo(() => Object.fromEntries((usersQuery.data?.items ?? []).map((u) => [u.id, u.nome])), [usersQuery.data])

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['propostas'] })
  const createMutation = useMutation({ mutationFn: createProposta, onSuccess: () => { setDrawerOpen(false); invalidate() } })
  const statusMutation = useMutation({
    mutationFn: ({ id, status }) => mudarStatusProposta(id, status),
    onSuccess: () => { invalidate(); queryClient.invalidateQueries({ queryKey: ['financeiro'] }) },
  })

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Propostas</h1>
          <p>{items.length} proposta(s)</p>
        </div>
        <button className="btn-primary" onClick={() => setDrawerOpen(true)}>+ Nova proposta</button>
      </header>

      <div className="content">
        <div className="card">
          {listQuery.isLoading && <p className="state-msg">Carregando propostas…</p>}
          {listQuery.isError && <p className="state-msg error">Não foi possível carregar as propostas.</p>}
          {listQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>Proposta</th><th>Cliente</th><th>Vendedor</th><th>Versão</th>
                    <th className="num">Tabela</th><th className="num">Proposto</th><th className="num">Desc.</th>
                    <th>Status</th><th className="actions-col"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((p) => (
                    <tr key={p.id}>
                      <td className="mono">{p.numero}</td>
                      <td>{companiesById[p.company_id] ?? '—'}</td>
                      <td>{p.vendedor_id ? (usersById[p.vendedor_id] ?? '—') : '—'}</td>
                      <td className="mono">v{p.versao}</td>
                      <td className="num">{formatCurrency(p.valor_tabela_total, { cents: true })}</td>
                      <td className="num">{formatCurrency(p.valor_proposto_total, { cents: true })}</td>
                      <td className="num" style={p.desconto_pct_total >= 20 ? { color: '#b3403a', fontWeight: 700 } : undefined}>{formatPct(p.desconto_pct_total)}</td>
                      <td><span className={`fin-pill ${STATUS[p.status]?.cls ?? 'p-neu'}`}>{STATUS[p.status]?.label ?? p.status}</span></td>
                      <td className="actions-col">
                        {(ACOES[p.status] ?? []).map(([st, label]) => (
                          <button
                            key={st}
                            className="btn-ghost sm"
                            disabled={statusMutation.isPending}
                            onClick={() => {
                              if (st === 'aceita' && !confirm('Aceitar a proposta gera um contrato. Continuar?')) return
                              statusMutation.mutate({ id: p.id, status: st })
                            }}
                          >
                            {label}
                          </button>
                        ))}
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && <tr><td colSpan={9} className="empty-cell">Nenhuma proposta cadastrada.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
          <p className="fin-note"><b>RN-F09 (captura):</b> o desconto é sempre calculado (tabela − proposto) e registrado por item — alimenta a margem cedida no dashboard. Nesta fase não há fila de alçada/aprovação nem bloqueio de piso (governança → fase seguinte). Aceitar a proposta gera o contrato.</p>
        </div>
      </div>

      {drawerOpen && (
        <PropostaDrawer
          companies={companiesQuery.data?.items ?? []}
          users={usersQuery.data?.items ?? []}
          produtos={produtosQuery.data?.items ?? []}
          onClose={() => setDrawerOpen(false)}
          onSubmit={(data) => createMutation.mutate(data)}
          submitting={createMutation.isPending}
          error={createMutation.error}
        />
      )}
    </>
  )
}

function PropostaDrawer({ companies, users, produtos, onClose, onSubmit, submitting, error }) {
  const [companyId, setCompanyId] = useState('')
  const [vendedorId, setVendedorId] = useState('')
  const [validade, setValidade] = useState('')
  const [linhas, setLinhas] = useState([{ produto_id: '', preco_proposto: '', quantidade: 1 }])
  const [touched, setTouched] = useState(false)

  const produtosById = useMemo(() => Object.fromEntries(produtos.map((p) => [p.id, p])), [produtos])

  function setLinha(i, patch) {
    setLinhas((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)))
  }
  function addLinha() { setLinhas((ls) => [...ls, { produto_id: '', preco_proposto: '', quantidade: 1 }]) }
  function removeLinha(i) { setLinhas((ls) => ls.filter((_, idx) => idx !== i)) }

  function onProdutoChange(i, produto_id) {
    const prod = produtosById[produto_id]
    setLinha(i, { produto_id, preco_proposto: prod ? String(prod.preco_tabela) : '' })
  }

  const totais = useMemo(() => {
    let tabela = 0, proposto = 0
    for (const l of linhas) {
      const prod = produtosById[l.produto_id]
      if (!prod) continue
      const qtd = parseInt(l.quantidade) || 0
      tabela += (parseFloat(prod.preco_tabela) || 0) * qtd
      proposto += (parseFloat(l.preco_proposto) || 0) * qtd
    }
    return { tabela, proposto, desconto: descontoPct(tabela, proposto) }
  }, [linhas, produtosById])

  const okCliente = Boolean(companyId)
  const okItens = linhas.length > 0 && linhas.every((l) => l.produto_id && (parseFloat(l.preco_proposto) >= 0) && (parseInt(l.quantidade) >= 1))

  function handleSubmit(e) {
    e.preventDefault()
    setTouched(true)
    if (!okCliente || !okItens) return
    onSubmit({
      company_id: companyId,
      vendedor_id: vendedorId || null,
      validade: validade || null,
      itens: linhas.map((l) => ({ produto_id: l.produto_id, preco_proposto: parseFloat(l.preco_proposto), quantidade: parseInt(l.quantidade) })),
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show wide" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div><h2>Nova proposta</h2><p>Itens do catálogo com captura de desconto</p></div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Cliente <span className="req">*</span></label>
                <select className={`f-input${touched && !okCliente ? ' err' : ''}`} value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
                  <option value="">Selecione…</option>
                  {companies.map((c) => <option key={c.id} value={c.id}>{c.razao_social}</option>)}
                </select>
                <span className={`f-err${touched && !okCliente ? ' show' : ''}`}>Selecione o cliente.</span>
              </div>
              <div className="f-group">
                <label className="f-label">Vendedor</label>
                <select className="f-input" value={vendedorId} onChange={(e) => setVendedorId(e.target.value)}>
                  <option value="">—</option>
                  {users.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
                </select>
              </div>
            </div>
            <div className="f-group">
              <label className="f-label">Validade</label>
              <input type="date" className="f-input" value={validade} onChange={(e) => setValidade(e.target.value)} />
            </div>

            <div className="f-group">
              <label className="f-label">Itens <span className="req">*</span></label>
              <div className="item-head item-row">
                <span>Produto</span><span>Tabela</span><span>Proposto</span><span>Qtd</span><span></span>
              </div>
              {linhas.map((l, i) => {
                const prod = produtosById[l.produto_id]
                const desc = prod ? descontoPct(prod.preco_tabela, l.preco_proposto) : 0
                return (
                  <div className="item-row" key={i}>
                    <select className="f-input" value={l.produto_id} onChange={(e) => onProdutoChange(i, e.target.value)}>
                      <option value="">Selecione…</option>
                      {produtos.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
                    </select>
                    <span className="calc">{prod ? formatCurrency(prod.preco_tabela, { cents: true }) : '—'}</span>
                    <input type="number" step="0.01" min="0" className="f-input" value={l.preco_proposto} onChange={(e) => setLinha(i, { preco_proposto: e.target.value })} placeholder="0,00" />
                    <input type="number" min="1" className="f-input" value={l.quantidade} onChange={(e) => setLinha(i, { quantidade: e.target.value })} />
                    <button type="button" className="icon-btn danger" title="Remover" onClick={() => removeLinha(i)} disabled={linhas.length === 1}>✕</button>
                    {prod && <span className="calc" style={{ gridColumn: '1 / -1', color: desc >= 20 ? '#b3403a' : '#6b7086' }}>Desconto do item: {formatPct(desc)}</span>}
                  </div>
                )
              })}
              <button type="button" className="btn-ghost sm" onClick={addLinha}>+ Adicionar item</button>
            </div>

            <div className="preview-card">
              <div className="preview-label">Totais</div>
              <div className="preview-body">
                Tabela: <b>{formatCurrency(totais.tabela, { cents: true })}</b> ·
                Proposto: <b>{formatCurrency(totais.proposto, { cents: true })}</b> ·
                Desconto: <b style={{ color: totais.desconto >= 20 ? '#b3403a' : undefined }}>{formatPct(totais.desconto)}</b>
              </div>
            </div>

            {error && <p className="state-msg error">{error.response?.data?.error?.message ?? 'Não foi possível salvar.'}</p>}
          </div>
          <div className="drawer-foot">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Criar proposta'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
