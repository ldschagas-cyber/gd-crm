import { useSoftphone } from '../context/SoftphoneContext.jsx'
import './Softphone.css'

function formatSeconds(total) {
  const m = String(Math.floor(total / 60)).padStart(2, '0')
  const s = String(total % 60).padStart(2, '0')
  return `${m}:${s}`
}

export default function Softphone() {
  const { status, label, incoming, seconds, error, answer, rejectIncoming, hangup } = useSoftphone()

  if (status === 'incoming' && incoming) {
    return (
      <div className="softphone-bar softphone-incoming">
        <div className="softphone-info">
          <span className="softphone-pulse" />
          <div>
            <strong>Chamada recebida</strong>
            <span>{incoming.from}</span>
          </div>
        </div>
        <div className="softphone-actions">
          <button className="softphone-btn reject" onClick={rejectIncoming} title="Recusar">✕</button>
          <button className="softphone-btn accept" onClick={answer} title="Atender">✓</button>
        </div>
      </div>
    )
  }

  if (status === 'idle') {
    if (!error) return null
    return (
      <div className="softphone-bar softphone-error">
        <span>{error}</span>
      </div>
    )
  }

  return (
    <div className="softphone-bar softphone-active">
      <div className="softphone-info">
        <span className={`softphone-pulse ${status === 'in-call' ? 'connected' : ''}`} />
        <div>
          <strong>{label ?? 'Chamada'}</strong>
          <span>
            {status === 'dialing' && 'Ligando…'}
            {status === 'ringing' && 'Chamando…'}
            {status === 'in-call' && formatSeconds(seconds)}
          </span>
        </div>
      </div>
      <div className="softphone-actions">
        <button className="softphone-btn reject" onClick={hangup} title="Desligar">✕</button>
      </div>
    </div>
  )
}
