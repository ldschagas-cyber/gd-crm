import { api } from './client'

export function listCompanies({
  page = 1, size = 20, status, uf, busca, responsavelId, segmento, porte, origem,
} = {}) {
  return api
    .get('/companies', {
      params: {
        page, size, status, uf, busca, responsavel_id: responsavelId, segmento, porte, origem,
      },
    })
    .then((res) => res.data)
}

export function getCompanyFilterOptions() {
  return api.get('/companies/filter-options').then((res) => res.data)
}

export function getCompany(id) {
  return api.get(`/companies/${id}`).then((res) => res.data)
}

export function createCompany(data) {
  return api.post('/companies', data).then((res) => res.data)
}

export function updateCompany(id, data) {
  return api.put(`/companies/${id}`, data).then((res) => res.data)
}

export function deleteCompany(id) {
  return api.delete(`/companies/${id}`)
}

export function setCompanyStatus(id, status) {
  return api.patch(`/companies/${id}/status`, { status }).then((res) => res.data)
}

export function importCompanies(file) {
  const form = new FormData()
  form.append('file', file)
  return api
    .post('/companies/import', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    .then((res) => res.data)
}

export function importCompaniesContacts(file) {
  const form = new FormData()
  form.append('file', file)
  return api
    .post('/companies/import-empresas-contatos', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    .then((res) => res.data)
}

export function getImportJob(jobId) {
  return api.get(`/companies/import/${jobId}`).then((res) => res.data)
}

export function getCompanyIcp(id) {
  return api.get(`/companies/${id}/icp`).then((res) => res.data)
}

export function updateCompanyDossier(id, data) {
  return api.put(`/companies/${id}/dossie`, data).then((res) => res.data)
}

export function regenerateCompanyResumo(id) {
  return api.post(`/companies/${id}/dossie/resumo/atualizar`).then((res) => res.data)
}

export function askCompanyAi(id, pergunta) {
  return api.post(`/companies/${id}/dossie/perguntar`, { pergunta }).then((res) => res.data)
}

// SDR Argos (nível 2 do agente comercial, ver docs/PLANO_SDR_AUTONOMO.md) — gatilho manual
// ("botão SDR Argos"); a regra padrão é automática em background no handoff da promoção.
export function runSdrArgos(id) {
  return api.post(`/companies/${id}/sdr-argos`).then((res) => res.data)
}

// ---- Central de Leads --------------------------------------------------------

export function listCentralLeads({
  funilEstagio, responsavelId, busca, leadScoreMin, emCadencia, esconderConvertidosAposDias,
} = {}) {
  return api
    .get('/companies/central-leads', {
      params: {
        funil_estagio: funilEstagio, responsavel_id: responsavelId, busca,
        lead_score_min: leadScoreMin, em_cadencia: emCadencia,
        esconder_convertidos_apos_dias: esconderConvertidosAposDias,
      },
    })
    .then((res) => res.data)
}

export function getCentralLeadsResumo() {
  return api.get('/companies/central-leads/resumo').then((res) => res.data)
}

export function setCompanyFunilEstagio(id, funilEstagio) {
  return api.patch(`/companies/${id}/funil-estagio`, { funil_estagio: funilEstagio }).then((res) => res.data)
}

export async function exportCompanies({
  status, uf, busca, responsavelId, segmento, porte, origem,
} = {}) {
  const res = await api.get('/companies/export', {
    params: {
      status, uf, busca, responsavel_id: responsavelId, segmento, porte, origem,
    },
    responseType: 'blob',
  })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'empresas.csv'
  a.click()
  URL.revokeObjectURL(url)
}
