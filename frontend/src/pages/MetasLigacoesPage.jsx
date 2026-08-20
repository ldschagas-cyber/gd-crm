import { useQuery } from '@tanstack/react-query'
import { getMetasLigacoesProgresso } from '../api/metasLigacoes'
import '../styles/dataTable.css'
import './MetasLigacoesPage.css'

function pct(atual, meta) {
  if (!meta) return null
  return Math.round((atual / meta) * 100)
}
function statusClass(p) {
  if (p == null) return ''
  if (p >= 100) return 'ok'
  if (p >= 70) return 'atencao'
  return 'critico'
}
function initials(nome) {
  if (!nome) return '?'
  const parts = nome.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] ?? '')).toUpperCase()
}

function LigBar({ label, atual, meta }) {
  const p = pct(atual, meta)
  return (
    <div className="lig-bar">
      <span className="lig-bar-label">{label}</span>
      {meta ? (
        <>
          <div className="lig-track">
            <div className={`lig-fill ${statusClass(p)}`} style={{ width: `${Math.min(100, p)}%` }} />
          </div>
          <span className={`lig-pill ${statusClass(p)}`}>{atual}/{meta}</span>
        </>
      ) : (
        <span className="lig-nogoal">{atual} ligaç{atual === 1 ? 'ão' : 'ões'} · sem meta definida</span>
      )}
    </div>
  )
}

export default function MetasLigacoesPage() {
  const query = useQuery({ queryKey: ['metas-ligacoes'], queryFn: getMetasLigacoesProgresso, retry: false })

  if (query.isError) {
    return (
      <>
        <header className="topbar"><div className="topbar-title"><h1>Metas de Ligações</h1></div></header>
        <div className="content"><p className="state-msg error">Só administradores e gestores podem ver este controle.</p></div>
      </>
    )
  }

  const rows = query.data?.rows ?? []
  const totalSemana = rows.reduce((a, r) => a + r.ligacoes_semana, 0)
  const totalMes = rows.reduce((a, r) => a + r.ligacoes_mes, 0)

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Metas de Ligações</h1>
          <p>Ligações por vendedor na semana e no mês correntes — realizado = tarefas de ligação concluídas</p>
        </div>
      </header>

      <div className="content">
        {query.isLoading ? (
          <p className="state-msg">Carregando…</p>
        ) : rows.length === 0 ? (
          <div className="card"><p className="state-msg">Nenhuma meta de ligação definida e nenhuma ligação registrada. Defina metas em Usuários.</p></div>
        ) : (
          <>
            <div className="stat-strip">
              <div className="stat-tile"><div className="t">Ligações na semana</div><div className="v">{totalSemana}</div></div>
              <div className="stat-tile"><div className="t">Ligações no mês</div><div className="v">{totalMes}</div></div>
              <div className="stat-tile"><div className="t">Vendedores ativos</div><div className="v">{rows.length}</div></div>
            </div>

            <div className="card">
              <div className="card-head">
                <div>
                  <h3>Progresso por vendedor</h3>
                  <p>Semana e mês correntes — sempre "hoje", independente de filtros. Realizado atualiza conforme as tarefas de ligação são concluídas.</p>
                </div>
              </div>
              <div className="card-body">
                {rows.map((r) => (
                  <div className="lig-row" key={r.user_id}>
                    <div className="row-resp"><span className="avatar">{initials(r.nome)}</span>{r.nome}</div>
                    <div className="lig-bars">
                      <LigBar label="Semana" atual={r.ligacoes_semana} meta={r.meta_semanal} />
                      <LigBar label="Mês" atual={r.ligacoes_mes} meta={r.meta_mensal} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
