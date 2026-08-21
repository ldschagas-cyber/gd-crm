import { api } from './client'

export function listProdutos({ page = 1, size = 100, busca, ativo } = {}) {
  return api.get('/produtos', { params: { page, size, busca, ativo } }).then((res) => res.data)
}

export function createProduto(data) {
  return api.post('/produtos', data).then((res) => res.data)
}

export function updateProduto(id, data) {
  return api.put(`/produtos/${id}`, data).then((res) => res.data)
}

export function getHistoricoPreco(id) {
  return api.get(`/produtos/${id}/historico-preco`).then((res) => res.data)
}
