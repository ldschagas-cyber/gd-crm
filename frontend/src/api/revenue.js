import { api } from './client'

export function getRevenueResumo(periodo = 'mes') {
  return api.get('/receita-recorrente/resumo', { params: { periodo } }).then((res) => res.data)
}

export function getRevenueWaterfall(meses = 6) {
  return api.get('/receita-recorrente/waterfall', { params: { meses } }).then((res) => res.data)
}
