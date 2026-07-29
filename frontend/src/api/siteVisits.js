import { api } from './client'

export function getSiteVisitsKpis() {
  return api.get('/site-visits/kpis').then((res) => res.data)
}

export function getDailySessions(days = 14) {
  return api.get('/site-visits/daily', { params: { days } }).then((res) => res.data)
}

export function getTopPages(days = 30, limit = 10) {
  return api.get('/site-visits/pages', { params: { days, limit } }).then((res) => res.data)
}

export function getIdentifiedCompanies(days = 30, limit = 20) {
  return api.get('/site-visits/companies', { params: { days, limit } }).then((res) => res.data)
}
