import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { resetPassword } from '../api/auth'
import ArgosMark from '../components/ArgosMark.jsx'
import './LoginPage.css'

// Tela pública acessada via link gerado por um admin em Usuários (não há envio
// automático por e-mail nesta versão — o admin copia o link e envia manualmente).
export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [novaSenha, setNovaSenha] = useState('')
  const [confirmarSenha, setConfirmarSenha] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)

    if (novaSenha.length < 8) {
      setError({ title: 'Senha muito curta', body: 'Use pelo menos 8 caracteres.' })
      return
    }
    if (novaSenha !== confirmarSenha) {
      setError({ title: 'As senhas não coincidem', body: 'Confira os dois campos e tente de novo.' })
      return
    }

    setLoading(true)
    try {
      await resetPassword(token, novaSenha)
      setSuccess(true)
    } catch (err) {
      setError(
        err.response?.status === 401
          ? { title: 'Link inválido ou expirado', body: 'Peça ao administrador para gerar um novo link.' }
          : { title: 'Não foi possível redefinir a senha', body: 'Tente novamente em instantes.' },
      )
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
            <h1>Defina sua nova senha de acesso.</h1>
            <p>Escolha uma senha com pelo menos 8 caracteres. Depois de salvar, use-a para entrar normalmente.</p>
          </div>
        </div>

        <div className="brand-bottom">
          <span>Argos by GD Conecta &copy; 2026</span>
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

          {!token && (
            <>
              <div className="form-card-head">
                <h2>Link inválido</h2>
                <p className="sub">Este link de redefinição está incompleto. Peça um novo link ao administrador.</p>
              </div>
              <Link to="/login" className="forgot" style={{ padding: 0 }}>Voltar para o login</Link>
            </>
          )}

          {token && success && (
            <>
              <div className="form-card-head">
                <h2>Senha redefinida</h2>
                <p className="sub">Sua senha foi atualizada. Você já pode entrar com ela.</p>
              </div>
              <button type="button" className="submit" onClick={() => navigate('/login', { replace: true })}>
                <span className="submit-label">Ir para o login</span>
              </button>
            </>
          )}

          {token && !success && (
            <>
              <div className="form-card-head">
                <h2>Redefinir senha</h2>
                <p className="sub">Escolha uma nova senha para a sua conta.</p>
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
                  <label htmlFor="nova-senha">Nova senha</label>
                  <div className="field-control has-toggle">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      id="nova-senha"
                      name="nova-senha"
                      autoComplete="new-password"
                      placeholder="Mínimo 8 caracteres"
                      value={novaSenha}
                      onChange={(e) => setNovaSenha(e.target.value)}
                      aria-invalid={error ? 'true' : undefined}
                      required
                      minLength={8}
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

                <div className="field">
                  <label htmlFor="confirmar-senha">Confirmar nova senha</label>
                  <div className="field-control">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      id="confirmar-senha"
                      name="confirmar-senha"
                      autoComplete="new-password"
                      placeholder="Repita a nova senha"
                      value={confirmarSenha}
                      onChange={(e) => setConfirmarSenha(e.target.value)}
                      aria-invalid={error ? 'true' : undefined}
                      required
                      minLength={8}
                    />
                  </div>
                </div>

                <button type="submit" className={`submit${loading ? ' is-loading' : ''}`} disabled={loading}>
                  <span className="spinner" aria-hidden="true" />
                  <span className="submit-label">{loading ? 'Salvando…' : 'Salvar nova senha'}</span>
                </button>
              </form>
            </>
          )}
        </div>
      </main>
    </div>
  )
}
