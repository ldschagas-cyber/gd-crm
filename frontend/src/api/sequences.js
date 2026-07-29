import { api } from './client'

export function listSequences({ page = 1, size = 100, busca } = {}) {
  return api.get('/sequences', { params: { page, size, busca } }).then((res) => res.data)
}

export function createSequence(data) {
  return api.post('/sequences', data).then((res) => res.data)
}

export function updateSequence(id, data) {
  return api.put(`/sequences/${id}`, data).then((res) => res.data)
}

export function deleteSequence(id) {
  return api.delete(`/sequences/${id}`)
}

export function cloneSequence(id) {
  return api.post(`/sequences/${id}/clone`).then((res) => res.data)
}

export function listSequenceEnrollments(id) {
  return api.get(`/sequences/${id}/enrollments`).then((res) => res.data)
}

export function createSequenceEnrollment(id, data) {
  return api.post(`/sequences/${id}/enrollments`, data).then((res) => res.data)
}
