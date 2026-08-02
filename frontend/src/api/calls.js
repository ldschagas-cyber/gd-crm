import { api } from './client'

export function getCallConfig() {
  return api.get('/calls/config').then((res) => res.data)
}

export function getCallToken() {
  return api.get('/calls/token').then((res) => res.data)
}
