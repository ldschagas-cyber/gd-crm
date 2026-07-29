import { api } from './client'

export function listImportJobs({ page = 1, size = 20 } = {}) {
  return api.get('/import-jobs', { params: { page, size } }).then((res) => res.data)
}
