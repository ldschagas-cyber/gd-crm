import { api } from './client'

export function getTenant() {
  return api.get('/tenant').then((res) => res.data)
}

export function updateTenant(data) {
  return api.put('/tenant', data).then((res) => res.data)
}

export function getIcpScoringRules() {
  return api.get('/tenant/icp-scoring-rules').then((res) => res.data)
}

export function updateIcpScoringRules(data) {
  return api.put('/tenant/icp-scoring-rules', data).then((res) => res.data)
}

export function getLeadScoreRules() {
  return api.get('/tenant/lead-score-rules').then((res) => res.data)
}

export function updateLeadScoreRules(data) {
  return api.put('/tenant/lead-score-rules', data).then((res) => res.data)
}

export function getWhatsappStatus() {
  return api.get('/tenant/whatsapp-status').then((res) => res.data)
}

export function getFunilMetasConfig() {
  return api.get('/tenant/funil-metas').then((res) => res.data)
}

export function updateFunilMetasConfig(data) {
  return api.put('/tenant/funil-metas', data).then((res) => res.data)
}
