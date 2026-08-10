import { api } from './client'

export function getFunilMetasResumo(modo, mes) {
  return api.get('/funil-metas/resumo', { params: { modo, mes } }).then((res) => res.data)
}
