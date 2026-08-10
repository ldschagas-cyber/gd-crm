import { api } from './client'

export function listMessageTemplates({ page = 1, size = 100, busca, canal } = {}) {
  return api.get('/message-templates', { params: { page, size, busca, canal } }).then((res) => res.data)
}

export function createMessageTemplate(data) {
  return api.post('/message-templates', data).then((res) => res.data)
}

export function updateMessageTemplate(id, data) {
  return api.put(`/message-templates/${id}`, data).then((res) => res.data)
}

export function deleteMessageTemplate(id) {
  return api.delete(`/message-templates/${id}`)
}
