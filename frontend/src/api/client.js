import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'
export const API_ORIGIN = BASE_URL.replace(/\/api\/v1\/?$/, '')

const TOKENS_KEY = 'gdcrm.tokens'

// "Manter conectado": marcado -> localStorage (sobrevive ao fechar o navegador);
// desmarcado -> sessionStorage (some ao fechar a aba). loadTokens() olha os dois
// pra funcionar em ambos os casos; saveTokens() sem `persist` explícito (usado no
// refresh de token) mantém o par onde já estava, sem trocar de storage sozinho.
export function loadTokens() {
  try {
    const raw = localStorage.getItem(TOKENS_KEY) ?? sessionStorage.getItem(TOKENS_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function currentTokenStorage() {
  try {
    if (localStorage.getItem(TOKENS_KEY)) return localStorage
  } catch {
    // ignora — segue pro fallback
  }
  return sessionStorage
}

export function saveTokens(tokens, persist) {
  try {
    if (!tokens) {
      localStorage.removeItem(TOKENS_KEY)
      sessionStorage.removeItem(TOKENS_KEY)
      return
    }
    const storage = persist === undefined ? currentTokenStorage() : (persist ? localStorage : sessionStorage)
    storage.setItem(TOKENS_KEY, JSON.stringify(tokens))
    const other = storage === localStorage ? sessionStorage : localStorage
    other.removeItem(TOKENS_KEY)
  } catch {
    // storage indisponível (modo privado restrito etc.) — segue sem persistir
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
