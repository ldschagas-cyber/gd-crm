import { api } from './client'

// ---- Módulo de Clientes (lista/resumo agregados) -------------------------------

export function listClientes({
  csFase, csResponsavelId, busca, healthScoreMax, renovacaoAteDias, somenteEmRisco,
} = {}) {
  return api
    .get('/clientes', {
      params: {
        cs_fase: csFase, cs_responsavel_id: csResponsavelId, busca,
        health_score_max: healthScoreMax, renovacao_ate_dias: renovacaoAteDias,
        somente_em_risco: somenteEmRisco || undefined,
      },
    })
    .then((res) => res.data)
}

export function getClientesResumo() {
  return api.get('/clientes/resumo').then((res) => res.data)
}

// ---- Sub-recursos por empresa ---------------------------------------------------

export function setCompanyCs(id, csResponsavelId) {
  return api.patch(`/companies/${id}/cs`, { cs_responsavel_id: csResponsavelId }).then((res) => res.data)
}

export function setCompanyCsFase(id, csFase) {
  return api.patch(`/companies/${id}/cs-fase`, { cs_fase: csFase }).then((res) => res.data)
}

export function getCompanyHealth(id) {
  return api.get(`/companies/${id}/health`).then((res) => res.data)
}

export function createCheckin(id, data) {
  return api.post(`/companies/${id}/checkins`, data).then((res) => res.data)
}

export function listOnboarding(id) {
  return api.get(`/companies/${id}/onboarding`).then((res) => res.data)
}

export function setOnboardingItemStatus(companyId, itemId, status) {
  return api.patch(`/companies/${companyId}/onboarding/${itemId}`, { status }).then((res) => res.data)
}
