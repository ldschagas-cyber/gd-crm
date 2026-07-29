import { api } from './client'

export function listPipelines({ page = 1, size = 20 } = {}) {
  return api.get('/pipelines', { params: { page, size } }).then((res) => res.data)
}

export function getPipeline(id) {
  return api.get(`/pipelines/${id}`).then((res) => res.data)
}

export function createPipeline(data) {
  return api.post('/pipelines', data).then((res) => res.data)
}

export function updatePipeline(id, data) {
  return api.put(`/pipelines/${id}`, data).then((res) => res.data)
}

export function addStage(pipelineId, data) {
  return api.post(`/pipelines/${pipelineId}/stages`, data).then((res) => res.data)
}

export function updateStage(pipelineId, stageId, data) {
  return api.put(`/pipelines/${pipelineId}/stages/${stageId}`, data).then((res) => res.data)
}

export function deleteStage(pipelineId, stageId) {
  return api.delete(`/pipelines/${pipelineId}/stages/${stageId}`)
}

export function getBoard(pipelineId) {
  return api.get(`/pipelines/${pipelineId}/board`).then((res) => res.data)
}
