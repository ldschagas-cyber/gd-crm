import { api } from './client'

export function listWorkflows({ page = 1, size = 100, busca } = {}) {
  return api.get('/workflows', { params: { page, size, busca } }).then((res) => res.data)
}

export function createWorkflow(data) {
  return api.post('/workflows', data).then((res) => res.data)
}

export function updateWorkflow(id, data) {
  return api.put(`/workflows/${id}`, data).then((res) => res.data)
}

export function deleteWorkflow(id) {
  return api.delete(`/workflows/${id}`)
}

export function listWorkflowLogs(id) {
  return api.get(`/workflows/${id}/logs`).then((res) => res.data)
}
