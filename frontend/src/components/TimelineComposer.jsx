import { useState } from 'react'

const TIMELINE_TYPES = [
  { key: 'nota', label: 'Nota' },
  { key: 'ligacao', label: 'Ligação' },
  { key: 'email', label: 'E-mail' },
  { key: 'reuniao', label: 'Reunião' },
]

export default function TimelineComposer({
  onSubmit, submitting, placeholder, submitLabel = 'Registrar', pendingLabel = 'Registrando…',
}) {
  const [tipo, setTipo] = useState('nota')
  const [titulo, setTitulo] = useState('')
  const [texto, setTexto] = useState('')
  const [destinatario, setDestinatario] = useState('')
  const [inicio, setInicio] = useState('')
  const [fim, setFim] = useState('')
  const [criarTeams, setCriarTeams] = useState(false)

  function reset() {
    setTitulo(''); setTexto(''); setDestinatario(''); setInicio(''); setFim(''); setCriarTeams(false)
  }

  function handleSubmit() {
    if (tipo === 'email') {
      if (!destinatario.trim() || !titulo.trim()) return
      onSubmit({ tipo, titulo: titulo.trim(), descricao: texto.trim() || null, destinatario: destinatario.trim() }, reset)
      return
    }
    if (tipo === 'reuniao') {
      if (!titulo.trim()) return
      const payload = { tipo, titulo: titulo.trim(), descricao: texto.trim() || null }
      if (inicio && fim) {
        payload.inicio = new Date(inicio).toISOString()
        payload.fim = new Date(fim).toISOString()
        payload.criar_teams = criarTeams
      }
      onSubmit(payload, reset)
      return
    }
    if (!texto.trim()) return
    const label = TIMELINE_TYPES.find((t) => t.key === tipo)?.label ?? 'Nota'
    onSubmit({ tipo, titulo: label, descricao: texto.trim() }, reset)
  }

  return (
    <div className="composer">
      <div className="composer-types">
        {TIMELINE_TYPES.map((t) => (
          <button key={t.key} className={`composer-type${tipo === t.key ? ' active' : ''}`} onClick={() => setTipo(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {tipo === 'email' && (
        <div className="f-row">
          <div className="f-group">
            <label className="f-label">Para</label>
            <input className="f-input" value={destinatario} onChange={(e) => setDestinatario(e.target.value)} placeholder="nome@empresa.com.br" />
          </div>
          <div className="f-group">
            <label className="f-label">Assunto</label>
            <input className="f-input" value={titulo} onChange={(e) => setTitulo(e.target.value)} />
          </div>
        </div>
      )}

      {tipo === 'reuniao' && (
        <>
          <div className="f-group">
            <label className="f-label">Título</label>
            <input className="f-input" value={titulo} onChange={(e) => setTitulo(e.target.value)} />
          </div>
          <div className="f-row">
            <div className="f-group">
              <label className="f-label">Início <span className="opt">opcional</span></label>
              <input className="f-input" type="datetime-local" value={inicio} onChange={(e) => setInicio(e.target.value)} />
            </div>
            <div className="f-group">
              <label className="f-label">Fim <span className="opt">opcional</span></label>
              <input className="f-input" type="datetime-local" value={fim} onChange={(e) => setFim(e.target.value)} />
            </div>
          </div>
          {inicio && fim && (
            <label className="teams-check-row">
              <input type="checkbox" checked={criarTeams} onChange={(e) => setCriarTeams(e.target.checked)} />
              Criar reunião do Teams e agendar na minha agenda Outlook conectada
            </label>
          )}
        </>
      )}

      <textarea
        placeholder={placeholder}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
      />

      <div className="composer-foot">
        <button className="composer-submit" disabled={submitting} onClick={handleSubmit}>
          {submitting ? pendingLabel : submitLabel}
        </button>
      </div>
    </div>
  )
}
