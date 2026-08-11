import { api } from './client'

export function listOrigemOptions() {
  return api.get('/origem-options').then((res) => res.data)
}

export function createOrigemOption(nome) {
  return api.post('/origem-options', { nome }).then((res) => res.data)
}
