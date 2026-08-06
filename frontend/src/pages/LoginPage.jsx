import { useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import ArgosMark from '../components/ArgosMark.jsx'
import './LoginPage.css'

// Recorte de negócios do painel de marca — conteúdo ilustrativo, mesmos
// registros de exemplo usados no Manual da Marca Argos (não são dados reais).
const RECORTE_ROWS = [
  { cliente: 'Usina Rio Claro', valor: '48.200,00', status: 'Em análise', tone: 'info' },
  { cliente: 'Condomínio Aldeia', valor: '9.870,50', status: 'Ganho', tone: 'success' },
  { cliente: 'Padaria São José', valor: '1.145,90', status: 'Aguardando doc.', tone: 'warning' },
]

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from ?? '/'

  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [remember, setRemember] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const passwordRef = useRef(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)

    if (!email || !senha) {
      setError({
        title: 'Preencha e-mail e senha',
        body: 'Os dois campos são obrigatórios para continuar.',
      })
      return
    }

    setLoading(true)
    try {
      await login(email, senha, remember)
      navigate(from, { replace: true })
    } catch (err) {
      setError(
        err.response?.status === 401
          ? { title: 'E-mail ou senha incorretos', body: 'Confira os dados e tente novamente.' }
          : { title: 'Não foi possível entrar', body: 'Tente novamente em instantes.' },
      )
      passwordRef.current?.focus()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="screen">
      <aside className="brand" aria-hidden="false">
        <div className="brand-glow" aria-hidden="true" />
        <div className="brand-ring" aria-hidden="true" />

        <div className="wordmark">
          <ArgosMark size={48} variant="dark" />
          <div className="wordmark-text">
            <strong>Argos</strong>
            <span>by GD Conecta</span>
          </div>
        </div>

        <div className="brand-mid">
          <div className="brand-claim">
            <h1>Cada empresa da sua carteira, num único lugar.</h1>
            <p>
              Prospecção, pipeline e relacionamento comercial — organizados do
              primeiro contato ao fechamento.
            </p>
          </div>

          <div className="recorte" role="img" aria-label="Prévia da tabela de negócios do CRM">
            <div className="recorte-head">
              <span>Cliente</span>
              <span>Valor</span>
              <span>Status</span>
            </div>
            {RECORTE_ROWS.map((row) => (
              <div className="recorte-row" key={row.cliente}>
                <span className="recorte-cliente">{row.cliente}</span>
                <span className="recorte-valor">{row.valor}</span>
                <span>
                  <span className={`recorte-pill recorte-pill--${row.tone}`}>{row.status}</span>
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="brand-bottom">
          <span>Argos by GD Conecta &copy; 2026</span>
          {import.meta.env.DEV && (
            <span className="env-pill">
              <span className="env-dot" aria-hidden="true" />
              v0.1 · ambiente local
            </span>
          )}
        </div>
      </aside>

      <main className="form-panel">
        <div className="form-card">
          <div className="form-brand">
            <ArgosMark size={40} variant="light" />
            <div>
              <strong>Argos</strong>
              <span>by GD Conecta</span>
            </div>
          </div>

          <div className="form-card-head">
            <h2>Entrar na sua conta</h2>
            <p className="sub">
              Use o e-mail e a senha cadastrados pelo administrador da sua empresa.
            </p>
          </div>

          {error && (
            <div className="alert error show" role="alert">
              <span className="alert-icon" aria-hidden="true">!</span>
              <div className="alert-text">
                <strong>{error.title}</strong>
                <span>{error.body}</span>
              </div>
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
                  placeholder="nome@empresa.com.br"
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
                  placeholder="Sua senha"
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
                  {showPassword ? 'OCULTAR' : 'VER'}
                </button>
              </div>
            </div>

            <div className="row-between">
              <label className="remember-row" htmlFor="remember">
                <input
                  type="checkbox"
                  id="remember"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                />
                <span>Manter conectado</span>
              </label>
              <button
                type="button"
                className="forgot"
                onClick={() =>
                  setError({
                    title: 'Recuperação indisponível',
                    body: 'Recuperação de senha por e-mail ainda não está disponível nesta versão.',
                  })
                }
              >
                Esqueci minha senha
              </button>
            </div>

            <button type="submit" className={`submit${loading ? ' is-loading' : ''}`} disabled={loading}>
              <span className="spinner" aria-hidden="true" />
              <span className="submit-label">{loading ? 'Entrando…' : 'Entrar'}</span>
            </button>
          </form>

          <div className="support-note">
            <p>
              Não tem acesso? Fale com o administrador da sua empresa ou escreva para{' '}
              <a href="mailto:suporte@gdconecta.com.br">suporte@gdconecta.com.br</a>.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
