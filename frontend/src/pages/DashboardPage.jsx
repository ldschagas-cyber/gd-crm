import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext.jsx'
import { getCommercialDashboard, getSellerDashboard } from '../api/dashboards'
import { getUpcomingMeetings } from '../api/me'
import '../styles/dataTable.css'
import './DashboardPage.css'

const GESTAO_PERFIS = new Set(['admin', 'gestor'])

function formatCurrency(value) {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}

function formatPercent(value) {
  return `${(value * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
}

function formatHoras(horas) {
  if (horas >= 24) return `${(horas / 24).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}d`
  return `${horas.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}h`
}

export default function DashboardPage() {
  const { user } = useAuth()
  const isGestao = GESTAO_PERFIS.has(user?.perfil)
  const [periodo, setPeriodo] = useState('mes')

  const query = useQuery({
    queryKey: ['dashboard', isGestao ? 'commercial' : 'seller', periodo],
    queryFn: () => (isGestao ? getCommercialDashboard(periodo) : getSellerDashboard(periodo)),
    enabled: Boolean(user),
  })

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>{isGestao ? 'Dashboard comercial' : 'Meu painel'}</h1>
          <p>{isGestao ? 'Visão geral do funil e da carteira' : 'Suas atividades e negócios em aberto'}</p>
        </div>
        <div className="segmented">
          <button className={periodo === 'hoje' ? 'active' : ''} onClick={() => setPeriodo('hoje')}>Hoje</button>
          <button className={periodo === 'mes' ? 'active' : ''} onClick={() => setPeriodo('mes')}>Este mês</button>
        </div>
      </header>

      <div className="content">
        {query.isLoading && <p className="state-msg">Carregando indicadores…</p>}
        {query.isError && (
          <p className="state-msg error">Não foi possível carregar o dashboard agora.</p>
        )}

        {query.data && isGestao && <CommercialKpis data={query.data} />}
        {query.data && !isGestao && <SellerKpis data={query.data} />}

        {query.data && isGestao && (
          <section className="grid-2">
            <PipelineFunnelCard stages={query.data.funil} />
            <SlaBreachCard items={query.data.sla_estourado} />
          </section>
        )}
        {query.data && isGestao && <SequenceExecutionCard items={query.data.execucao_sequencias} />}

        <UpcomingMeetingsWidget />
      </div>
    </>
  )
}

function UpcomingMeetingsWidget() {
  const query = useQuery({
    queryKey: ['upcoming-meetings'],
    queryFn: () => getUpcomingMeetings(7),
    retry: false,
  })

  // Sem Calendário conectado (ou sem eventos) é o estado normal da maioria dos
  // usuários hoje — degrada silenciosamente em vez de mostrar erro.
  if (query.isLoading || query.isError || !query.data || query.data.length === 0) return null

  return (
    <section className="card meetings-widget">
      <div className="card-head"><h3>Próximos compromissos</h3></div>
      <div className="meetings-list">
        {query.data.map((m, i) => (
          <div className="meeting-row" key={i}>
            <div className="meeting-time">
              <strong>{new Date(m.inicio).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</strong>
              <span>{new Date(m.inicio).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}</span>
            </div>
            <div className={`meeting-bar${m.teams_join_url ? ' teams' : ''}`} />
            <div className="meeting-main">
              <div className="meeting-title">{m.assunto}</div>
              {m.teams_join_url && (
                <a className="meeting-teams-link" href={m.teams_join_url} target="_blank" rel="noopener noreferrer">
                  Entrar na reunião do Teams
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function CommercialKpis({ data }) {
  return (
    <>
      <section className="kpi-row" aria-label="Indicadores principais">
        <KpiCard label="Negócios ativos" value={data.negocios_ativos.toLocaleString('pt-BR')} />
        <KpiCard label="Receita prevista" value={formatCurrency(data.receita_prevista)} />
        <KpiCard label="Receita ganha" value={formatCurrency(data.receita_ganha)} />
        <KpiCard label="Taxa de conversão" value={formatPercent(data.taxa_conversao)} />
      </section>
      <section className="kpi-strip" aria-label="Indicadores secundários">
        <div className="kpi-mini"><span className="t">Total de leads</span><span className="v">{data.total_leads.toLocaleString('pt-BR')}</span></div>
        <div className="kpi-mini"><span className="t">Empresas qualificadas</span><span className="v">{data.empresas_qualificadas.toLocaleString('pt-BR')}</span></div>
        <div className="kpi-mini"><span className="t">Negócios criados</span><span className="v">{data.negocios_criados.toLocaleString('pt-BR')}</span></div>
        <div className="kpi-mini"><span className="t">Ticket médio</span><span className="v">{formatCurrency(data.ticket_medio)}</span></div>
      </section>
    </>
  )
}

function SellerKpis({ data }) {
  return (
    <section className="kpi-row" aria-label="Indicadores principais">
      <KpiCard label="Tarefas pendentes" value={data.tarefas_pendentes.toLocaleString('pt-BR')} />
      <KpiCard label="Tarefas concluídas" value={data.tarefas_concluidas.toLocaleString('pt-BR')} />
      <KpiCard label="Ligações realizadas" value={data.ligacoes_realizadas.toLocaleString('pt-BR')} />
      <KpiCard label="E-mails enviados" value={data.emails_enviados.toLocaleString('pt-BR')} />
      <KpiCard label="Negócios abertos" value={data.negocios_abertos.toLocaleString('pt-BR')} />
      <KpiCard label="Receita prevista" value={formatCurrency(data.receita_prevista)} />
    </section>
  )
}

function KpiCard({ label, value }) {
  return (
    <div className="kpi-card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  )
}

function PipelineFunnelCard({ stages }) {
  const maxCount = Math.max(1, ...stages.map((s) => s.negocios_abertos))
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3>Funil do pipeline</h3>
          <p>Negócios abertos por etapa &middot; tempo médio desde a última interação</p>
        </div>
      </div>
      {stages.length === 0 ? (
        <p className="state-msg" style={{ padding: '0 18px 18px' }}>Nenhum pipeline configurado.</p>
      ) : (
        <div className="funnel">
          {stages.map((s) => {
            const late = s.sla_horas != null && s.tempo_medio_parado_horas != null && s.tempo_medio_parado_horas > s.sla_horas
            return (
              <div className="funnel-row" key={s.stage_id}>
                <div className="funnel-name">{s.nome}</div>
                <div className="funnel-track">
                  <div className="funnel-fill" style={{ width: `${(s.negocios_abertos / maxCount) * 100}%` }} />
                </div>
                <div className="funnel-count">{s.negocios_abertos}</div>
                <div className={`funnel-sla ${late ? 'late' : 'ok'}`}>
                  {s.tempo_medio_parado_horas == null
                    ? ' '
                    : `${formatHoras(s.tempo_medio_parado_horas)} médio${s.sla_horas != null ? ` · SLA ${s.sla_horas}h` : ''}`}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function SlaBreachCard({ items }) {
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3>Negócios com SLA estourado</h3>
          <p>Sem interação além do prazo da etapa</p>
        </div>
      </div>
      {items.length === 0 ? (
        <p className="state-msg" style={{ padding: '0 18px 18px' }}>Nenhum negócio com SLA estourado.</p>
      ) : (
        <div className="alert-list">
          {items.map((it) => (
            <div className="alert-item" key={it.deal_id}>
              <span className="alert-dot" />
              <div className="alert-body">
                <div className="alert-title">{it.nome}</div>
                <div className="alert-sub">{it.company_nome} &middot; etapa {it.stage_nome}</div>
              </div>
              <div className="alert-days">+{formatHoras(it.horas_atraso)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const EXEC_LABEL = { sequence: 'Sequência' }

function SequenceExecutionCard({ items }) {
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3>Execução de sequências</h3>
          <p>Como os processos automatizados estão performando</p>
        </div>
      </div>
      {items.length === 0 ? (
        <p className="state-msg" style={{ padding: '0 18px 18px' }}>Nenhuma sequência ativa com inscrições.</p>
      ) : (
        <div className="exec-list">
          {items.map((it) => (
            <div className="exec-row" key={`${it.tipo}-${it.id}`}>
              <div className="exec-head">
                <span className="exec-name">{EXEC_LABEL[it.tipo] || it.tipo} &middot; {it.nome}</span>
                <span className="exec-total">{it.total} inscrições</span>
              </div>
              <div className="exec-stack">
                <span style={{ width: `${(it.concluida / it.total) * 100}%`, background: 'var(--good)' }} />
                <span style={{ width: `${(it.pausada / it.total) * 100}%`, background: 'var(--warning)' }} />
                <span style={{ width: `${(it.ativa / it.total) * 100}%`, background: 'var(--azul)' }} />
              </div>
              <div className="exec-legend">
                <span>Concluída {formatPercent(it.concluida / it.total)}</span>
                <span>Pausada por resposta {formatPercent(it.pausada / it.total)}</span>
                <span>Em andamento {formatPercent(it.ativa / it.total)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
