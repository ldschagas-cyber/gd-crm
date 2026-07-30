import { useEffect, useState } from 'react'
import {
  bulkAddPublicCompanies, getCnaeSimilares, searchCnaeCodes, searchPublicCompanies,
} from '../api/publicCompanies'
import '../styles/dataTable.css'
import './BuscarEmpresasPage.css'

const UF_REGIAO = {
  AC: 'Norte', AP: 'Norte', AM: 'Norte', PA: 'Norte', RO: 'Norte', RR: 'Norte', TO: 'Norte',
  AL: 'Nordeste', BA: 'Nordeste', CE: 'Nordeste', MA: 'Nordeste', PB: 'Nordeste', PE: 'Nordeste',
  PI: 'Nordeste', RN: 'Nordeste', SE: 'Nordeste',
  DF: 'Centro-Oeste', GO: 'Centro-Oeste', MT: 'Centro-Oeste', MS: 'Centro-Oeste',
  ES: 'Sudeste', MG: 'Sudeste', RJ: 'Sudeste', SP: 'Sudeste',
  PR: 'Sul', RS: 'Sul', SC: 'Sul',
}
const REGIOES = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']
const NIVEIS = [
  { v: 'subclasse', l: 'Só este código' },
  { v: 'classe', l: 'Mesma Classe' },
  { v: 'grupo', l: 'Mesmo Grupo' },
  { v: 'divisao', l: 'Mesma Divisão' },
]
const PORTES = ['MICRO EMPRESA', 'EMPRESA DE PEQUENO PORTE', 'DEMAIS']

function IconInfo() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="10" cy="10" r="7.3" />
      <path d="M10 9v4.2" strokeLinecap="round" />
      <circle cx="10" cy="6.8" r=".9" fill="currentColor" stroke="none" />
    </svg>
  )
}

