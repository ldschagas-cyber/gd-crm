import { api, API_ORIGIN } from './client'

export function updateMe(data) {
  return api.put('/me', data).then((res) => res.data)
}

export function uploadAvatar(file) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/me/avatar', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then((res) => res.data)
}

export function removeAvatar() {
  return api.delete('/me/avatar').then((res) => res.data)
}

export function avatarUrl(user) {
  if (!user?.avatar_url) return null
  return `${API_ORIGIN}${user.avatar_url}`
}

export function changeMyPassword(data) {
  return api.put('/me/password', data)
}

export function getIntegration(tipo) {
  return api.get(`/me/integrations/${tipo}`).then((res) => res.data)
}

export async function connectIntegration(tipo) {
  const { data } = await api.post(`/me/integrations/${tipo}`)
  window.location.href = data.auth_url
}

export function disconnectIntegration(tipo) {
  return api.delete(`/me/integrations/${tipo}`)
}

export function getUpcomingMeetings(days = 7) {
  return api.get('/me/upcoming-meetings', { params: { days } }).then((res) => res.data)
}
