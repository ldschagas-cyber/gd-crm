import { api } from './client'

export function getMetasLigacoesProgresso(mes) {
  return api.get('/metas-ligacoes/progresso', { params: { mes } }).then((res) => res.data)
}

export function setMetasLigacoesTargets(mes, items) {
  return api.put('/metas-ligacoes/targets', items, { params: { mes } }).then((res) => res.data)
}
