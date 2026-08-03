import { api } from './client'

export function listDeals({
  page = 1, size = 20, pipelineId, stageId, status, responsavelId, companyId, busca, contactId,
} = {}) {
  return api
    .get('/deals', {
      params: {
        page, size, pipeline_id: pipelineId, stage_id: stageId, status,
        responsavel_id: responsavelId, company_id: companyId, busca, contact_id: contactId,
      },
    })
    .then((res) => res.data)
}

export function getDeal(id) {
  return api.get(`/deals/${id}`).then((res) => res.data)
}

export function createDeal(data) {
  return api.post('/deals', data).then((res) => res.data)
}

export function updateDeal(id, data) {
  return api.put(`/deals/${id}`, data).then((res) => res.data)
}

export function moveDealStage(id, stageId) {
  return api.patch(`/deals/${id}/stage`, { stage_id: stageId }).then((res) => res.data)
}

export function closeDeal(id, data) {
  return api.patch(`/deals/${id}/close`, data).then((res) => res.data)
}

export function deleteDeal(id) {
  return api.delete(`/deals/${id}`)
}