export default function BuscarEmpresasPage() {
  const [helpOpen, setHelpOpen] = useState(false)
  const [cnaeBusca, setCnaeBusca] = useState('')
  const [cnaeOpcoes, setCnaeOpcoes] = useState([])
  const [cnaeAlvo, setCnaeAlvo] = useState(null)
  const [nivel, setNivel] = useState('classe')
  const [similares, setSimilares] = useState([])
  const [incluidos, setIncluidos] = useState({})

  const [regiao, setRegiao] = useState('')
  const [uf, setUf] = useState('')
  const [porte, setPorte] = useState('')

  const [resultados, setResultados] = useState([])
  const [cursor, setCursor] = useState(null)
  const [buscou, setBuscou] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selecionados, setSelecionados] = useState({})
  const [addStatus, setAddStatus] = useState(null)
  const [ocultarCadastradas, setOcultarCadastradas] = useState(false)

  useEffect(() => {
    if (cnaeBusca.trim().length < 2) { setCnaeOpcoes([]); return }
    const handle = setTimeout(() => {
      searchCnaeCodes(cnaeBusca.trim()).then(setCnaeOpcoes).catch(() => setCnaeOpcoes([]))
    }, 300)
    return () => clearTimeout(handle)
  }, [cnaeBusca])

  useEffect(() => {
    if (!cnaeAlvo) { setSimilares([]); setIncluidos({}); return }
    getCnaeSimilares(cnaeAlvo.codigo, nivel).then((lista) => {
      setSimilares(lista)
      setIncluidos(Object.fromEntries(lista.map((c) => [c.codigo, true])))
    }).catch(() => { setSimilares([]); setIncluidos({}) })
  }, [cnaeAlvo, nivel])

  function escolherCnae(c) {
    setCnaeAlvo(c)
    setCnaeBusca(`${c.codigo} — ${c.descricao}`)
    setCnaeOpcoes([])
  }

  function toggleIncluido(codigo) {
    setIncluidos((s) => ({ ...s, [codigo]: !s[codigo] }))
  }

  function handleRegiaoChange(r) {
    setRegiao(r)
    if (r && uf && UF_REGIAO[uf] !== r) setUf('')
  }

  const ufsDisponiveis = Object.keys(UF_REGIAO)
    .filter((u) => !regiao || UF_REGIAO[u] === regiao)
    .sort()

  const cnaeSelecionados = similares.filter((c) => incluidos[c.codigo]).map((c) => c.codigo)

  async function buscar(cursorAtual = null) {
    if (cnaeSelecionados.length === 0) {
      setError('Selecione um CNAE de referência antes de buscar — a busca não funciona só com UF/região/porte.')
      return
    }
    setLoading(true)
    setError(null)
    setAddStatus(null)
    try {
      const resp = await searchPublicCompanies({
        cnae: cnaeSelecionados, regiao: regiao ? [regiao] : [], uf: uf ? [uf] : [],
        porte: porte || undefined, cursor: cursorAtual,
      })
      setResultados((prev) => (cursorAtual ? [...prev, ...resp.data] : resp.data))
      setCursor(resp.cursor)
      setBuscou(true)
    } catch {
      setError('A base pública de CNPJ está indisponível no momento. Tente novamente em instantes.')
    } finally {
      setLoading(false)
    }
  }

  function toggleSelecionado(cnpj) {
    setSelecionados((s) => ({ ...s, [cnpj]: !s[cnpj] }))
  }

  const selecionadosIds = Object.keys(selecionados).filter((id) => selecionados[id])
  const qtdJaCadastradas = resultados.filter((r) => r.ja_cadastrado).length
  const resultadosVisiveis = ocultarCadastradas ? resultados.filter((r) => !r.ja_cadastrado) : resultados

  async function adicionarSelecionados() {
    const empresas = resultados
      .filter((r) => selecionados[r.cnpj])
      .map((r) => ({
        cnpj: r.cnpj, razao_social: r.razao_social, uf: r.uf, cnae_fiscal_descricao: r.cnae_fiscal_descricao,
      }))
    if (empresas.length === 0) return
    setAddStatus('loading')
    try {
      const resp = await bulkAddPublicCompanies(empresas)
      setAddStatus(`${resp.criados} adicionada(s) à Pesquisa de Leads${resp.ignorados ? `, ${resp.ignorados} já existente(s) ignorada(s)` : ''}.`)
      setResultados((prev) => prev.map((r) => (selecionados[r.cnpj] ? { ...r, ja_cadastrado: true } : r)))
      setSelecionados({})
    } catch {
      setAddStatus('Não foi possível adicionar as empresas selecionadas agora.')
    }
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Buscar Empresas</h1>
          <p>Descubra empresas-alvo por CNAE e região, direto da base pública de CNPJ</p>
        </div>
      </header>

      <div className="content">
        <button className="info-trigger" onClick={() => setHelpOpen(true)}>
          <IconInfo /> Como funciona a busca
        </button>

        <div className="filters-bar">
          <div className="search cnae-picker">
            <input
              type="text" placeholder="CNAE por código ou descrição (ex.: supermercado)"
              value={cnaeBusca}
              onChange={(e) => { setCnaeBusca(e.target.value); setCnaeAlvo(null) }}
            />
            {cnaeOpcoes.length > 0 && (
              <div className="cnae-options">
                {cnaeOpcoes.map((c) => (
                  <div key={c.codigo} className="cnae-option" onClick={() => escolherCnae(c)}>
                    <span className="mono">{c.codigo}</span> {c.descricao}
                  </div>
                ))}
              </div>
            )}
          </div>
          <select className="filter-select" value={regiao} onChange={(e) => handleRegiaoChange(e.target.value)}>
            <option value="">Toda região</option>
            {REGIOES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select className="filter-select" value={uf} onChange={(e) => setUf(e.target.value)}>
            <option value="">Toda UF</option>
            {ufsDisponiveis.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
          <select className="filter-select" value={porte} onChange={(e) => setPorte(e.target.value)}>
            <option value="">Todos os portes</option>
            {PORTES.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        {cnaeAlvo && (
          <div className="card" style={{ padding: 18, marginTop: 16 }}>
            <div className="f-group">
              <div className="f-label">Nível de semelhança</div>
              <div className="segmented" style={{ marginLeft: 0 }}>
                {NIVEIS.map((n) => (
                  <button key={n.v} className={nivel === n.v ? 'active' : ''} onClick={() => setNivel(n.v)}>{n.l}</button>
                ))}
              </div>
            </div>

            <div className="f-group" style={{ marginBottom: 0 }}>
              <div className="f-label">CNAEs incluídos na busca ({cnaeSelecionados.length} de {similares.length})</div>
              <div className="cnae-checklist">
                {similares.map((c) => (
                  <label key={c.codigo} className="col-option">
                    <input type="checkbox" checked={!!incluidos[c.codigo]} onChange={() => toggleIncluido(c.codigo)} />
                    <span className="mono">{c.codigo}</span> {c.descricao}
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        <button
          className="btn-primary" style={{ marginTop: 16 }}
          disabled={loading}
          onClick={() => buscar(null)}
        >
          {loading && !buscou ? 'Buscando…' : 'Buscar'}
        </button>

        {error && <p className="state-msg error">{error}</p>}

        {buscou && (
          <div className="card" style={{ marginTop: 16 }}>
            {selecionadosIds.length > 0 && (
              <div className="bulk-bar show">
                <span><b>{selecionadosIds.length}</b> selecionada(s)</span>
                <div className="link-btn">
                  <a onClick={adicionarSelecionados}>Adicionar à Pesquisa de Leads</a>
                </div>
              </div>
            )}
            {addStatus && addStatus !== 'loading' && <p className="state-msg">{addStatus}</p>}

            {resultados.length > 0 && qtdJaCadastradas > 0 && (
              <label className="col-option" style={{ marginBottom: 12 }}>
                <input
                  type="checkbox" checked={ocultarCadastradas}
                  onChange={(e) => setOcultarCadastradas(e.target.checked)}
                />
                Ocultar já cadastradas ({qtdJaCadastradas})
              </label>
            )}

            {resultadosVisiveis.length === 0 && !loading && (
              <p className="empty-cell">
                {resultados.length === 0
                  ? 'Nenhuma empresa encontrada com esses filtros.'
                  : 'Todas as empresas encontradas já estão cadastradas.'}
              </p>
            )}

            {resultadosVisiveis.length > 0 && (
              <div className="table-scroll">
                <table className="data">
                  <thead>
                    <tr>
                      <th className="checkbox-col" />
                      <th>Empresa</th>
                      <th>UF</th>
                      <th>CNAE</th>
                      <th>Porte</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultadosVisiveis.map((r) => (
                      <tr key={r.cnpj} className={selecionados[r.cnpj] ? 'row-selected' : ''}>
                        <td className="checkbox-col">
                          <input
                            type="checkbox" checked={!!selecionados[r.cnpj]} disabled={r.ja_cadastrado}
                            onChange={() => toggleSelecionado(r.cnpj)}
                          />
                        </td>
                        <td>
                          <div className="row-title">{r.razao_social}{r.ja_cadastrado && <span className="badge-default" style={{ marginLeft: 8 }}>Já cadastrada</span>}</div>
                          <div className="row-sub">{r.cnpj}</div>
                        </td>
                        <td>{r.uf}</td>
                        <td>{r.cnae_fiscal_descricao}</td>
                        <td>{r.porte}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {cursor && (
              <div className="pagination">
                <span />
                <button className="btn-ghost" disabled={loading} onClick={() => buscar(cursor)}>
                  {loading ? 'Carregando…' : 'Carregar mais'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {helpOpen && (
        <div className="scrim show" onClick={() => setHelpOpen(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3><IconInfo />Como funciona a busca</h3>
            <p className="sub">
              Busca sobre a base pública de CNPJ (minha-receita.org, dados da Receita Federal). Escolha um CNAE
              de referência e o nível de semelhança — os códigos incluídos aparecem abaixo, editáveis. Sem busca
              por nome de empresa: os filtros disponíveis são CNAE, região/UF e porte.
            </p>
            <div className="row"><button className="btn-ghost" onClick={() => setHelpOpen(false)}>Fechar</button></div>
          </div>
        </div>
      )}
    </>
  )
}
