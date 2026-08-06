import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import * as authApi from '../api/auth'
import { loadTokens, saveTokens } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState('loading') // loading | authenticated | anonymous

  useEffect(() => {
    const tokens = loadTokens()
    if (!tokens?.access_token) {
      setStatus('anonymous')
      return
    }
    authApi
      .me()
      .then((data) => {
        setUser(data)
        setStatus('authenticated')
      })
      .catch(() => {
        saveTokens(null)
        setStatus('anonymous')
      })
  }, [])

  const login = useCallback(async (email, senha, remember = true) => {
    const tokens = await authApi.login(email, senha)
    saveTokens(tokens, remember)
    const data = await authApi.me()
    setUser(data)
    setStatus('authenticated')
    return data
  }, [])

  const refreshUser = useCallback(async () => {
    const data = await authApi.me()
    setUser(data)
    return data
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      // tokens são stateless; ignora falha de rede no logout
    }
    saveTokens(null)
    setUser(null)
    setStatus('anonymous')
  }, [])

  return (
    <AuthContext.Provider value={{ user, status, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return ctx
}
