import { api } from './client'

export function getFaturamento(competencia) {
  return api.get('/faturamento', { params: { competencia } }).then((res) => res.data)
}

export function gerarFaturamento(competencia) {
  return api.post('/faturamento/gerar', { competencia }).then((res) => res.data)
}

export function reenviarNf(competencia) {
  return api.post('/faturamento/reenviar-nf', { competencia }).then((res) => res.data)
}

export function criarCobrancaPontual(data) {
  return api.post('/faturamento/cobrancas', data).then((res) => res.data)
}
