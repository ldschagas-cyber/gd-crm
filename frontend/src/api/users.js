import { api } from './client'

export function listUsers({ page = 1, size = 100, busca, perfil } = {}) {
  return api.get('/users', { params: { page, size, busca, perfil } }).then((res) => res.data)
}

export function createUser(data) {
  return api.post('/users', data).then((res) => res.data)
}

export function updateUser(id, data) {
  return api.put(`/users/${id}`, data).then((res) => res.data)
}

export function setUserStatus(id, status) {
  return api.patch(`/users/${id}/status`, { status }).then((res) => res.data)
}

export function generateResetLink(id) {
  return api.post(`/users/${id}/reset-link`).then((res) => res.data)
}
