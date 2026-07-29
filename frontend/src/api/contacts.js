import { api } from './client'

export function listContacts({ page = 1, size = 20, companyId, busca, cargo, temWhatsapp } = {}) {
  return api
    .get('/contacts', {
      params: { page, size, company_id: companyId, busca, cargo, tem_whatsapp: temWhatsapp },
    })
    .then((res) => res.data)
}

export function getContactFilterOptions() {
  return api.get('/contacts/filter-options').then((res) => res.data)
}

export function getContact(id) {
  return api.get(`/contacts/${id}`).then((res) => res.data)
}

export function getContactEmails(id) {
  return api.get(`/contacts/${id}/emails`).then((res) => res.data)
}

export function createContact(data) {
  return api.post('/contacts', data).then((res) => res.data)
}

export function updateContact(id, data) {
  return api.put(`/contacts/${id}`, data).then((res) => res.data)
}

export function deleteContact(id) {
  return api.delete(`/contacts/${id}`)
}

export function importContacts(file) {
  const form = new FormData()
  form.append('file', file)
  return api
    .post('/contacts/import', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    .then((res) => res.data)
}

export function getContactImportJob(jobId) {
  return api.get(`/contacts/import/${jobId}`).then((res) => res.data)
}

export async function exportContacts({ companyId, busca, cargo, temWhatsapp } = {}) {
  const res = await api.get('/contacts/export', {
    params: { company_id: companyId, busca, cargo, tem_whatsapp: temWhatsapp },
    responseType: 'blob',
  })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'contatos.csv'
  a.click()
  URL.revokeObjectURL(url)
}
