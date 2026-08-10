import { api } from './client'

export function getForecastResumo({ mes, pipelineId, responsavelId } = {}) {
  return api
    .get('/forecast/resumo', { params: { mes, pipeline_id: pipelineId, responsavel_id: responsavelId } })
    .then((res) => res.data)
}
