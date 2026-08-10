import { api } from './client'

export function listTasks({
  page = 1, size = 20, companyId, responsavelId, status, tipo, prioridade, busca,
  dataInicio, dataFim, dealId, contactId,
} = {}) {
  return api
    .get('/tasks', {
      params: {
        page, size, company_id: companyId, responsavel_id: responsavelId,
        status, tipo, prioridade, busca, data_inicio: dataInicio, data_fim: dataFim, deal_id: dealId,
        contact_id: contactId,
      },
    })
    .then((res) => res.data)
}

export function getTask(id) {
  return api.get(`/tasks/${id}`).then((res) => res.data)
}

export function createTask(data) {
  return api.post('/tasks', data).then((res) => res.data)
}

export function updateTask(id, data) {
  return api.put(`/tasks/${id}`, data).then((res) => res.data)
}

export function deleteTask(id) {
  return api.delete(`/tasks/${id}`)
}

// `data` é opcional — só faz sentido pra tarefas de ligação concluídas pela
// fila de execução: { resultado_ligacao, observacoes }.
export function completeTask(id, data) {
  return api.patch(`/tasks/${id}/complete`, data ?? {}).then((res) => res.data)
}

export function uncompleteTask(id) {
  return api.patch(`/tasks/${id}/uncomplete`).then((res) => res.data)
}

// Envio manual de e-mail pela fila de execução (integração Microsoft 365 já
// conectada) — { destinatario, assunto, corpo }. Marca a tarefa como
// concluída no sucesso.
export function sendTaskEmail(id, data) {
  return api.post(`/tasks/${id}/send-email`, data).then((res) => res.data)
}

export async function exportTasks(filters = {}) {
  const res = await api.get('/tasks/export', {
    params: {
      responsavel_id: filters.responsavelId, status: filters.status,
      tipo: filters.tipo, prioridade: filters.prioridade, busca: filters.busca,
      company_id: filters.companyId, data_inicio: filters.dataInicio, data_fim: filters.dataFim,
    },
    responseType: 'blob',
  })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'tarefas.csv'
  a.click()
  URL.revokeObjectURL(url)
}
