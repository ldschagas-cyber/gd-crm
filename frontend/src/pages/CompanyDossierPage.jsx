import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  askCompanyAi, getCompany, getCompanyIcp, regenerateCompanyResumo, updateCompanyDossier,
} from '../api/companies'
import { listContacts } from '../api/contacts'
import { listTimeline } from '../api/timeline'
import CompanyTabs from '../components/CompanyTabs.jsx'
import '../styles/detailPage.css'
import './CompanyDetailPage.css'
import './CompanyDossierPage.css'

function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}
function formatCurrency(v) {
  return v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}
function tempoDecorrido(iso) {
  if (!iso) return null
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (min < 1) return 'agora mesmo'
  if (min < 60) return `há ${min} min`
  const h = Math.round(min / 60)
  if (h < 24) return `há ${h} h`
  return `há ${Math.round(h / 24)} d`
}
function tipoGlyph(tipo) {
  const map = { nota: '📝', ligacao: '📞', email: '✉️', reuniao: '📅', pipeline: '📈', tarefa: '✔️', cadastro: '●' }
  return map[tipo] ?? '●'
}

function ManualField({ label, value, placeholder, onSave, saving }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value ?? '')

  if (!editing) {
    return (
      <div className="manual-field">
        <span className="m-label">{label}</span>
        <button className="m-edit" onClick={() => { setDraft(value ?? ''); setEditing(true) }}>editar</button>
        <div className="m-value">{value || <span className="m-empty">{placeholder}</span>}</div>
      </div>
    )
  }
  return (
    <div className="manual-field editing">
      <span className="m-label">{label}</span>
      <textarea value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={placeholder} autoFocus />
      <div className="m-edit-actions">
        <button className="btn-ghost" onClick={() => setEditing(false)} disabled={saving}>Cancelar</button>
        <button
          className="composer-submit"
          disabled={saving}
          onClick={() => onSave(draft, () => setEditing(false))}
        >
          Salvar
        </button>
      </div>
    </div>
  )
}

