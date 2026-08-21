import { api } from './client'

export function getFinanceiroResumo() {
  return api.get('/financeiro/resumo').then((res) => res.data)
}

export function listCategorias(tipo = 'receita') {
  return api.get('/financeiro/categorias', { params: { tipo } }).then((res) => res.data)
}

export function createCategoria(data) {
  return api.post('/financeiro/categorias', data).then((res) => res.data)
}

export function listContratos(status) {
  return api.get('/contratos', { params: { status } }).then((res) => res.data)
}

export function ativarContrato(id, data) {
  return api.post(`/contratos/${id}/ativar`, data ?? {}).then((res) => res.data)
}
