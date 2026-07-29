import { api } from './client'

export function listSnippets({ page = 1, size = 100, busca } = {}) {
  return api.get('/snippets', { params: { page, size, busca } }).then((res) => res.data)
}

export function createSnippet(data) {
  return api.post('/snippets', data).then((res) => res.data)
}

export function updateSnippet(id, data) {
  return api.put(`/snippets/${id}`, data).then((res) => res.data)
}

export function deleteSnippet(id) {
  return api.delete(`/snippets/${id}`)
}
