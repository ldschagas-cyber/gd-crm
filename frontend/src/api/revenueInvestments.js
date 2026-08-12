import { api } from './client'

export function listRevenueInvestments({ mes } = {}) {
  return api.get('/revenue-investments', { params: { mes } }).then((res) => res.data)
}

export function createRevenueInvestment(data) {
  return api.post('/revenue-investments', data).then((res) => res.data)
}

export function updateRevenueInvestment(id, data) {
  return api.put(`/revenue-investments/${id}`, data).then((res) => res.data)
}

export function deleteRevenueInvestment(id) {
  return api.delete(`/revenue-investments/${id}`)
}

export function getCacRoi({ mes }) {
  return api.get('/revenue-investments/cac-roi', { params: { mes } }).then((res) => res.data)
}
