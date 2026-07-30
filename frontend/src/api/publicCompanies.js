import { api } from './client'

export function searchCnaeCodes(busca) {
  return api.get('/cnae-codes/search', { params: { busca } }).then((res) => res.data)
}

export function getCnaeSimilares(codigo, nivel) {
  return api.get(`/cnae-codes/${codigo}/similares`, { params: { nivel } }).then((res) => res.data)
}

function buildListParams({ cnae, regiao, uf, porte, cursor }) {
  const params = new URLSearchParams()
  cnae.forEach((c) => params.append('cnae', c))
  ;(regiao ?? []).forEach((r) => params.append('regiao', r))
  ;(uf ?? []).forEach((u) => params.append('uf', u))
  if (porte) params.append('porte', porte)
  if (cursor) params.append('cursor', cursor)
  return params
}

export function searchPublicCompanies({ cnae, regiao, uf, porte, cursor }) {
  const params = buildListParams({ cnae, regiao, uf, porte, cursor })
  return api.get(`/public-companies/search?${params.toString()}`).then((res) => res.data)
}

export function bulkAddPublicCompanies(empresas) {
  return api.post('/public-companies/bulk-add', { empresas }).then((res) => res.data)
}
