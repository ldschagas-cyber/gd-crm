import { api } from './client'

export function listAssinaturas({ status, responsavelId, companyId } = {}) {
  return api
    .get('/assinaturas', { params: { status, responsavel_id: responsavelId, company_id: companyId } })
    .then((res) => res.data)
}

export function getAssinatura(id) {
  return api.get(`/assinaturas/${id}`).then((res) => res.data)
}

export function createAssinatura(data) {
  return api.post('/assinaturas', data).then((res) => res.data)
}

export function atualizarValorAssinatura(id, data) {
  return api.patch(`/assinaturas/${id}/valor`, data).then((res) => res.data)
}

export function cancelarAssinatura(id, data) {
  return api.patch(`/assinaturas/${id}/cancelar`, data).then((res) => res.data)
}

export function reativarAssinatura(id, data) {
  return api.patch(`/assinaturas/${id}/reativar`, data).then((res) => res.data)
}

export function listEventosAssinatura(id) {
  return api.get(`/assinaturas/${id}/eventos`).then((res) => res.data)
}
