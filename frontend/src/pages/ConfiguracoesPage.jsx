import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getTenant, updateTenant } from '../api/tenant'
import { listImportJobs } from '../api/importJobs'
import '../styles/dataTable.css'
import './ConfiguracoesPage.css'

const TIPO_LABEL = { empresas: 'Empresas', contatos: 'Contatos' }
const STATUS_LABEL = { pendente: 'Pendente', processando: 'Processando', concluido: 'Concluído', erro: 'Erro' }

export default function ConfiguracoesPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const tenantQuery = useQuery({ queryKey: ['tenant'], queryFn: getTenant })
  const jobsQuery = useQuery({ queryKey: ['import-jobs', page], queryFn: () => listImportJobs({ page, size: 15 }) })

  const [form, setForm] = useState(null)
  const tenant = tenantQuery.data
  const current = form ?? (tenant ? { razao_social: tenant.razao_social, nome_fantasia: tenant.nome_fantasia ?? '' } : null)

  const updateMutation = useMutation({
    mutationFn: (data) => updateTenant(data),
    onSuccess: () => {
      setForm(null)
      queryClient.invalidateQueries({ queryKey: ['tenant'] })
    },
  })

  function set(field) {
    return (e) => setForm({ ...current, [field]: e.target.value })
  }

  function handleSave(e) {
    e.preventDefault()
    updateMutation.mutate({
      razao_social: current.razao_social.trim(),
      nome_fantasia: current.nome_fantasia.trim() || null,
    })
  }

  const total = jobsQuery.data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / 15))

  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>Configurações</h1>
          <p>Dados da empresa e histórico de importações</p>
        </div>
      </header>

      <div className="content">
        {tenantQuery.isLoading && <p className="state-msg">Carregando…</p>}

        {current && (
          <form className="card section-card" onSubmit={handleSave}>
            <div className="card-head">
              <h2>Dados da empresa</h2>
              <p>Essas informações identificam seu tenant no CRM</p>
            </div>
            <div className="section-body">
              <div className="f-group">
                <label className="f-label">Razão social <span className="req">*</span></label>
                <input className="f-input" value={current.razao_social} onChange={set('razao_social')} required />
              </div>
              <div className="f-group">
                <label className="f-label">Nome fantasia <span className="opt">opcional</span></label>
                <input className="f-input" value={current.nome_fantasia} onChange={set('nome_fantasia')} />
              </div>
              <div className="f-row">
                <div className="f-group">
                  <label className="f-label">CNPJ</label>
                  <input className="f-input mono" value={tenant.cnpj} disabled />
                </div>
                <div className="f-group">
                  <label className="f-label">Plano e status</label>
                  <input className="f-input" value={`${tenant.plano} · ${tenant.status}`} disabled />
                </div>
              </div>
              {updateMutation.isError && <p className="state-msg error">Não foi possível salvar. Confira os dados e tente de novo.</p>}
            </div>
            <div className="section-foot">
              <button type="submit" className="btn-primary" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? 'Salvando…' : 'Salvar alterações'}
              </button>
            </div>
          </form>
        )}

        <div className="card section-card">
          <div className="card-head">
            <h2>Histórico de importações</h2>
            <p>Uploads de empresas e contatos processados pelo worker</p>
          </div>

          {jobsQuery.isLoading && <p className="state-msg">Carregando…</p>}
          {jobsQuery.isError && <p className="state-msg error">Não foi possível carregar o histórico agora.</p>}

          {jobsQuery.data && (
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>Arquivo</th><th>Tipo</th><th>Status</th><th>Linhas</th><th>Importados</th><th>Erros</th><th>Data</th>
                  </tr>
                </thead>
                <tbody>
                  {(jobsQuery.data.items ?? []).map((j) => (
                    <tr key={j.id}>
                      <td><div className="row-title">{j.arquivo}</div></td>
                      <td>{TIPO_LABEL[j.tipo] ?? j.tipo}</td>
                      <td><span className={`job-status-pill job-status-${j.status}`}>{STATUS_LABEL[j.status] ?? j.status}</span></td>
                      <td>{j.total_linhas ?? '—'}</td>
                      <td>{j.importadas ?? '—'}</td>
                      <td>
                        {j.erros?.length
                          ? <span className="job-errors" title={JSON.stringify(j.erros).slice(0, 500)}>{j.erros.length} erro(s)</span>
                          : '—'}
                      </td>
                      <td>{new Date(j.created_at).toLocaleString('pt-BR')}</td>
                    </tr>
                  ))}
                  {jobsQuery.data.items.length === 0 && (
                    <tr><td colSpan={7} className="empty-cell">Nenhuma importação ainda.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          <div className="pagination">
            <span className="info">{total > 0 ? `mostrando página ${page} de ${totalPages}` : 'sem resultados'}</span>
            <div className="controls">
              <button className="page-btn" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>‹</button>
              <button className="page-btn" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>›</button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
