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

export default function DashboardPage() {
  const { user } = useAuth()
  const isGestao = GESTAO_PERFIS.has(user?.perfil)

  const query = useQuery({
    queryKey: ['dashboard', isGestao ? 'commercial' : 'seller'],
    queryFn: isGestao ? getCommercialDashboard : getSellerDashboard,
    enabled: Boolean(user),
  })

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>{isGestao ? 'Dashboard comercial' : 'Meu painel'}</h1>
          <p>{isGestao ? 'Visão geral do funil e da carteira' : 'Suas atividades e negócios em aberto'}</p>
        </div>
      </header>

      <div className="content">
        {query.isLoading && <p className="state-msg">Carregando indicadores…</p>}
        {query.isError && (
          <p className="state-msg error">Não foi possível carregar o dashboard agora.</p>
        )}

        {query.data && isGestao && <CommercialKpis data={query.data} />}
        {query.data && !isGestao && <SellerKpis data={query.data} />}

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
