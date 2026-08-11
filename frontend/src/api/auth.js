import { api } from './client'

export function login(email, senha) {
  return api.post('/auth/login', { email, senha }).then((res) => res.data)
}

export function me() {
  return api.get('/auth/me').then((res) => res.data)
}

export function logout() {
  return api.post('/auth/logout')
}

export function resetPassword(token, novaSenha) {
  return api.post('/auth/reset-password', { token, nova_senha: novaSenha }).then((res) => res.data)
}
