import { api } from './client'

export function listCadences({ page = 1, size = 100, busca } = {}) {
  return api.get('/cadences', { params: { page, size, busca } }).then((res) => res.data)
}

export function createCadence(data) {
  return api.post('/cadences', data).then((res) => res.data)
}

export function updateCadence(id, data) {
  return api.put(`/cadences/${id}`, data).then((res) => res.data)
}

export function deleteCadence(id) {
  return api.delete(`/cadences/${id}`)
}

export function cloneCadence(id) {
  return api.post(`/cadences/${id}/clone`).then((res) => res.data)
}

export function listCadenceEnrollments(id) {
  return api.get(`/cadences/${id}/enrollments`).then((res) => res.data)
}

export function createCadenceEnrollment(id, data) {
  return api.post(`/cadences/${id}/enrollments`, data).then((res) => res.data)
}
