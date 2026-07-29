import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'
export const API_ORIGIN = BASE_URL.replace(/\/api\/v1\/?$/, '')

const TOKENS_KEY = 'gdcrm.tokens'

export function loadTokens() {
  try {
    const raw = localStorage.getItem(TOKENS_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function saveTokens(tokens) {
  if (tokens) {
    localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens))
  } else {
    localStorage.removeItem(TOKENS_KEY)
  }
}

export const api = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use((config) => {
  const tokens = loadTokens()
  if (tokens?.access_token) {
    config.headers.Authorization = `Bearer ${tokens.access_token}`
  }
  return config
})

let refreshPromise = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error
    const isAuthRoute = config?.url?.includes('/auth/')
    if (response?.status !== 401 || isAuthRoute || config._retried) {
      return Promise.reject(error)
    }

    const tokens = loadTokens()
    if (!tokens?.refresh_token) {
      return Promise.reject(error)
    }

    config._retried = true
    try {
      refreshPromise ??= axios
        .post(`${BASE_URL}/auth/refresh`, { refresh_token: tokens.refresh_token })
        .finally(() => {
          refreshPromise = null
        })
      const { data } = await refreshPromise
      saveTokens(data)
      config.headers.Authorization = `Bearer ${data.access_token}`
      return api(config)
    } catch (refreshError) {
      saveTokens(null)
      return Promise.reject(refreshError)
    }
  },
)
