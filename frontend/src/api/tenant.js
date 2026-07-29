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
