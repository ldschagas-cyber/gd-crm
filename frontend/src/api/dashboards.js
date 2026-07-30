import { api } from './client'

export function getCommercialDashboard(periodo = 'mes') {
  return api.get('/dashboards/commercial', { params: { periodo } }).then((res) => res.data)
}

export function getSellerDashboard(periodo = 'mes') {
  return api.get('/dashboards/seller', { params: { periodo } }).then((res) => res.data)
}
