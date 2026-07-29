import { api } from './client'

export function getCommercialDashboard() {
  return api.get('/dashboards/commercial').then((res) => res.data)
}

export function getSellerDashboard() {
  return api.get('/dashboards/seller').then((res) => res.data)
}
