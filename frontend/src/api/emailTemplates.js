import { api } from './client'

export function listEmailTemplates({ page = 1, size = 100, busca } = {}) {
  return api.get('/email-templates', { params: { page, size, busca } }).then((res) => res.data)
}

export function createEmailTemplate(data) {
  return api.post('/email-templates', data).then((res) => res.data)
}

export function updateEmailTemplate(id, data) {
  return api.put(`/email-templates/${id}`, data).then((res) => res.data)
}

export function deleteEmailTemplate(id) {
  return api.delete(`/email-templates/${id}`)
}
