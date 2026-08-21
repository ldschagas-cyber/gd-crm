import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createProduto, getHistoricoPreco, listProdutos, updateProduto } from '../api/produtos'
import { formatCurrency, formatDate } from '../utils/format'
import '../styles/dataTable.css'
import '../styles/financeiro.css'

export default function ProdutosPage() {
  const queryClient = useQueryClient()
  const [drawer, setDrawer] = useState(undefined) // undefined=fechado, null=novo, obj=editar
  const [histProduto, setHistProduto] = useState(null)

  const listQuery = useQuery({ queryKey: ['produtos', 'list'], queryFn: () => listProdutos({ size: 200 }) })
  const items = listQuery.data?.items ?? []

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['produtos'] })
  const createMutation = useMutation({ mutationFn: createProduto, onSuccess: () => { setDrawer(undefined); invalidate() } })
  const updateMutation = useMutation({ mutationFn: ({ id, data }) => updateProduto(id, data), onSuccess: () => { setDrawer(undefined); invalidate() } })

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Produtos e Serviços</h1>
          <p>{items.length} item(ns) no catálogo</p>
        </div>
        <button className="btn-primary" onClick={() => setDrawer(null)}>+ Novo produto</button>
      </header>

      <div className="content">
        <div className="card">
          {listQuery.isLoading && <p className="state-msg">Carregando catálogo…</p>}
          {listQuery.isError && <p className="state-msg error">Não foi possível carregar o catálogo.</p>}
          {listQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>Produto</th>
                    <th>Tipo</th>
                    <th className="num">Preço tabela</th>
                    <th className="num">Piso</th>
                    <th>Status</th>
                    <th className="actions-col"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((p) => (
                    <tr key={p.id}>
                      <td><div className="row-title">{p.nome}</div>{p.descricao && <div className="row-sub">{p.descricao}</div>}</td>
                      <td><span className={`fin-pill ${p.tipo === 'recorrente' ? 'p-blue' : 'p-neu'}`}>{p.tipo === 'recorrente' ? 'Recorrente' : 'Pontual'}</span></td>
                      <td className="num">{formatCurrency(p.preco_tabela, { cents: true })}{p.tipo === 'recorrente' ? '/mês' : ''}</td>
                      <td className="num">{formatCurrency(p.preco_minimo, { cents: true })}</td>
                      <td><span className={`fin-pill ${p.ativo ? 'p-ok' : 'p-off'}`}>{p.ativo ? 'Ativo' : 'Inativo'}</span></td>
                      <td className="actions-col">
                        <button className="icon-btn" title="Editar" onClick={() => setDrawer(p)}>✎</button>
                        <button className="icon-btn" title="Histórico de preço" onClick={() => setHistProduto(p)}>↺</button>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && <tr><td colSpan={6} className="empty-cell">Nenhum produto cadastrado.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
          <p className="fin-note"><b>RN-F13:</b> alterar o preço de tabela não muda propostas e contratos existentes — o preço é congelado no item na criação. O piso é referência; o bloqueio automático abaixo dele é da fase de governança.</p>
        </div>
      </div>

      {drawer !== undefined && (
        <ProdutoDrawer
          produto={drawer}
          onClose={() => setDrawer(undefined)}
          onSubmit={(data) => { if (drawer) updateMutation.mutate({ id: drawer.id, data }); else createMutation.mutate(data) }}
          submitting={createMutation.isPending || updateMutation.isPending}
          error={createMutation.error || updateMutation.error}
        />
      )}

      {histProduto && <HistoricoModal produto={histProduto} onClose={() => setHistProduto(null)} />}
    </>
  )
}

function ProdutoDrawer({ produto, onClose, onSubmit, submitting, error }) {
  const [nome, setNome] = useState(produto?.nome ?? '')
  const [descricao, setDescricao] = useState(produto?.descricao ?? '')
  const [tipo, setTipo] = useState(produto?.tipo ?? 'recorrente')
  const [precoTabela, setPrecoTabela] = useState(produto?.preco_tabela ?? '')
  const [precoMinimo, setPrecoMinimo] = useState(produto?.preco_minimo ?? '')
  const [ativo, setAtivo] = useState(produto?.ativo ?? true)
  const [touched, setTouched] = useState(false)

  const okNome = nome.trim().length > 0
  const tabela = parseFloat(precoTabela) || 0
  const piso = parseFloat(precoMinimo) || 0
  const okPreco = tabela >= 0
  const okPiso = piso <= tabela

  function handleSubmit(e) {
    e.preventDefault()
    setTouched(true)
    if (!okNome || !okPreco || !okPiso) return
    onSubmit({
      nome: nome.trim(), descricao: descricao.trim() || null, tipo,
      preco_tabela: tabela, preco_minimo: piso, ativo,
    })
  }

  return (
    <div className="scrim show" onClick={onClose}>
      <div className="drawer show" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div><h2>{produto ? 'Editar produto' : 'Novo produto'}</h2><p>Catálogo com preço de tabela e piso</p></div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="drawer-body">
            <div className="f-group">
              <label className="f-label">Nome <span className="req">*</span></label>
              <input className={`f-input${touched && !okNome ? ' err' : ''}`} value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ex.: Consultoria logística contínua" />
              <span className={`f-err${touched && !okNome ? ' show' : ''}`}>Informe o nome do produto.</span>
            </div>
            <div className="f-group">
              <label className="f-label">Descrição</label>
              <textarea className="f-textarea" value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder="Opcional" />
            </div>
            <div className="f-group">
              <label className="f-label">Tipo</label>
              <div className="segmented">
                <button type="button" className={tipo === 'recorrente' ? 'active' : ''} onClick={() => setTipo('recorrente')}>Recorrente</button>
                <button type="button" className={tipo === 'pontual' ? 'active' : ''} onClick={() => setTipo('pontual')}>Pontual</button>
              </div>
            </div>
            <div className="f-row">
              <div className="f-group">
                <label className="f-label">Preço de tabela <span className="req">*</span></label>
                <input type="number" step="0.01" min="0" className="f-input" value={precoTabela} onChange={(e) => setPrecoTabela(e.target.value)} placeholder="0,00" />
              </div>
              <div className="f-group">
                <label className="f-label">Piso (preço mínimo)</label>
                <input type="number" step="0.01" min="0" className={`f-input${touched && !okPiso ? ' err' : ''}`} value={precoMinimo} onChange={(e) => setPrecoMinimo(e.target.value)} placeholder="0,00" />
                <span className={`f-err${touched && !okPiso ? ' show' : ''}`}>O piso não pode ser maior que o preço de tabela.</span>
              </div>
            </div>
            <label className="f-check">
              <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} /> Produto ativo
            </label>
            {error && <p className="state-msg error">{error.response?.data?.error?.message ?? 'Não foi possível salvar.'}</p>}
          </div>
          <div className="drawer-foot">
            <button type="button" className="btn-ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Salvando…' : 'Salvar produto'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function HistoricoModal({ produto, onClose }) {
  const histQuery = useQuery({ queryKey: ['produtos', produto.id, 'hist'], queryFn: () => getHistoricoPreco(produto.id) })
  const hist = histQuery.data ?? []
  return (
    <div className="scrim show" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <h3>Histórico de preço — {produto.nome}</h3>
        {histQuery.isLoading && <p className="state-msg">Carregando…</p>}
        {hist.length === 0 && !histQuery.isLoading && <p className="sub">Nenhuma alteração de preço registrada.</p>}
        {hist.length > 0 && (
          <table className="data">
            <thead><tr><th>Data</th><th className="num">Anterior</th><th className="num">Novo</th></tr></thead>
            <tbody>
              {hist.map((h) => (
                <tr key={h.id}>
                  <td>{formatDate(h.created_at)}</td>
                  <td className="num">{h.preco_anterior != null ? formatCurrency(h.preco_anterior, { cents: true }) : '—'}</td>
                  <td className="num">{formatCurrency(h.preco_novo, { cents: true })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="row"><button className="btn-ghost" onClick={onClose}>Fechar</button></div>
      </div>
    </div>
  )
}
