import { api } from './client'

// periodo: { mes: 'AAAA-MM' } para visão mensal ou { ano: 'AAAA' } para visão anual agregada.
export function getFunilMetasResumo(modo, { mes, ano } = {}) {
  const params = ano ? { modo, ano } : { modo, mes }
  return api.get('/funil-metas/resumo', { params }).then((res) => res.data)
}
