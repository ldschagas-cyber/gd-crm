import { api } from './client'

export function listPropostas({ page = 1, size = 100, status, company_id } = {}) {
  return api.get('/propostas', { params: { page, size, status, company_id } }).then((res) => res.data)
}

export function getProposta(id) {
  return api.get(`/propostas/${id}`).then((res) => res.data)
}

export function createProposta(data) {
  return api.post('/propostas', data).then((res) => res.data)
}

export function updateProposta(id, data) {
  return api.put(`/propostas/${id}`, data).then((res) => res.data)
}

export function mudarStatusProposta(id, status) {
  return api.post(`/propostas/${id}/status`, { status }).then((res) => res.data)
}
