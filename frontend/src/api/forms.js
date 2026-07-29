import { api } from './client'

export function listForms() {
  return api.get('/forms').then((res) => res.data)
}

export function getFormsKpis() {
  return api.get('/forms/kpis').then((res) => res.data)
}

export function getForm(id) {
  return api.get(`/forms/${id}`).then((res) => res.data)
}

export function createForm(data) {
  return api.post('/forms', data).then((res) => res.data)
}

export function updateForm(id, data) {
  return api.put(`/forms/${id}`, data).then((res) => res.data)
}

export function listFormSubmissions(id, { page = 1, size = 10 } = {}) {
  return api.get(`/forms/${id}/submissions`, { params: { page, size } }).then((res) => res.data)
}
