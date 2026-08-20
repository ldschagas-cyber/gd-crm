import { api } from './client'

export function getMetasLigacoesProgresso() {
  return api.get('/metas-ligacoes/progresso').then((res) => res.data)
}
