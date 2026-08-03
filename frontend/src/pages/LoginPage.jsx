import { useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import './LoginPage.css'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from ?? '/'

  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const passwordRef = useRef(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)

    if (!email || !senha) {
      setError('Preencha e-mail e senha para continuar.')
      return
    }

    setLoading(true)
    try {
      await login(email, senha)
      navigate(from, { replace: true })
    } catch (err) {
      setError(
        err.response?.status === 401
          ? 'E-mail ou senha inválidos.'
          : 'Não foi possível entrar. Tente novamente em instantes.',
      )
      passwordRef.current?.focus()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="screen">
      <aside className="brand" aria-hidden="false">
        <div className="brand-top">
          <div className="wordmark">
            <div className="monogram">GD</div>
            <div className="wordmark-text">
              <strong>Conecta CRM</strong>
              <span>Gestão comercial B2B</span>
            </div>
          </div>

          <div className="brand-claim">
            <h1>Cada empresa da sua carteira, num único lugar.</h1>
            <p>
              Prospecção, pipeline e relacionamento comercial — organizados do
              primeiro contato ao fechamento.
            </p>
          </div>
        </div>

        <div className="brand-bottom">
          <span>GD Conecta &copy; 2026</span>
          <span className="env-pill">v0.1 · ambiente local</span>
        </div>
      </aside>

      <main className="form-panel">
        <div className="form-card">
          <div className="form-mobile-brand">
            <div className="monogram">GD</div>
            <div>
              <strong>Conecta CRM</strong>
              <span>Gestão comercial B2B</span>
            </div>
          </div>

          <h2>Entrar na sua conta</h2>
          <p className="sub">
            Use o e-mail e a senha cadastrados pelo administrador da sua empresa.
          </p>

          {error && (
            <div className="alert error show" role="alert">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7">
                <circle cx="10" cy="10" r="8" />
                <path d="M10 6.5v4.2M10 13.4h.01" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="field">
              <label htmlFor="email">E-mail</label>
              <div className="field-control">
                <input
                  type="email"
                  id="email"
                  name="email"
                  autoComplete="username"
                  placeholder="voce@suaempresa.com.br"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  aria-invalid={error ? 'true' : undefined}
                  required
                />
              </div>
            </div>

            <div className="field">
              <label htmlFor="password">Senha</label>
              <div className="field-control has-toggle">
                <input
                  ref={passwordRef}
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  name="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  aria-invalid={error ? 'true' : undefined}
                  required
                />
                <button
                  type="button"
                  className="toggle-visibility"
                  aria-pressed={showPassword}
                  aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                  onClick={() => setShowPassword((v) => !v)}
                >
                  {showPassword ? (
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
                      <path d="M2.5 2.5l15 15M8.3 8.4a2.6 2.6 0 003.4 3.4M6 5.2C3.3 6.6 1.5 10 1.5 10s3 5.5 8.5 5.5c1.4 0 2.7-.35 3.8-.9M12.2 5.1c-.7-.2-1.4-.3-2.2-.3-1 0-1.9.16-2.7.45" />
                      <path d="M15.6 6.9c1.5 1.2 2.9 3.1 2.9 3.1s-.7 1.28-2 2.6" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
                      <path d="M1.5 10S4.5 4.5 10 4.5 18.5 10 18.5 10 15.5 15.5 10 15.5 1.5 10 1.5 10Z" />
                      <circle cx="10" cy="10" r="2.6" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            <div className="row-between">
              <button
                type="button"
                className="forgot"
                onClick={() =>
                  setError('Recuperação por e-mail ainda não está disponível nesta versão.')
                }
              >
                Esqueci minha senha
              </button>
            </div>

            <button type="submit" className={`submit${loading ? ' is-loading' : ''}`} disabled={loading}>
              <span className="spinner" aria-hidden="true" />
              <span className="submit-label">Entrar</span>
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}
