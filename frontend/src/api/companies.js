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

export function getImportJob(jobId) {
  return api.get(`/companies/import/${jobId}`).then((res) => res.data)
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
