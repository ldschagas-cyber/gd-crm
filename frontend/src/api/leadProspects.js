import { api } from './client'

export function listLeadProspects({
  page = 1, size = 200, status, icpFit, pesquisadoPor, busca,
} = {}) {
  return api
    .get('/lead-prospects', {
      params: {
        page, size, status, icp_fit: icpFit, pesquisado_por: pesquisadoPor, busca,
      },
    })
    .then((res) => res.data)
}

export function getLeadProspect(id) {
  return api.get(`/lead-prospects/${id}`).then((res) => res.data)
}

export function createLeadProspect(data) {
  return api.post('/lead-prospects', data).then((res) => res.data)
}

export function updateLeadProspect(id, data) {
  return api.put(`/lead-prospects/${id}`, data).then((res) => res.data)
}

export function deleteLeadProspect(id) {
  return api.delete(`/lead-prospects/${id}`)
}

export function promoteLeadProspect(id) {
  return api.post(`/lead-prospects/${id}/promote`).then((res) => res.data)
}

export function importLeadProspects(file) {
  const form = new FormData()
  form.append('file', file)
  return api
    .post('/lead-prospects/import', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    .then((res) => res.data)
}

export function getLeadProspectImportJob(jobId) {
  return api.get(`/lead-prospects/import/${jobId}`).then((res) => res.data)
}

export function enrichLeadProspect(id) {
  return api.post(`/lead-prospects/${id}/enrich`).then((res) => res.data)
}

export function getPerformanceReport(mes) {
  return api.get('/lead-prospects/performance-report', { params: { mes } }).then((res) => res.data)
}
