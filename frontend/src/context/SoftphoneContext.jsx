import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { Device } from '@twilio/voice-sdk'
import { useQuery } from '@tanstack/react-query'
import { getCallConfig, getCallToken } from '../api/calls'

const SoftphoneContext = createContext(null)

// Números no cadastro são salvos sem DDI (ex.: "12996597214"). Sem o "+55",
// a Twilio interpreta como NANP (EUA) e a chamada falha na hora, sem tocar.
function toE164BR(numero) {
  const raw = String(numero || '').trim()
  if (!raw) return ''
  if (raw.startsWith('+')) return `+${raw.replace(/\D/g, '')}`
  const digits = raw.replace(/\D/g, '')
  if (digits.startsWith('55') && digits.length >= 12) return `+${digits}`
  return `+55${digits}`
}

// idle | dialing | ringing | in-call | incoming
export function SoftphoneProvider({ children }) {
  const configQuery = useQuery({ queryKey: ['calls', 'config'], queryFn: getCallConfig, staleTime: 5 * 60 * 1000 })
  const conectado = configQuery.data?.conectado ?? false

  const deviceRef = useRef(null)
  const activeCallRef = useRef(null)
  const [status, setStatus] = useState('idle')
  const [label, setLabel] = useState(null)
  const [incoming, setIncoming] = useState(null) // { call, from }
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState(null)

  const reset = useCallback(() => {
    activeCallRef.current = null
    setStatus('idle')
    setLabel(null)
    setIncoming(null)
    setSeconds(0)
  }, [])

  const wireCallEvents = useCallback((call, initialLabel) => {
    activeCallRef.current = call
    call.on('ringing', () => setStatus('ringing'))
    call.on('accept', () => setStatus('in-call'))
    call.on('disconnect', reset)
    call.on('cancel', reset)
    call.on('reject', reset)
    call.on('error', (err) => {
      setError(err?.message ?? 'Falha na chamada.')
      reset()
    })
    if (initialLabel) setLabel(initialLabel)
  }, [reset])

  useEffect(() => {
    if (!conectado || deviceRef.current) return
    let cancelled = false

    getCallToken().then(({ token }) => {
      if (cancelled) return
      const device = new Device(token, { logLevel: 'error' })
      deviceRef.current = device

      device.on('tokenWillExpire', async () => {
        const { token: fresh } = await getCallToken()
        device.updateToken(fresh)
      })
      device.on('incoming', (call) => {
        setIncoming({ call, from: call.parameters?.From || 'Número desconhecido' })
        setStatus('incoming')
        call.on('cancel', reset)
        call.on('disconnect', reset)
        call.on('reject', reset)
      })
      device.on('error', (err) => setError(err?.message ?? 'Erro no dispositivo de chamadas.'))
      device.register()
    }).catch((err) => setError(err?.message ?? 'Não foi possível iniciar as chamadas.'))

    return () => {
      cancelled = true
      deviceRef.current?.destroy()
      deviceRef.current = null
    }
  }, [conectado, reset])

  useEffect(() => {
    if (status !== 'in-call') return
    setSeconds(0)
    const id = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [status])

  const call = useCallback(async (numero, { label: callLabel, companyId, contactId, dealId } = {}) => {
    if (!deviceRef.current) {
      setError('Chamadas ainda não conectadas.')
      return
    }
    setError(null)
    setStatus('dialing')
    try {
      const conn = await deviceRef.current.connect({
        params: {
          To: toE164BR(numero),
          ...(companyId ? { CompanyId: companyId } : {}),
          ...(contactId ? { ContactId: contactId } : {}),
          ...(dealId ? { DealId: dealId } : {}),
        },
      })
      wireCallEvents(conn, callLabel || numero)
    } catch (err) {
      setError(err?.message ?? 'Não foi possível ligar.')
      reset()
    }
  }, [wireCallEvents, reset])

  const answer = useCallback(() => {
    if (!incoming) return
    wireCallEvents(incoming.call, incoming.from)
    incoming.call.accept()
    setIncoming(null)
  }, [incoming, wireCallEvents])

  const rejectIncoming = useCallback(() => {
    incoming?.call.reject()
    reset()
  }, [incoming, reset])

  const hangup = useCallback(() => {
    activeCallRef.current?.disconnect()
    reset()
  }, [reset])

  return (
    <SoftphoneContext.Provider value={{ conectado, status, label, incoming, seconds, error, call, answer, rejectIncoming, hangup }}>
      {children}
    </SoftphoneContext.Provider>
  )
}

export function useSoftphone() {
  const ctx = useContext(SoftphoneContext)
  if (!ctx) throw new Error('useSoftphone deve ser usado dentro de SoftphoneProvider')
  return ctx
}
