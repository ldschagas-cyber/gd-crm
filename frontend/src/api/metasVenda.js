import { api } from './client'

export function getMetasVendaResumo(mes) {
  return api.get('/metas-venda/resumo', { params: { mes } }).then((res) => res.data)
}

export function setMetasVendaTargets(mes, items) {
  return api.put('/metas-venda/targets', items, { params: { mes } }).then((res) => res.data)
}