export default function CompanyDossierPage() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const [timelineFilter, setTimelineFilter] = useState('all')
  const [pergunta, setPergunta] = useState('')
  const [conversa, setConversa] = useState([])

  const companyQuery = useQuery({ queryKey: ['companies', 'detail', id], queryFn: () => getCompany(id) })
  const icpQuery = useQuery({ queryKey: ['companies', 'icp', id], queryFn: () => getCompanyIcp(id) })
  const timelineQuery = useQuery({ queryKey: ['timeline', id], queryFn: () => listTimeline(id) })
  const contactsQuery = useQuery({ queryKey: ['contacts', 'mini', id], queryFn: () => listContacts({ companyId: id, size: 3 }) })

  const invalidateCompany = () => queryClient.invalidateQueries({ queryKey: ['companies', 'detail', id] })

  const dossierMutation = useMutation({
    mutationFn: (data) => updateCompanyDossier(id, data),
    onSuccess: invalidateCompany,
  })
  const regenerateMutation = useMutation({
    mutationFn: () => regenerateCompanyResumo(id),
    onSuccess: invalidateCompany,
  })
  const askMutation = useMutation({
    mutationFn: (texto) => askCompanyAi(id, texto),
    onSuccess: (data, texto) => setConversa((prev) => [...prev, { pergunta: texto, ...data }]),
  })

  if (companyQuery.isLoading) return <div className="content"><p className="state-msg">Carregando…</p></div>
  if (companyQuery.isError) return <div className="content"><p className="state-msg error">Empresa não encontrada.</p></div>

  const company = companyQuery.data
  const icp = icpQuery.data
  const timelineItems = (timelineQuery.data?.items ?? []).filter(
    (e) => timelineFilter === 'all' || e.tipo === timelineFilter,
  )
  const emails = (timelineQuery.data?.items ?? []).filter((e) => e.tipo === 'email').slice(0, 3)
  const reunioes = (timelineQuery.data?.items ?? []).filter((e) => e.tipo === 'reuniao').slice(0, 3)
  const contatoPrincipal = contactsQuery.data?.items?.[0]

  const saveField = (field) => (value, done) => {
    dossierMutation.mutate({ [field]: value }, { onSuccess: done })
  }

  return (
    <>
      <header className="topbar">
        <div className="breadcrumb">
          <Link to="/empresas">Empresas</Link>
          <span>/</span>
          <span className="current">{company.razao_social}</span>
        </div>
      </header>

      <div className="content">
        <CompanyTabs companyId={id} />

        <div className="dossie-wrap">

          {/* Empresa */}
          <section className="card co-header">
            <div className="co-header-top">
              <div className="co-logo">{initials(company.razao_social)}</div>
              <div className="co-title-block">
                <div className="co-title-row"><h1>{company.razao_social}</h1></div>
                {company.nome_fantasia && <p className="co-sub">{company.nome_fantasia}</p>}
                <div className="co-tags">
                  {company.segmento && <span className="tag">{company.segmento}</span>}
                  {company.cidade && <span className="tag">{company.cidade}{company.uf ? `, ${company.uf}` : ''}</span>}
                  {company.origem && <span className="tag">{company.origem}</span>}
                </div>
              </div>
            </div>
          </section>

          {/* Resumo Executivo */}
          <section className="card card-pad">
            <div className="card-head">
              <div><h3>Resumo executivo</h3><p>O que você precisa saber antes de ligar</p></div>
              <span className="ia-badge"><span className="pulse" /> Gerado por IA</span>
            </div>
            {company.resumo_executivo ? (
              <p className="resumo-text">{company.resumo_executivo}</p>
            ) : (
              <p className="resumo-text muted">
                Ainda não há resumo gerado — será criado automaticamente assim que houver um evento registrado
                nesta empresa (ligação, e-mail, reunião ou nota).
              </p>
            )}
            <div className="resumo-foot">
              <span className="resumo-meta">
                {company.resumo_executivo_atualizado_em
                  ? `Atualizado automaticamente · ${tempoDecorrido(company.resumo_executivo_atualizado_em)} · monitora novos eventos na timeline`
                  : 'Ainda não gerado'}
              </span>
              <button className="link-btn" disabled={regenerateMutation.isPending} onClick={() => regenerateMutation.mutate()}>
                {regenerateMutation.isPending ? 'Gerando…' : 'Atualizar agora ↻'}
              </button>
            </div>
          </section>

          {/* ICP + Score */}
          <section className="card card-pad">
            <div className="card-head"><div><h3>Perfil de encaixe (ICP)</h3></div></div>
            {icp && (
              <>
                <div className="icp-row">
                  <div className={`icp-fit fit-${icp.fit === 'Sem Perfil' || icp.fit === 'Não avaliado' ? 'baixo' : icp.fit.toLowerCase()}`}>
                    <span className="letter">{icp.fit === 'Não avaliado' ? '—' : icp.fit}</span>
                    <span className="cap">FIT ICP</span>
                  </div>
                  <div className="icp-score">
                    <span className="icp-score-num">{icp.score}</span><span className="icp-score-den"> / 100</span>
                    <div className="icp-score-bar"><span style={{ width: `${icp.score}%` }} /></div>
                    {icp.breakdown.length > 0 ? (
                      <div className="icp-breakdown">
                        {icp.breakdown.map((b) => (
                          <span className="icp-chip" key={b.criterio}>{b.criterio}: {b.valor} <b>+{b.pontos}</b></span>
                        ))}
                      </div>
                    ) : (
                      <p className="icp-note">Sem setor, região ou porte preenchidos ainda — edite a empresa pra calcular o fit.</p>
                    )}
                  </div>
                </div>
              </>
            )}
          </section>

          {/* Perfil */}
          <section className="card card-pad">
            <div className="card-head"><div><h3>Perfil da empresa</h3></div></div>
            <dl className="stat-row">
              <div className="stat"><dt>Segmento</dt><dd className="stat-text">{company.segmento || '—'}</dd></div>
              <div className="stat"><dt>Faturamento estimado</dt><dd>{formatCurrency(company.faturamento_estimado)}</dd></div>
              <div className="stat"><dt>Funcionários</dt><dd>{company.num_funcionarios?.toLocaleString('pt-BR') ?? '—'}</dd></div>
            </dl>
          </section>

          {/* Stack operacional */}
          <section className="card card-pad">
            <div className="card-head"><div><h3>Stack operacional</h3><p>Transportadoras, ERP e TMS — preenchido manualmente na descoberta</p></div></div>
            <div className="manual-grid">
              <ManualField label="Transportadoras" value={company.transportadoras} placeholder="Ex.: Braspress (capital), Jamef (interior)…"
                          onSave={saveField('transportadoras')} saving={dossierMutation.isPending} />
              <ManualField label="ERP" value={company.erp} placeholder="Ex.: TOTVS Protheus"
                          onSave={saveField('erp')} saving={dossierMutation.isPending} />
              <ManualField label="TMS" value={company.tms} placeholder="Ex.: Nenhum — planilha"
                          onSave={saveField('tms')} saving={dossierMutation.isPending} />
            </div>
          </section>

          {/* Descoberta */}
          <section className="card card-pad">
            <div className="card-head"><div><h3>Descoberta</h3><p>Problemas encontrados e hipóteses — texto livre</p></div></div>
            <div className="discovery-grid">
              <div className="discovery-box problemas">
                <ManualField label="⚠ Problemas encontrados" value={company.problemas_encontrados} placeholder="O que já foi identificado como dor…"
                            onSave={saveField('problemas_encontrados')} saving={dossierMutation.isPending} />
              </div>
              <div className="discovery-box hipoteses">
                <ManualField label="💡 Hipóteses" value={company.hipoteses} placeholder="O que ainda é especulação a validar…"
                            onSave={saveField('hipoteses')} saving={dossierMutation.isPending} />
              </div>
            </div>
          </section>

          {/* Histórico / Linha do tempo */}
          <section className="card">
            <div className="card-pad" style={{ paddingBottom: 0 }}><h3>Histórico</h3><p>Linha do tempo — todo o histórico de interações</p></div>
            <div className="filter-row">
              {['all', 'ligacao', 'email', 'reuniao', 'nota'].map((f) => (
                <button key={f} className={`filter-chip${timelineFilter === f ? ' active' : ''}`} onClick={() => setTimelineFilter(f)}>
                  {{ all: 'Tudo', ligacao: 'Ligações', email: 'E-mails', reuniao: 'Reuniões', nota: 'Notas' }[f]}
                </button>
              ))}
            </div>
            <div className="timeline">
              {timelineQuery.isLoading && <p className="state-msg">Carregando…</p>}
              {timelineItems.map((e) => (
                <div className="tl-item" key={e.id}>
                  <div className={`tl-icon t-${e.tipo}`}>{tipoGlyph(e.tipo)}</div>
                  <div className="tl-body">
                    <div className="tl-title">{e.titulo}</div>
                    {e.descricao && <div className="tl-desc">{e.descricao}</div>}
                    <div className="tl-meta"><span>{new Date(e.created_at).toLocaleString('pt-BR')}</span></div>
                  </div>
                </div>
              ))}
              {timelineQuery.data && timelineItems.length === 0 && <p className="state-msg">Nenhum evento com esse filtro.</p>}
            </div>
          </section>

          {/* Contato */}
          <section className="card">
            <div className="card-pad" style={{ paddingBottom: 0 }}><h3>Contato principal</h3></div>
            <div className="contact-row">
              {contatoPrincipal ? (
                <>
                  <span className="avatar">{initials(contatoPrincipal.nome)}</span>
                  <div className="contact-main">
                    <div className="contact-name">{contatoPrincipal.nome}</div>
                    <div className="contact-role">{contatoPrincipal.cargo ?? '—'}</div>
                    <div className="contact-links">
                      {contatoPrincipal.email && <a href={`mailto:${contatoPrincipal.email}`}>{contatoPrincipal.email}</a>}
                      {contatoPrincipal.telefone && <a href={`tel:${contatoPrincipal.telefone}`}>{contatoPrincipal.telefone}</a>}
                    </div>
                  </div>
                </>
              ) : <p className="state-msg">Nenhum contato cadastrado ainda.</p>}
            </div>
          </section>

          {/* Últimos e-mails / reuniões */}
          <section className="card">
            <div className="card-pad" style={{ paddingBottom: 0 }}><h3>Recentes</h3><p>Últimos e-mails e reuniões</p></div>
            <div className="two-col">
              <div>
                <div className="mini-list">
                  {emails.map((e) => (
                    <div className="mini-row" key={e.id}>
                      <div className="mini-main"><div className="mini-title">{e.titulo}</div>{e.descricao && <div className="mini-sub">{e.descricao}</div>}</div>
                      <span className="mini-when">{new Date(e.created_at).toLocaleDateString('pt-BR')}</span>
                    </div>
                  ))}
                  {emails.length === 0 && <p className="state-msg">Nenhum e-mail registrado.</p>}
                </div>
              </div>
              <div>
                <div className="mini-list">
                  {reunioes.map((e) => (
                    <div className="mini-row" key={e.id}>
                      <div className="mini-main"><div className="mini-title">{e.titulo}</div>{e.descricao && <div className="mini-sub">{e.descricao}</div>}</div>
                      <span className="mini-when">{new Date(e.created_at).toLocaleDateString('pt-BR')}</span>
                    </div>
                  ))}
                  {reunioes.length === 0 && <p className="state-msg">Nenhuma reunião registrada.</p>}
                </div>
              </div>
            </div>
          </section>

          {/* IA / Copiloto */}
          <section className="card card-pad copilot-card">
            <div className="copilot-head">
              <span className="copilot-icon">✦</span>
              <div><h3>Copiloto do dossiê</h3></div>
            </div>

            {company.proxima_acao_sugerida && (
              <div className="nba">
                <div>
                  <div className="nba-label">Próxima ação sugerida</div>
                  <div className="nba-text">{company.proxima_acao_sugerida}</div>
                </div>
              </div>
            )}

            <div className="ask-box">
              <form
                className="ask-input-row"
                onSubmit={(e) => {
                  e.preventDefault()
                  if (!pergunta.trim() || askMutation.isPending) return
                  askMutation.mutate(pergunta.trim())
                  setPergunta('')
                }}
              >
                <input
                  value={pergunta}
                  onChange={(e) => setPergunta(e.target.value)}
                  placeholder="Pergunte algo sobre esta empresa…"
                />
                <button className="ask-send" type="submit" disabled={askMutation.isPending}>
                  {askMutation.isPending ? 'Perguntando…' : 'Perguntar'}
                </button>
              </form>
              {conversa.length > 0 && (
                <div className="ask-qa">
                  {conversa.map((c, i) => (
                    <div key={i}>
                      <div className="ask-q">{c.pergunta}</div>
                      <div className="ask-a">{c.resposta}</div>
                      {c.fontes?.length > 0 && (
                        <div className="ask-src">
                          {c.fontes.map((f) => <span className="src-chip" key={f}>{f}</span>)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {askMutation.isError && (
                <p className="state-msg error" style={{ padding: '0 14px 12px' }}>
                  {askMutation.error?.response?.data?.error?.message ?? 'Não foi possível responder agora.'}
                </p>
              )}
            </div>
          </section>

        </div>
      </div>
    </>
  )
}
