import { api } from './client'

export function listTimeline(companyId, { page = 1, size = 30 } = {}) {
  return api
    .get(`/companies/${companyId}/timeline`, { params: { page, size } })
    .then((res) => res.data)
}

export function addTimelineNote(companyId, data) {
  return api.post(`/companies/${companyId}/timeline`, data).then((res) => res.data)
}

export function listDealTimeline(dealId, { page = 1, size = 30 } = {}) {
  return api
    .get(`/deals/${dealId}/timeline`, { params: { page, size } })
    .then((res) => res.data)
}

export function addDealTimelineNote(dealId, data) {
  return api.post(`/deals/${dealId}/timeline`, data).then((res) => res.data)
}

export function listContactTimeline(contactId, { page = 1, size = 30 } = {}) {
  return api
    .get(`/contacts/${contactId}/timeline`, { params: { page, size } })
    .then((res) => res.data)
}

export function addContactTimelineNote(contactId, data) {
  return api.post(`/contacts/${contactId}/timeline`, data).then((res) => res.data)
}
