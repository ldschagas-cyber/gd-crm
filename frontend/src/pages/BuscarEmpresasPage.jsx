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

export default function BuscarEmpresasPage() {
  const [cnaeBusca, setCnaeBusca] = useState('')
  const [cnaeOpcoes, setCnaeOpcoes] = useState([])
  const [cnaeAlvo, setCnaeAlvo] = useState(null)
  const [nivel, setNivel] = useState('classe')
  const [similares, setSimilares] = useState([])
  const [incluidos, setIncluidos] = useState({})

  const [regioes, setRegioes] = useState([])
  const [ufs, setUfs] = useState([])
  const [porte, setPorte] = useState('')

  const [resultados, setResultados] = useState([])
  const [cursor, setCursor] = useState(null)
  const [buscou, setBuscou] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selecionados, setSelecionados] = useState({})
  const [addStatus, setAddStatus] = useState(null)

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

  function toggleRegiao(r) {
    setRegioes((s) => (s.includes(r) ? s.filter((x) => x !== r) : [...s, r]))
  }

  function toggleUf(u) {
    setUfs((s) => (s.includes(u) ? s.filter((x) => x !== u) : [...s, u]))
  }

  const ufsDisponiveis = Object.keys(UF_REGIAO)
    .filter((u) => regioes.length === 0 || regioes.includes(UF_REGIAO[u]))
    .sort()

  const cnaeSelecionados = similares.filter((c) => incluidos[c.codigo]).map((c) => c.codigo)

  async function buscar(cursorAtual = null) {
    if (cnaeSelecionados.length === 0) return
    setLoading(true)
    setError(null)
    setAddStatus(null)
    try {
      const resp = await searchPublicCompanies({
        cnae: cnaeSelecionados, regiao: regioes, uf: ufs, porte: porte || undefined, cursor: cursorAtual,
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
        <div className="help-card">
          <span>
            Busca sobre a base pública de CNPJ (minha-receita.org, dados da Receita Federal). Escolha um CNAE de
            referência e o nível de semelhança — os códigos incluídos aparecem abaixo, editáveis. Sem busca por
            nome de empresa: os filtros disponíveis são CNAE, região/UF e porte.
          </span>
        </div>

        <div className="card" style={{ padding: 18, marginTop: 16 }}>
          <div className="f-group">
            <div className="f-label">CNAE de referência</div>
            <div className="cnae-picker">
              <input
                className="f-input" type="text" placeholder="Buscar por código ou descrição (ex.: supermercado)"
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
          </div>

          {cnaeAlvo && (
            <>
              <div className="f-group">
                <div className="f-label">Nível de semelhança</div>
                <div className="segmented" style={{ marginLeft: 0 }}>
                  {NIVEIS.map((n) => (
                    <button key={n.v} className={nivel === n.v ? 'active' : ''} onClick={() => setNivel(n.v)}>{n.l}</button>
                  ))}
                </div>
              </div>

              <div className="f-group">
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
            </>
          )}

          <div className="f-row">
            <div className="f-group">
              <div className="f-label">Região</div>
              <div className="chip-row">
                {REGIOES.map((r) => (
                  <label key={r} className="chip-toggle">
                    <input type="checkbox" checked={regioes.includes(r)} onChange={() => toggleRegiao(r)} />
                    {r}
                  </label>
                ))}
              </div>
            </div>
            <div className="f-group">
              <div className="f-label">Porte <span className="opt">opcional</span></div>
              <select className="f-select" value={porte} onChange={(e) => setPorte(e.target.value)}>
                <option value="">Todos os portes</option>
                {PORTES.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>

          <div className="f-group">
            <div className="f-label">UF <span className="opt">refinamento opcional dentro da região</span></div>
            <div className="chip-row">
              {ufsDisponiveis.map((u) => (
                <label key={u} className="chip-toggle">
                  <input type="checkbox" checked={ufs.includes(u)} onChange={() => toggleUf(u)} />
                  {u}
                </label>
              ))}
            </div>
          </div>

          <button
            className="btn-primary" disabled={cnaeSelecionados.length === 0 || loading}
            onClick={() => buscar(null)}
          >
            {loading && !buscou ? 'Buscando…' : 'Buscar'}
          </button>
        </div>

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

            {resultados.length === 0 && !loading && <p className="empty-cell">Nenhuma empresa encontrada com esses filtros.</p>}

            {resultados.length > 0 && (
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
                    {resultados.map((r) => (
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
    </>
  )
}
