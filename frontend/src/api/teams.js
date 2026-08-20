import { api } from './client'

export function listTeams() {
  return api.get('/teams').then((res) => res.data)
}

export function createTeam(data) {
  return api.post('/teams', data).then((res) => res.data)
}

export function updateTeam(id, data) {
  return api.put(`/teams/${id}`, data).then((res) => res.data)
}

export function deleteTeam(id) {
  return api.delete(`/teams/${id}`)
}
