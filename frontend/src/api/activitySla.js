import { api } from './client'

export function listSlaRules() {
  return api.get('/activity-sla/rules').then((res) => res.data)
}

export function createSlaRule(data) {
  return api.post('/activity-sla/rules', data).then((res) => res.data)
}

export function updateSlaRule(id, data) {
  return api.put(`/activity-sla/rules/${id}`, data).then((res) => res.data)
}

export function deleteSlaRule(id) {
  return api.delete(`/activity-sla/rules/${id}`)
}

export function getSlaResumo() {
  return api.get('/activity-sla/resumo').then((res) => res.data)
}
